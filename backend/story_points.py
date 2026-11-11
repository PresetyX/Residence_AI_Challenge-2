"""Estimativa de story points das tarefas do Planejador.

Dois modos, escolhidos por ``criar_estimador()`` a partir de config.STORY_POINTS_URL:

- Local (STORY_POINTS_URL vazio): ``StoryPointsPredictor`` carrega o BGE-M3 e a
  rede neural (modelos/rede_neural.pt) nesta máquina. Precisa de torch e
  sentence-transformers (requirements-ia.txt).
- Remoto (STORY_POINTS_URL definido): ``StoryPointsRemoto`` envia as tarefas por
  HTTP ao servidor de IA (backend/servidor_story_points.py), que roda o mesmo
  ``StoryPointsPredictor`` na GPU. Não importa torch nem sentence-transformers.

Por isso torch e sentence-transformers só são importados dentro de
``StoryPointsPredictor``: importar este módulo é leve nos dois modos.

Os dois estimadores têm a mesma interface:
    prever(tarefa) -> int
    prever_lote(tarefas) -> list[int]
"""

from __future__ import annotations

import html
import re
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import httpx

from destrava.core import config

if TYPE_CHECKING:  # só para o editor; não importa torch em tempo de execução
    import torch


EMBEDDING_MODEL = "BAAI/bge-m3"
MODEL_PATH = Path(__file__).resolve().parents[1] / "modelos" / "rede_neural.pt"
MACROS = re.compile(r"\{(?:html|code|noformat|quote|panel|color)(?::[^}]*)?\}", re.I)
TAGS = re.compile(r"<[^>]+>")
URLS = re.compile(r"https?://\S+")
CAMPOS_TAREFA = ("titulo", "objetivo", "entregaveis", "demonstracao")
# Cabeçalho com a chave compartilhada (config.CHAVE_API_IA).
CABECALHO_CHAVE = "X-API-Key"


class ErroStoryPoints(RuntimeError):
    """O serviço de story points está fora do ar ou respondeu algo inesperado."""


class EstimadorStoryPoints(Protocol):
    def prever(self, tarefa: Mapping[str, object]) -> int: ...

    def prever_lote(self, tarefas: Sequence[Mapping[str, object]]) -> list[int]: ...


def _limpar_texto(value: object) -> str:
    texto = str(value)
    texto = MACROS.sub(" ", texto)
    texto = TAGS.sub(" ", texto)
    texto = html.unescape(texto)
    texto = URLS.sub(" URL ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def montar_texto(tarefa: Mapping[str, object], max_chars: int = 4000) -> str:
    """Texto da tarefa que entra no embedding (o mesmo formato usado no treino)."""
    texto = ". ".join(_limpar_texto(tarefa[campo]) for campo in CAMPOS_TAREFA)
    return texto[:max_chars]


def _criar_mlp(input_size: int, dropout: float = 0.15) -> "torch.nn.Module":
    """A MLP treinada no notebook. Fica numa função para importar torch só aqui.

    O atributo ``network`` e a ordem das camadas precisam ficar iguais aos do
    treino: os nomes das chaves do state_dict dependem deles.
    """
    import torch

    class StoryPointsMLP(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.network = torch.nn.Sequential(
                torch.nn.Linear(input_size, 64),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout),
                torch.nn.Linear(64, 32),
                torch.nn.ReLU(),
                torch.nn.Linear(32, 16),
                torch.nn.ReLU(),
                torch.nn.Linear(16, 1),
            )

        def forward(self, features: torch.Tensor) -> torch.Tensor:
            return self.network(features)

    return StoryPointsMLP()


class StoryPointsPredictor:
    """Modo local: BGE-M3 + rede neural carregados nesta máquina."""

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        embedding_model: str = EMBEDDING_MODEL,
    ) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Modelo de story points não encontrado em: {model_path}"
            )

        # Imports pesados só no modo local (ver docstring do módulo).
        import torch
        from sentence_transformers import SentenceTransformer

        self._torch = torch
        artifact = torch.load(model_path, map_location="cpu", weights_only=True)
        if not isinstance(artifact, dict) or "model_state_dict" not in artifact:
            raise TypeError(
                "O artefato deve conter o state_dict e os parâmetros de pré-processamento."
            )

        model_class = artifact.get("model_class")
        if model_class != "MLP":
            raise ValueError(f"Classe de modelo não suportada: {model_class!r}")

        input_size = artifact.get("input_size")
        if not isinstance(input_size, int) or input_size <= 0:
            raise ValueError("O artefato deve informar um input_size positivo.")

        self._model = _criar_mlp(input_size)
        self._model.load_state_dict(artifact["model_state_dict"])
        self._model.eval()

        self._pca_components = artifact["pca_components"].float()
        self._pca_mean = artifact["pca_mean"].float()
        self._scaler_mean = artifact["scaler_mean"].float()
        self._scaler_scale = artifact["scaler_scale"].float()
        if (
            self._pca_components.ndim != 2
            or self._pca_mean.ndim != 1
            or self._scaler_mean.ndim != 1
            or self._scaler_scale.ndim != 1
            or self._pca_components.shape[0] != input_size
            or self._pca_components.shape[1] != self._pca_mean.shape[0]
            or self._scaler_mean.shape[0] != input_size
            or self._scaler_scale.shape[0] != input_size
        ):
            raise ValueError("Dimensões de PCA e scaler incompatíveis com o modelo.")

        encoder_name = artifact.get("embedding_model", embedding_model)
        max_seq_len = artifact.get("max_seq_len")
        self._max_chars = artifact.get("max_chars", 4000)
        # O SentenceTransformer usa a GPU (CUDA) se o torch instalado tiver
        # suporte a ela; senão, a CPU.
        self._embedding_model = SentenceTransformer(encoder_name)
        if isinstance(max_seq_len, int) and max_seq_len > 0:
            self._embedding_model.max_seq_length = max_seq_len
        # Uma inferência por vez: com várias pessoas chamando o servidor ao
        # mesmo tempo, evita disputar a memória da GPU.
        self._trava = threading.Lock()

    @property
    def dispositivo(self) -> str:
        return str(self._embedding_model.device)

    def prever(self, tarefa: Mapping[str, object]) -> int:
        return self.prever_lote([tarefa])[0]

    def prever_lote(self, tarefas: Sequence[Mapping[str, object]]) -> list[int]:
        """Story points de várias tarefas com um único embedding em lote."""
        if not tarefas:
            return []
        torch = self._torch
        textos = [montar_texto(tarefa, self._max_chars) for tarefa in tarefas]
        with self._trava:
            embeddings = self._embedding_model.encode(
                textos,
                convert_to_tensor=True,
                normalize_embeddings=True,
            ).to("cpu")

            with torch.inference_mode():
                reduced = (embeddings - self._pca_mean) @ self._pca_components.T
                scaled = (reduced - self._scaler_mean) / self._scaler_scale
                previsoes = self._model(scaled).reshape(-1)

        return [max(1, round(float(torch.expm1(valor).item()))) for valor in previsoes]


