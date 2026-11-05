"""Teste manual do RAG de uma base de conhecimento.

Mostra, para uma pergunta em texto livre, os trechos que o agente receberia
como contexto: a fonte, a seção, a nota e o método da busca. Com --prompt,
mostra o prompt montado; com --responder, gera a resposta com o LLM. Não usa o
Google.

Métodos:
    lexico   só palavras-chave (BM25). É o que roda sem o Ollama.
    hibrido  palavras-chave + embeddings (precisa do Ollama com o modelo
             config.MODELO_EMBEDDING: ollama pull nomic-embed-text).

Uso (na raiz do projeto, com -m para o Python encontrar o pacote destrava):
    python -m scripts.teste_rag supervisor "marca dentista amanhã às 15h"
    python -m scripts.teste_rag planejador "api de cadastro de alunos" --prompt
    python -m scripts.teste_rag supervisor "como criar um evento?" --responder
    python -m scripts.teste_rag supervisor            -> pede as perguntas, uma por vez

Opções:
    --sem-embeddings   nunca chama o Ollama (só palavras-chave)
    --prompt           mostra também o prompt montado (PROMPT_RAG)
    --responder        gera a resposta com o LLM (precisa do Ollama com config.MODELO)
    -k N               quantos trechos usar (padrão: config.RAG_TOP_K)

A primeira execução monta o índice e o salva em .rag_indices/ (ignorado pelo
git). Ele é refeito sozinho quando os arquivos da base mudam. Base vazia é
válida: o script diz que não há trechos.
"""

import argparse

from destrava.core import config
from destrava.rag import Rag

SAIR = ("sair", "exit", "quit")


def mostrar(rag: Rag, pergunta: str, k: int | None, prompt: bool, responder: bool) -> None:
    trechos = rag.buscar(pergunta, k)

    if not trechos:
        print("Nenhum trecho relevante." + (" (a base está vazia)" if rag.vazia else ""))
    for n, trecho in enumerate(trechos, start=1):
        print(f"[{n}] {trecho.score:.4f} ({trecho.metodo})  {trecho.fonte}")
        print(f"    {trecho.secao}")

    if prompt:
        print("\n--- prompt montado ---")
        print(rag.montar_prompt(pergunta, k=k).strip())
        print("----------------------")

    if responder:
        resposta = rag.responder(pergunta, k)
        origem = "LLM" if resposta.usou_llm else "texto fixo, sem LLM"
        print(f"\nResposta ({origem}):\n{resposta.resposta}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Testa o RAG de uma base de conhecimento.")
    parser.add_argument("base", choices=sorted(config.RAG_BASES), help="base de conhecimento")
    parser.add_argument("pergunta", nargs="*", help="pergunta em texto livre")
    parser.add_argument("--sem-embeddings", action="store_true")
    parser.add_argument("--prompt", action="store_true")
    parser.add_argument("--responder", action="store_true")
    parser.add_argument("-k", type=int, default=None)
    args = parser.parse_args()

    rag = Rag(args.base, usar_embeddings=False if args.sem_embeddings else None)
    modo = "palavras-chave + embeddings" if rag.usa_embeddings else "só palavras-chave"
    print(f"Base '{args.base}': {rag.total_trechos} trechos, busca por {modo}.\n")

    if args.pergunta:
        mostrar(rag, " ".join(args.pergunta), args.k, args.prompt, args.responder)
        return

    while True:
        pergunta = input("Pergunta: ").strip()
        if pergunta.lower() in SAIR:
            break
        if pergunta:
            mostrar(rag, pergunta, args.k, args.prompt, args.responder)


if __name__ == "__main__":
    main()
