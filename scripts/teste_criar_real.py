"""
Teste interativo do Agente de Criação com o Google Calendar real.

Usa Gemma 2 para interpretar pedidos em linguagem natural.
Solicita confirmação antes de criar cada evento e mostra a resposta em texto.
Para testar o caminho em JSON (sem LLM), use: python cli.py (agente 2).

Uso:
    python -m scripts.teste_criar_real
"""

import json
from datetime import datetime

from pydantic import ValidationError

from destrava.agents.criar import AgenteCriar
from destrava.core.models import PedidoCriacao


def formatar_data(data_iso: str) -> str:
    """Converte a data ISO para um formato legível."""
    return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y às %H:%M")


def confirmar(dados: dict) -> bool:
    """Mostra o evento interpretado e pede a confirmação do usuário."""
    print("\n=== EVENTO A CRIAR ===")
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

    print('Exemplo: {"titulo": "Dentista", "inicio": "2026-11-15T15:00", "fim": "2026-11-15T16:00"}\n')

    while True:
        entrada = input("JSON: ").strip()

        if entrada.lower() == "sair":
            break

        if not entrada:
            continue

        try:
            pedido = PedidoCriacao.model_validate_json(entrada) 
        except ValidationError as erro:
            print(f"[pedido inválido] {erro}")
            continue

        confirmar({"titulo": pedido.titulo, "inicio": pedido.inicio.isoformat(),
                   "fim": pedido.fim.isoformat()})
        if not confirmar({"titulo": pedido.titulo,
                          "inicio": pedido.inicio.isoformat(),
                          "fim": pedido.fim.isoformat()}):
            print("\nCriação cancelada. Nada foi alterado na agenda.\n")
            continue

        try:
            resposta = agente.executar_json(entrada)
        except Exception as erro:
            print(f"\n[erro] {erro}\n")
            continue

        print("\n=== RESPOSTA ===")
        print(json.dumps(resposta, ensure_ascii=False, indent=2))
        print()

if __name__ == "__main__":
    main()
