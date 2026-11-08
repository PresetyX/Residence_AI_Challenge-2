"""
Banco vetorial do RAG: Chroma, gravado em disco, acessado pelo LangChain.

Guarda cada trecho com o seu vetor (embedding) e responde "quais trechos têm
significado mais parecido com esta pergunta?".

Peças:
    - ``chromadb.PersistentClient``: o banco em si, numa pasta local (SQLite +
      índice HNSW). Não precisa de servidor.
    - ``langchain_chroma.Chroma``: o adaptador que transforma o Chroma num
      ``VectorStore`` do LangChain. É esse formato que a Indexing API
      (indice.py) sabe alimentar: ela adiciona e apaga documentos por ID.
    - ``BancoVetorial`` (esta classe): só junta as duas coisas com as escolhas
      do projeto (cosseno, telemetria desligada) e devolve a busca no formato
      que o recuperador usa.

Quem gera os vetores é o objeto ``Embeddings`` recebido (EmbeddingsOllama, do
llm_client): o Chroma o chama ao adicionar trechos (``embed_documents``) e ao
buscar (``embed_query``).

Para trocar por outro banco (FAISS, Qdrant, pgvector...), basta outro
``VectorStore`` do LangChain que aceite apagar por ID; a Indexing API e o
recuperador continuam iguais.
"""

from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

# Nome da coleção dentro da pasta do banco. Cada base (supervisor, planejador)
# e cada modelo de embeddings tem a sua pasta (ver indice.py), então um nome
# fixo basta.
COLECAO = "trechos"


class BancoVetorial:
    """Chroma persistente de uma base de conhecimento, com busca por cosseno."""

    def __init__(self, pasta: Path, embeddings: Embeddings):
        """Abre (ou cria) o banco na pasta. Não chama o Ollama.

        Args:
            pasta: Onde o Chroma grava os arquivos (criada se não existir).
            embeddings: Modelo que transforma texto em vetor.
        """
        pasta.mkdir(parents=True, exist_ok=True)
        # anonymized_telemetry=False: por padrão o Chroma envia estatísticas de
        # uso pela internet. Um projeto local não tem por que fazer isso.
        cliente = chromadb.PersistentClient(
            path=str(pasta), settings=Settings(anonymized_telemetry=False)
        )
        self.vector_store = Chroma(
            collection_name=COLECAO,
            embedding_function=embeddings,
            client=cliente,
            # "hnsw:space": "cosine" faz o Chroma medir DISTÂNCIA DE COSSENO
            # (= 1 - cosseno). O padrão seria a distância euclidiana (L2), que
            # depende do comprimento dos vetores e não teria a escala de 0 a 1
            # que config.RAG_SIMILARIDADE_MINIMA supõe. Só vale na criação da
            # coleção; uma coleção existente mantém a métrica com que nasceu.
            collection_metadata={"hnsw:space": "cosine"},
        )

    def total(self) -> int:
        """Quantos trechos (vetores) estão guardados."""
        return self.vector_store._collection.count()

    def buscar(self, pergunta: str, k: int, minimo: float = 0.0) -> list[tuple[Document, float]]:
        """Os trechos de significado mais parecido com a pergunta.

        Args:
            pergunta: Texto da pergunta (o Chroma gera o vetor dela com
                ``embed_query``, que aplica o prefixo de consulta).
            k: Quantos trechos pedir ao banco, no máximo.
            minimo: Similaridade de cosseno mínima para um trecho entrar.

        Returns:
            Pares (documento, similaridade de cosseno), do mais parecido para
            o menos. O documento traz o texto indexado e os metadados (fonte,
            seção, posição) gravados na indexação.

        Raises:
            ErroLLM: Se o Ollama falhar ao gerar o vetor da pergunta.
        """
        if k <= 0 or self.total() == 0:
            return []
        # similarity_search_with_score devolve a DISTÂNCIA de cosseno (0 =
        # idêntico, 2 = oposto). Convertemos para similaridade (1 = idêntico),
        # a mesma escala de config.RAG_SIMILARIDADE_MINIMA.
        # (O LangChain também tem similarity_search_with_relevance_scores, que
        # faz essa conta, mas emite avisos quando o cosseno dá negativo.)
        # min(k, total): pedir mais do que existe faz o Chroma emitir aviso.
        pares = self.vector_store.similarity_search_with_score(pergunta, k=min(k, self.total()))
        com_similaridade = [(doc, 1.0 - distancia) for doc, distancia in pares]
        # O Chroma já devolve do mais próximo para o mais distante; só cortamos
        # os que ficaram abaixo do mínimo.
        return [(doc, sim) for doc, sim in com_similaridade if sim >= minimo]
