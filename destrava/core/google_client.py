# Conexão com a API do Google Calendar (compartilhada por todos os agentes).
#
# O que este arquivo faz:
#   - Autenticação OAuth e criação do service do Google Calendar
#   - Funções básicas de acesso à API (sem regras de negócio dos agentes)
#
# Decisão do grupo sobre escopos:
#   get_service(escopos) recebe o escopo como PARÂMETRO, e cada agente pede
#   apenas o que precisa (princípio do menor privilégio):
#     - visualizar -> https://www.googleapis.com/auth/calendar.readonly
#     - criar / editar / excluir -> https://www.googleapis.com/auth/calendar
#   Assim, o agente de visualização continua sem permissão de escrita.
#
# Tokens:
#   Cada nível de escopo usa o seu próprio token (ex.: token_readonly.json e
#   token_calendar.json), pois um token só vale para os escopos autorizados.
#
# Segurança:
#   credentials.json e token*.json NUNCA devem ir para o Git (já estão no .gitignore).
