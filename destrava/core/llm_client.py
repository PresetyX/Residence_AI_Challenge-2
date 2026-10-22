# Chamada ao modelo Gemma 2, rodando local via Ollama (compartilhada por todos os agentes).
#
# O que este arquivo faz:
#   - Envia um prompt ao Ollama (localhost:11434) e devolve a resposta em texto
#   - Lê o nome do modelo de config.py (nada de nome de modelo fixo aqui)
#
# Interface combinada com o grupo:
#   perguntar(prompt: str) -> str
#
# Observações sobre o Gemma 2:
#   - O template dele não tem papel "system": as instruções vão dentro da
#     mensagem do usuário, junto com a pergunta.
#   - Ele não tem function calling nativo: os agentes devem pedir a saída em
#     formato fixo (ex.: JSON) e o código valida a resposta.
#
# Os prompts ficam na pasta prompts/, não aqui.
