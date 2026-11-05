"""
Banco vetorial do RAG: guarda os trechos com o vetor (embedding) de cada um e
responde "quais trechos são mais parecidos com este vetor?".

``BancoVetorial`` é o contrato (Protocol): quem usa o banco só depende dele.
``BancoVetorialLocal`` é a implementação atual, em Python puro, que compara
a pergunta com todos os trechos por similaridade de cosseno. Para uma base
pequena (centenas de trechos) isso é instantâneo e não exige dependência nova.

Para trocar por um banco vetorial de verdade (Chroma, FAISS, pgvector...),
escreva uma classe com os mesmos membros e passe-a ao ``Recuperador``; nada
mais muda.
"""

import math
from typing import Protocol

from destrava.rag.chunker import Trecho


class BancoVetorial(Protocol):
    """O que o RAG precisa de um banco vetorial."""

    @property
    def trechos(self) -> list[Trecho]:
        """Os trechos guardados, na ordem em que foram adicionados."""

    def buscar(
        self, vetor: list[float], n: int | None = None, minimo: float = 0.0
    ) -> list[tuple[int, float]]:
        """Posições dos trechos mais parecidos com o vetor, com a similaridade.

        Devolve pares (posição em ``trechos``, cosseno), do mais parecido para
        o menos, só com cosseno >= minimo e no máximo n pares (todos se n for
        None). Levanta ValueError se o vetor tiver tamanho diferente do dos
        vetores guardados.
        """


def normalizar(vetor: list[float]) -> list[float]:
    """Deixa o vetor com comprimento 1 (assim o cosseno vira um produto escalar)."""
    comprimento = math.sqrt(sum(x * x for x in vetor))
    return [x / comprimento for x in vetor] if comprimento else list(vetor)


class BancoVetorialLocal:
    """Banco vetorial em memória, com busca exata por similaridade de cosseno."""

    def __init__(self, trechos: list[Trecho], vetores: list[list[float]]):
        """
        Args:
            trechos: Trechos a guardar.
            vetores: Um vetor por trecho, na mesma ordem e do mesmo tamanho.

        Raises:
            ValueError: Se a quantidade de vetores for diferente da de trechos
                ou se os vetores tiverem tamanhos diferentes.
        """
        if len(trechos) != len(vetores):
            raise ValueError("Deve haver exatamente um vetor por trecho.")
        if len({len(v) for v in vetores}) > 1:
            raise ValueError("Todos os vetores devem ter o mesmo tamanho.")

        self._trechos = list(trechos)
        self._vetores = [normalizar(v) for v in vetores]
        self.dimensao = len(vetores[0]) if vetores else 0

    @property
    def trechos(self) -> list[Trecho]:
        return self._trechos

    def buscar(
        self, vetor: list[float], n: int | None = None, minimo: float = 0.0
    ) -> list[tuple[int, float]]:
        if self._vetores and len(vetor) != self.dimensao:
            raise ValueError(
                f"O vetor tem {len(vetor)} dimensões, mas o banco usa {self.dimensao} "
                "(o modelo de embeddings mudou desde que o índice foi gerado?)."
            )

        consulta = normalizar(vetor)
        pares = [
            (i, sum(a * b for a, b in zip(consulta, doc)))
            for i, doc in enumerate(self._vetores)
        ]
        pares = [(i, s) for i, s in pares if s >= minimo]
        pares.sort(key=lambda p: (-p[1], p[0]))
        return pares if n is None else pares[:n]
