from pathlib import Path
import html
import re

import torch


EMBEDDING_MODEL = "BAAI/bge-m3"
MODEL_PATH = Path(__file__).resolve().parents[1] / "modelos" / "rede_neural.pt"
MACROS = re.compile(r"\{(?:html|code|noformat|quote|panel|color)(?::[^}]*)?\}", re.I)
TAGS = re.compile(r"<[^>]+>")
URLS = re.compile(r"https?://\S+")


class StoryPointsMLP(torch.nn.Module):
    def __init__(self, input_size: int, dropout: float = 0.15) -> None:
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


def _limpar_texto(value: object) -> str:
    texto = str(value)
    texto = MACROS.sub(" ", texto)
    texto = TAGS.sub(" ", texto)
    texto = html.unescape(texto)
    texto = URLS.sub(" URL ", texto)
    return re.sub(r"\s+", " ", texto).strip()


class StoryPointsPredictor:
    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        embedding_model: str = EMBEDDING_MODEL,
    ) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Modelo de story points não encontrado em: {model_path}"
            )

        from sentence_transformers import SentenceTransformer

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

        self._model = StoryPointsMLP(input_size)
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
        self._embedding_model = SentenceTransformer(encoder_name)
        if isinstance(max_seq_len, int) and max_seq_len > 0:
            self._embedding_model.max_seq_length = max_seq_len

    def prever(self, tarefa: dict[str, object]) -> int:
        texto = ". ".join(
            (
                _limpar_texto(tarefa["titulo"]),
                _limpar_texto(tarefa["objetivo"]),
                _limpar_texto(tarefa["entregaveis"]),
                _limpar_texto(tarefa["demonstracao"]),
            )
        )
        max_chars = getattr(self, "_max_chars", 4000)
        texto = texto[:max_chars]
        embedding = self._embedding_model.encode(
            [texto],
            convert_to_tensor=True,
            normalize_embeddings=True,
        ).to("cpu")

        with torch.inference_mode():
            reduced = (embedding - self._pca_mean) @ self._pca_components.T
            scaled = (reduced - self._scaler_mean) / self._scaler_scale
            previsao = self._model(scaled)

        valor = float(torch.expm1(previsao.squeeze()).item())
        return max(1, round(valor))
