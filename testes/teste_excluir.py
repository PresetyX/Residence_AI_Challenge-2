from destrava.agents.excluir import excluir_evento_agenda

print("=== TESTE DO AGENTE DE EXCLUSÃO ===")

pedido = "Exclua meu passeio com cachorro de amanhã"

print(f"\nUsuário: {pedido}")
print("\nExecutando o agente...\n")

resultado = excluir_evento_agenda(pedido)

print(f"Agente: {resultado}")
