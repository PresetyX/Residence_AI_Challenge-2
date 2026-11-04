"""CLI do Destrava: agentes de visualização e criação da agenda.

Contrato: cada agente recebe um JSON e devolve um JSON (sem LLM).

    visualizar  entrada: {"inicio": "...", "fim": "..."}
                saída:   {"livres": [...], "total_minutos_livres": ...}
                Se "fim" for igual a "inicio", o período vira o dia inteiro.

    criar       entrada: {"titulo": "...", "inicio": "...", "fim": "..."}
                saída:   {"evento": {"id", "titulo", "inicio", "fim", "link"}}

As datas são ISO 8601 (ex.: "2026-11-04T14:00:00-03:00"); sem fuso, valem no
horário de config.FUSO. Pedido inválido devolve {"erro": "Pedido inválido", ...}.

Uso (na raiz do projeto):
    python cli.py
    Agente: 1
    JSON: {"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05T00:00:00-03:00"}
"""

import json

from destrava.agents.criar import AgenteCriar
from destrava.agents.visualizar import AgenteVisualizar

SAIR = ("sair", "exit", "quit")

AGENTES = {
    "1": ("visualizar", AgenteVisualizar, '{"inicio": "...", "fim": "..."}'),
    "2": ("criar", AgenteCriar, '{"titulo": "...", "inicio": "...", "fim": "..."}'),
}


def main():
    print("Agentes: 1 = visualizar, 2 = criar. Digite 'sair' para encerrar.\n")

    while True:
        escolha = input("Agente: ").strip().lower()

        if escolha in SAIR:
            break
        if escolha not in AGENTES:
            print("Opção inválida.\n")
            continue

        nome, classe, exemplo = AGENTES[escolha]
        print(f"Agente {nome}. Cole um JSON {exemplo}\n")

        entrada = input("JSON: ").strip()

        if entrada.lower() in SAIR:
            break
        if not entrada:
            continue

        try:
            resposta = classe().executar_json(entrada)
            print(json.dumps(resposta, ensure_ascii=False, indent=2, default=str))
        except Exception as erro:
            print(f"[erro] {erro}")

        print()


if __name__ == "__main__":
    main()
