"""
Busca do RAG do Supervisor.

Dado o pedido do usuário em texto livre, devolve os trechos da base de
conhecimento mais úteis para o Supervisor decidir o agente e montar o JSON.

Como a busca funciona:
    1. BM25 (palavras-chave): sempre disponível, não precisa do Ollama.
    2. Embeddings (significado): usados quando o Ollama e o modelo de
       embeddings estão disponíveis ("marcar dentista" acha "criar evento"
       mesmo sem palavras em comum).
    3. Com as duas, as listas são combinadas por Reciprocal Rank Fusion (RRF),
       que soma 1 / (60 + posição) de cada lista e dispensa comparar notas de
       escalas diferentes.

Se o Ollama cair no meio do uso, a busca daquele pedido segue só com BM25.
"""

import math
from collections import Counter
from typing import Literal

from destrava.core import config
from destrava.core.llm_client import ErroLLM, gerar_embeddings
from destrava.rag.chunker import Trecho
from destrava.rag.indice import Indice, construir_indice
from destrava.rag.texto import tokenizar

# Constantes do BM25 (valores usuais) e do RRF (60 é o valor do artigo original).
BM25_K1 = 1.5
BM25_B = 0.75
RRF_K = 60


class TrechoEncontrado(Trecho):
    """Um trecho devolvido pela busca, com a nota e o método que o achou.

    A nota só serve para ordenar resultados do mesmo método: "lexico" é a nota
    BM25, "hibrido" é a soma RRF.
    """

    score: float
    metodo: Literal["lexico", "hibrido"]


class _BM25:
    """BM25 sobre a lista de trechos (cálculo simples, corpus pequeno)."""

    def __init__(self, documentos: list[list[str]]):
        self._frequencias = [Counter(doc) for doc in documentos]
        self._tamanhos = [len(doc) for doc in documentos]
        self._media = (sum(self._tamanhos) / len(documentos)) if documentos else 0.0

        presenca: Counter = Counter()
        for freq in self._frequencias:
            presenca.update(freq.keys())
        total = len(documentos)
        self._idf = {
            termo: math.log(1 + (total - n + 0.5) / (n + 0.5))
            for termo, n in presenca.items()
        }

    def pontuar(self, consulta: list[str]) -> list[float]:
        """Nota BM25 de cada trecho para a consulta (0 se não houver palavra em comum)."""
        notas = []
        for freq, tamanho in zip(self._frequencias, self._tamanhos):
            nota = 0.0
            for termo in set(consulta):
                f = freq.get(termo, 0)
                if not f:
                    continue
                norma = 1 - BM25_B + BM25_B * tamanho / (self._media or 1.0)
                nota += self._idf[termo] * f * (BM25_K1 + 1) / (f + BM25_K1 * norma)
            notas.append(nota)
        return notas


def _normalizar(vetor: list[float]) -> list[float]:
    """Deixa o vetor com comprimento 1 (assim o cosseno vira um produto escalar)."""
    comprimento = math.sqrt(sum(x * x for x in vetor))
    return [x / comprimento for x in vetor] if comprimento else vetor


def _ordem(notas: list[float], minimo: float) -> list[int]:
    """Posições dos trechos com nota acima do mínimo, da maior nota para a menor."""
    return sorted(
        (i for i, nota in enumerate(notas) if nota > minimo),
        key=lambda i: notas[i],
        reverse=True,
    )


