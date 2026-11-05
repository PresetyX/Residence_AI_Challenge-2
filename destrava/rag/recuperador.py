"""
Fase de inferência do RAG, até a recuperação de contexto:

    pergunta → embedding da pergunta → busca por similaridade → N trechos mais próximos

Como a busca funciona:
    1. Embeddings (significado): a pergunta passa pelo mesmo modelo usado na
       indexação e o banco vetorial devolve os trechos de maior cosseno
       ("marcar dentista" acha "criar evento" mesmo sem palavras em comum).
    2. BM25 (palavras-chave): sempre disponível, não precisa do Ollama. Também
       acha o que o significado deixa passar (nomes próprios, siglas, números).
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
from destrava.rag.banco_vetorial import BancoVetorial
from destrava.rag.chunker import Trecho
from destrava.rag.indice import Indice
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


class Recuperador:
    """Busca os trechos mais relevantes de um índice para uma pergunta."""

    def __init__(
        self,
        indice: Indice,
        usar_embeddings: bool | None = None,
        banco: BancoVetorial | None = None,
    ):
        """
        Args:
            indice: Índice já construído (ver indice.construir_indice).
            usar_embeddings: None (padrão) usa embeddings se o índice os tiver
                e o Ollama responder; True exige (levanta ErroLLM se não
                responder); False usa só palavras-chave e nunca chama o Ollama.
            banco: Banco vetorial a usar no lugar do local (ver
                banco_vetorial.BancoVetorial). Deve guardar os mesmos trechos
                do índice.
        """
        self._usar_embeddings = usar_embeddings
        self._trechos = indice.trechos
        self._bm25 = _BM25([tokenizar(t.para_indexar) for t in self._trechos])

        # Só usa embeddings se existirem no índice e se o modo permitir.
        self._banco: BancoVetorial | None = None
        if usar_embeddings is not False:
            self._banco = banco if banco is not None else indice.banco_vetorial()

    @property
    def usa_embeddings(self) -> bool:
        """True se a busca combina BM25 com embeddings."""
        return self._banco is not None

    @property
    def total_trechos(self) -> int:
        return len(self._trechos)

    def _posicoes_por_significado(self, pergunta: str) -> list[int] | None:
        """Posições dos trechos por similaridade de significado, ou None se indisponível."""
        if self._banco is None:
            return None

        try:
            vetor = gerar_embeddings([config.RAG_PREFIXO_CONSULTA + pergunta])[0]
        except ErroLLM:
            if self._usar_embeddings:
                raise
            return None

        try:
            pares = self._banco.buscar(vetor, minimo=config.RAG_SIMILARIDADE_MINIMA)
        except ValueError:
            return None  # modelo trocado desde que o índice foi gerado
        return [i for i, _ in pares]

    def buscar(self, pergunta: str, k: int | None = None) -> list[TrechoEncontrado]:
        """Devolve os k trechos mais relevantes para a pergunta, do melhor para o pior.

        Args:
            pergunta: Pedido do usuário em texto livre.
            k: Quantos trechos devolver (padrão: config.RAG_TOP_K).

        Returns:
            Lista de trechos (vazia se a base for vazia ou nada for relevante).

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

        if not self._trechos:
            return []

        notas_lexicas = self._bm25.pontuar(tokenizar(pergunta))
        ordem_lexica = sorted(
            (i for i, nota in enumerate(notas_lexicas) if nota > 0),
            key=lambda i: notas_lexicas[i],
            reverse=True,
        )
        ordem_significado = self._posicoes_por_significado(pergunta)

        # Só palavras-chave: a própria nota BM25 ordena.
        if ordem_significado is None:
            return [
                TrechoEncontrado(
                    **self._trechos[i].model_dump(), score=notas_lexicas[i], metodo="lexico"
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
                **self._trechos[i].model_dump(), score=notas_rrf[i], metodo="hibrido"
            )
            for i in melhores
        ]
