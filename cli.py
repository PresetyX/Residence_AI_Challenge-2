"""CLI do Destrava: agente de visualização da agenda.

Contrato: recebe um JSON com o período ("inicio" e "fim", ISO 8601) e
devolve um JSON com os horários livres e o total de minutos livres.
Se "fim" for igual a "inicio", o período vira o dia inteiro.

Uso (na raiz do projeto):
    python cli.py
    JSON: {"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05T00:00:00-03:00"}
"""

import json

from destrava.agents.visualizar import AgenteVisualizar


def main():
    agente = AgenteVisualizar()

    print('Cole um JSON {"inicio": "...", "fim": "..."} (ou "sair").\n')

    while True:
        entrada = input("JSON: ").strip()

        if entrada.lower() in ("sair", "exit", "quit"):
            break
        if not entrada:
            continue

        try:
            resposta = agente.executar_json(entrada)
            print(json.dumps(resposta, ensure_ascii=False, indent=2))
        except Exception as erro:
            print(f"[erro] {erro}")


if __name__ == "__main__":
    main()
