
"""
Teste manual do Agente de Criação sem acessar o Google Calendar.

Uso:
    py -3.15 -m scripts.teste_criar
"""

from unittest.mock import MagicMock

from destrava.agents.criar import criar_evento_google


def main():
    """Testa a criação de um evento com um serviço simulado."""

    servico_falso = MagicMock()

    servico_falso.events.return_value.insert.return_value.execute.return_value = {
        "id": "evento_teste_123",
        "summary": "Estudar Python"
    }

    dados = {
        "titulo": "Estudar Python",
        "inicio": "2027-11-29T14:00",
        "fim": "2027-11-29T16:00"
    }

    print("=== DADOS RECEBIDOS ===")
    print(dados)

    resultado = criar_evento_google(dados, servico_falso)

    print("\n=== RESULTADO DA CRIAÇÃO SIMULADA ===")
    print(resultado)

    print("\n=== DADOS ENVIADOS À API ===")
    print(servico_falso.events.return_value.insert.call_args)


if __name__ == "__main__":
    main()
