"""CLI do Destrava: agentes de visualização, criação e planejamento.

Visualizar e criar recebem um JSON e devolvem um JSON (sem LLM), no mesmo
formato: {"status", "acao", "periodo", "dados", "fluxo", "erro"}.

    1 visualizar  entrada: {"inicio": "...", "fim": "..."}
                  dados:   {"livres": [...], "total_minutos_livres": ...}
                  Se "fim" for igual a "inicio", o período vira o dia inteiro.

    2 criar       entrada: {"titulo": "...", "inicio": "...", "fim": "..."}
                  dados:   {"evento": {"id", "titulo", "inicio", "fim", "link"}}

Pedido inválido ou falha no Google: status "erro" e o campo "erro" preenchido.

As datas são ISO 8601 (ex.: "2026-11-04T14:00:00-03:00"); sem fuso, valem no
horário de config.FUSO. O formato completo está em docs/contrato.md.

    3 planejador  entrada: a descrição do projeto em texto livre e o prazo
                           (AAAA-MM-DD; Enter usa daqui a 14 dias)
                  saída:   {"tarefas": [{"etapa", "titulo", "objetivo",
                                         "entregaveis", "demonstracao",
                                         "dependencia", "story_points"}]}
                  Usa o RAG (base do Planejador) e o LLM, então precisa do
                  Ollama ligado e pode levar alguns minutos.

Uso (na raiz do projeto):
    python cli.py
    Agente: 1
    JSON: {"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05T00:00:00-03:00"}

    python cli.py
    Agente: 3
    Projeto: Construir uma API de cadastro de alunos com nome, RA e email.
    Prazo (AAAA-MM-DD, Enter = 2026-11-22):
"""

import json
from datetime import datetime, timedelta

from destrava.agents.criar import AgenteCriar
from destrava.agents.planejador import AgentePlanejador, ErroPlanejador
from destrava.agents.visualizar import AgenteVisualizar
from destrava.core import config

SAIR = ("sair", "exit", "quit")

# Prazo usado pelo planejador quando o usuário só aperta Enter.
PRAZO_PADRAO_DIAS = 14

# Agentes que recebem e devolvem JSON: escolha -> (nome, classe, exemplo).
AGENTES = {
    "1": ("visualizar", AgenteVisualizar, '{"inicio": "...", "fim": "..."}'),
    "2": ("criar", AgenteCriar, '{"titulo": "...", "inicio": "...", "fim": "..."}'),
}

PLANEJADOR = "3"


def rodar_json(escolha: str) -> bool:
    """Pede um JSON, chama o agente escolhido e imprime o JSON de resposta.

    Returns:
        False se o usuário digitou 'sair'; True caso contrário.
    """
    nome, classe, exemplo = AGENTES[escolha]
    print(f"Agente {nome}. Cole um JSON {exemplo}\n")

    entrada = input("JSON: ").strip()

    if entrada.lower() in SAIR:
        return False
    if not entrada:
        return True

    try:
        resposta = classe().executar_json(entrada)
        print(json.dumps(resposta, ensure_ascii=False, indent=2, default=str))
    except Exception as erro:
        print(f"[erro] {erro}")

    return True


def rodar_planejador() -> bool:
    """Pede o projeto e o prazo, chama o planejador e imprime o plano em JSON.

    Diferente dos outros agentes, o planejador recebe texto livre e pode
    levantar exceção (ErroPlanejador, ErroLLM...), tratada aqui.

    Returns:
        False se o usuário digitou 'sair'; True caso contrário.
    """
    print("Agente planejador. Descreva o projeto em texto livre.\n")

    projeto = input("Projeto: ").strip()

    if projeto.lower() in SAIR:
        return False
    if not projeto:
        return True

    padrao = (
        datetime.now(config.FUSO).date() + timedelta(days=PRAZO_PADRAO_DIAS)
    ).isoformat()
    prazo = input(f"Prazo (AAAA-MM-DD, Enter = {padrao}): ").strip() or padrao

    if prazo.lower() in SAIR:
        return False

    print("\nPlanejando... (na primeira vez a base é indexada, e pode demorar)\n")

    try:
        plano = AgentePlanejador().executar(projeto, prazo)
        print(json.dumps(plano, ensure_ascii=False, indent=2))
    except ErroPlanejador as erro:
        # O modelo respondeu, mas fora do formato esperado: mostra o que veio.
        print(f"[resposta fora do contrato] {erro}")
        print("Resposta original:")
        print(erro.resposta_original)
    except Exception as erro:
        print(f"[erro] {erro}")

    return True


def main():
    print(
        "Agentes: 1 = visualizar, 2 = criar, 3 = planejador. "
        "Digite 'sair' para encerrar.\n"
    )

    while True:
        escolha = input("Agente: ").strip().lower()

        if escolha in SAIR:
            break

        if escolha == PLANEJADOR:
            continuar = rodar_planejador()
        elif escolha in AGENTES:
            continuar = rodar_json(escolha)
        else:
            print("Opção inválida.\n")
            continue

        if not continuar:
            break

        print()


if __name__ == "__main__":
    main()