class RagSupervisor:
    """RAG do Supervisor: busca na documentação dos agentes e nos exemplos de roteamento.

    Uso:
        rag = RagSupervisor()
        rag.buscar("marca um dentista amanhã às 15h")  # lista de TrechoEncontrado
        rag.contexto("marca um dentista amanhã às 15h") # texto pronto para o prompt
    """

    def __init__(
        self, usar_embeddings: bool | None = None, indice: Indice | None = None
    ):
        """
        Args:
            usar_embeddings: None (padrão) usa embeddings se o Ollama estiver
                disponível; True exige (levanta ErroLLM se não estiver);
                False usa só palavras-chave e nunca chama o Ollama.
            indice: Índice já pronto (para testes). Se omitido, é construído
                a partir de config.RAG_FONTES, com cópia em disco.
        """
        self._usar_embeddings = usar_embeddings
        self._indice = indice if indice is not None else construir_indice(usar_embeddings)

        self._bm25 = _BM25([tokenizar(t.para_indexar) for t in self._indice.trechos])

        # Só usa embeddings se existirem no índice e se o modo permitir.
        self._vetores = None
        if self._indice.embeddings is not None and usar_embeddings is not False:
            self._vetores = [_normalizar(v) for v in self._indice.embeddings]

    @property
    def usa_embeddings(self) -> bool:
        """True se a busca combina BM25 com embeddings."""
        return self._vetores is not None

    @property
    def total_trechos(self) -> int:
        return len(self._indice.trechos)

    def _ordem_por_significado(self, pergunta: str) -> list[int] | None:
        """Trechos ordenados por similaridade de significado, ou None se indisponível."""
        if self._vetores is None:
            return None

        try:
            vetor = gerar_embeddings([config.RAG_PREFIXO_CONSULTA + pergunta])[0]
        except ErroLLM:
            if self._usar_embeddings:
                raise
            return None

        vetor = _normalizar(vetor)
        if len(vetor) != len(self._vetores[0]):
            return None  # modelo trocado desde que o índice foi gerado

        similaridades = [
            sum(a * b for a, b in zip(vetor, doc)) for doc in self._vetores
        ]
        return _ordem(similaridades, config.RAG_SIMILARIDADE_MINIMA)

    def buscar(self, pergunta: str, k: int | None = None) -> list[TrechoEncontrado]:
        """Devolve os k trechos mais relevantes para o pedido, do melhor para o pior.

        Args:
            pergunta: Pedido do usuário em texto livre.
            k: Quantos trechos devolver (padrão: config.RAG_TOP_K).

        Returns:
            Lista de trechos (pode ser vazia, se nada for relevante).

        Raises:
            TypeError: Se a pergunta não for texto.
            ValueError: Se a pergunta estiver vazia ou k não for positivo.
            ErroLLM: Só com usar_embeddings=True e o Ollama indisponível.
        """
        if not isinstance(pergunta, str):
            raise TypeError("A pergunta deve ser uma string.")
        if not pergunta.strip():
            raise ValueError("A pergunta não pode estar vazia.")

        k = config.RAG_TOP_K if k is None else k
        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise ValueError("k deve ser um inteiro positivo.")

        trechos = self._indice.trechos
        notas_lexicas = self._bm25.pontuar(tokenizar(pergunta))
        ordem_lexica = _ordem(notas_lexicas, 0.0)
        ordem_significado = self._ordem_por_significado(pergunta)

        # Só palavras-chave: a própria nota BM25 ordena.
        if ordem_significado is None:
            return [
                TrechoEncontrado(
                    **trechos[i].model_dump(), score=notas_lexicas[i], metodo="lexico"
                )
                for i in ordem_lexica[:k]
            ]

        # Palavras-chave + significado: soma as posições das duas listas (RRF).
        notas_rrf: dict[int, float] = {}
        for ordem in (ordem_lexica, ordem_significado):
            for posicao, i in enumerate(ordem, start=1):
                notas_rrf[i] = notas_rrf.get(i, 0.0) + 1 / (RRF_K + posicao)

        melhores = sorted(notas_rrf, key=lambda i: (-notas_rrf[i], i))[:k]
        return [
            TrechoEncontrado(
                **trechos[i].model_dump(), score=notas_rrf[i], metodo="hibrido"
            )
            for i in melhores
        ]

    def contexto(self, pergunta: str, k: int | None = None) -> str:
        """Monta o texto de contexto para colocar no prompt do Supervisor.

        Cada trecho vem numerado e com a origem. Devolve "" se nada for
        relevante, para o prompt poder dizer que não há contexto.
        """
        encontrados = self.buscar(pergunta, k)
        return "\n\n".join(
            f"[{n}] Fonte: {t.fonte} | {t.secao}\n{t.texto}"
            for n, t in enumerate(encontrados, start=1)
        )
