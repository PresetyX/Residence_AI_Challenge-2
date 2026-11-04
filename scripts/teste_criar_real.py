
"""
Teste interativo do Agente de Criação com o Google Calendar real.

Usa Gemma 2 para interpretar pedidos em linguagem natural.
Solicita confirmação antes de criar cada evento e mostra o JSON padrão
(agente, status, acao, mensagem, periodo, dados, fluxo inicio/meio/fim, erro).

Uso:
    python -m scripts.teste_criar_real
"""

from datetime import datetime

from destrava.agents.criar import AgenteCriar


def formatar_data(data_iso: str) -> str:
    """Converte a data ISO para um formato legível."""
    return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y às %H:%M")


def confirmar(dados: dict) -> bool:
    """Mostra o evento interpretado e pede a confirmação do usuário."""
    print("\n=== EVENTO INTERPRETADO ===")
    print("Título:", dados["titulo"])
    print("Início:", formatar_data(dados["inicio"]))
    print("Fim:", formatar_data(dados["fim"]))

    return input(
        "\nDigite CRIAR para adicionar o evento à agenda real: "
    ).strip() == "CRIAR"


def main():
    """Recebe pedidos, confirma os dados e cria eventos reais."""

    agente = AgenteCriar()

    print("=== DESTRAVA - AGENTE DE CRIAÇÃO ===")
    print("Digite 'sair' para encerrar.\n")

    while True:
        pedido = input("Você: ").strip()

        if pedido.lower() == "sair":
            break

        if not pedido:
            continue

        resposta = agente.executar_por_texto(pedido, confirmar=confirmar)

        print("\n=== RESPOSTA (JSON) ===")
        print(resposta.para_json())

        if resposta.status == "sucesso" and not resposta.dados["periodo_confere"]:
            print(
                "\n[aviso] O período salvo no Google é diferente do pedido. "
                "Confira o evento na agenda."
            )
        print()


if __name__ == "__main__":
    main()
