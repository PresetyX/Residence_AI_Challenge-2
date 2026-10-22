# Configurações globais do projeto.
#
# O que este arquivo guarda (somente valores, sem lógica):
#   - Fuso horário (ex.: America/Sao_Paulo)
#   - Horário de trabalho (início e fim do expediente)
#   - Nome do modelo usado no Ollama (ex.: gemma2:2b para desenvolver, gemma2:9b para o final)
#
# Decisões do grupo:
#   - Trocar de modelo é mudar apenas o nome aqui; llm_client.py lê este valor.
#   - O escopo do OAuth NÃO fica aqui: cada agente informa o escopo de que precisa
#     ao chamar get_service() (ver google_client.py).
#   - Regras de negócio de cada agente ficam no próprio agente, não aqui.
