"""Teste manual do RAG do Supervisor.

Mostra, para um pedido em texto livre, os trechos que o Supervisor receberia
como contexto: a fonte, a seção, a nota e o método da busca. Não usa o Google.

Métodos:
    lexico   só palavras-chave (BM25). É o que roda sem o Ollama.
    hibrido  palavras-chave + embeddings (precisa do Ollama com o modelo
             config.MODELO_EMBEDDING: ollama pull nomic-embed-text).

Uso (na raiz do projeto, com -m para o Python encontrar o pacote destrava):
    python -m scripts.teste_rag "marca dentista amanhã às 15h"
    python -m scripts.teste_rag --sem-embeddings "tenho horário livre amanhã?"
    python -m scripts.teste_rag --contexto "cancela a reunião de sexta"
    python -m scripts.teste_rag            -> pede os pedidos, um por vez ("sair" encerra)

Opções:
    --sem-embeddings   nunca chama o Ollama (só palavras-chave)
    --contexto         mostra também o texto exato que vai para o prompt
    -k N               quantos trechos mostrar (padrão: config.RAG_TOP_K)

A primeira execução monta o índice e o salva em .rag_indice.json (ignorado
pelo git). Ele é refeito sozinho quando os .md das fontes mudam.
"""

import argparse

from destrava.rag import RagSupervisor

SAIR = ("sair", "exit", "quit")


def mostrar(rag: RagSupervisor, pedido: str, k: int | None, com_contexto: bool) -> None:
    resultado = rag.buscar(pedido, k)

    if not resultado:
        print("Nenhum trecho relevante.\n")
        return

    for n, trecho in enumerate(resultado, start=1):
        print(f"[{n}] {trecho.score:.4f} ({trecho.metodo})  {trecho.fonte}")
        print(f"    {trecho.secao}")

    if com_contexto:
        print("\n--- contexto enviado ao prompt ---")
        print(rag.contexto(pedido, k))
        print("----------------------------------")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Testa o RAG do Supervisor.")
    parser.add_argument("pedido", nargs="*", help="pedido em texto livre")
    parser.add_argument("--sem-embeddings", action="store_true")
    parser.add_argument("--contexto", action="store_true")
    parser.add_argument("-k", type=int, default=None)
    args = parser.parse_args()

    rag = RagSupervisor(usar_embeddings=False if args.sem_embeddings else None)
    modo = "palavras-chave + embeddings" if rag.usa_embeddings else "só palavras-chave"
    print(f"RAG pronto: {rag.total_trechos} trechos, busca por {modo}.\n")

    if args.pedido:
        mostrar(rag, " ".join(args.pedido), args.k, args.contexto)
        return

    while True:
        pedido = input("Pedido: ").strip()
        if pedido.lower() in SAIR:
            break
        if pedido:
            mostrar(rag, pedido, args.k, args.contexto)


if __name__ == "__main__":
    main()
