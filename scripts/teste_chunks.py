"""Mostra quantos chunks cada base tem: no chunking e já indexados no Chroma.

Não chama o Ollama nem gera embeddings: só lê os arquivos e abre o banco
existente em .rag_indices/ (se houver).

Uso (na raiz do projeto):
    python -m scripts.teste_chunks
"""

from destrava.core import config
from destrava.core.llm_client import criar_embeddings
from destrava.rag.banco_vetorial import BancoVetorial
from destrava.rag.indice import assinatura_do_modelo, construir_indice


def main() -> None:
    print(f"{'base':<14}{'chunks (arquivos)':>20}{'indexados (Chroma)':>22}")
    for nome in sorted(config.RAG_BASES):
        esperados = len(construir_indice(nome, usar_embeddings=False).trechos)
        pasta = config.PASTA_INDICES_RAG / nome / assinatura_do_modelo() / "chroma"
        if pasta.is_dir():
            indexados = str(BancoVetorial(pasta, criar_embeddings()).total())
        else:
            indexados = "sem índice"
        print(f"{nome:<14}{esperados:>20}{indexados:>22}")


if __name__ == "__main__":
    main()