class StoryPointsRemoto:
    """Modo remoto: pede os story points ao servidor de IA por HTTP."""

    def __init__(
        self,
        url: str,
        timeout: float = 120,
        chave: str = "",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """
        Args:
            url: Endereço base do servidor (ex.: http://<ip-tailscale>:8001).
            timeout: Segundos para a resposta chegar (a conexão tem 5 s).
            chave: Chave compartilhada, enviada no cabeçalho X-API-Key.
            transport: Só para os testes (httpx.MockTransport), sem rede.
        """
        self.url = url.strip().rstrip("/")
        cabecalhos = {CABECALHO_CHAVE: chave} if chave else {}
        self._cliente = httpx.Client(
            base_url=self.url,
            timeout=httpx.Timeout(float(timeout), connect=5.0),
            headers=cabecalhos,
            transport=transport,
        )

    def prever(self, tarefa: Mapping[str, object]) -> int:
        return self.prever_lote([tarefa])[0]

    def prever_lote(self, tarefas: Sequence[Mapping[str, object]]) -> list[int]:
        """
        Raises:
            ErroStoryPoints: Servidor fora do ar, chave recusada, tempo esgotado
                ou resposta fora do formato.
        """
        if not tarefas:
            return []
        corpo = {"tarefas": [{campo: str(t[campo]) for campo in CAMPOS_TAREFA} for t in tarefas]}
        try:
            resposta = self._cliente.post("/story-points", json=corpo)
        except httpx.TimeoutException as erro:
            raise ErroStoryPoints(
                f"O serviço de story points em {self.url} demorou demais para responder. "
                "Ele pode estar ocupado; tente de novo ou aumente TIMEOUT_STORY_POINTS."
            ) from erro
        except httpx.HTTPError as erro:
            raise ErroStoryPoints(
                f"Não foi possível conectar ao serviço de story points em {self.url}. "
                "Verifique se o servidor de IA está ligado e se a Tailscale está conectada."
            ) from erro

        if resposta.status_code == 401:
            raise ErroStoryPoints(
                "O serviço de story points recusou a chave de API. Confira CHAVE_API_IA."
            )
        if resposta.status_code != 200:
            raise ErroStoryPoints(
                f"O serviço de story points respondeu HTTP {resposta.status_code}: {resposta.text[:200]}"
            )

        try:
            valores = resposta.json()["story_points"]
        except (ValueError, KeyError, TypeError) as erro:
            raise ErroStoryPoints("O serviço de story points devolveu uma resposta inválida.") from erro
        if (
            not isinstance(valores, list)
            or len(valores) != len(tarefas)
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in valores)
        ):
            raise ErroStoryPoints(
                "O serviço de story points não devolveu um número inteiro para cada tarefa."
            )
        return valores

    def fechar(self) -> None:
        self._cliente.close()


def criar_estimador() -> EstimadorStoryPoints:
    """Estimador remoto se STORY_POINTS_URL estiver definido; senão, o local."""
    if config.STORY_POINTS_URL:
        return StoryPointsRemoto(
            config.STORY_POINTS_URL,
            timeout=config.TIMEOUT_STORY_POINTS,
            chave=config.CHAVE_API_IA,
        )
    return StoryPointsPredictor()
