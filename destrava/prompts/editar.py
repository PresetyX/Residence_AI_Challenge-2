# Prompts do agente de editar  (lógica do agente: destrava/agents/editar.py)
#
# COMO ESTE ARQUIVO FUNCIONA
# Este arquivo guarda SOMENTE texto de prompt, sem lógica. Cada agente tem duas
# constantes (mesmos nomes em todos os agentes, para facilitar a leitura e a revisão):
#
#   PROMPT_EXTRACAO  (passo 1: o LLM entende o pedido)
#     - Entrada: a pergunta/pedido do usuário em linguagem natural.
#     - Saída esperada: APENAS JSON, que o código lê com json.loads().
#         {"evento": "...", "novos_campos": {...}}  (qual evento alterar e o que mudar; o formato exato é definido pelo dono do agente)
#     - Lacunas: {data_de_hoje}, {fuso}, {pergunta_do_usuario}
#     - Inclua 2 ou 3 exemplos (few-shot): com modelos pequenos como o Gemma 2,
#       exemplos funcionam melhor do que explicações longas.
#
# REGRAS DO GRUPO
#   - Os prompts são modelos com lacunas {entre_chaves}; o agente preenche as
#     lacunas na hora de usar e envia o resultado para perguntar() (core/llm_client.py).
#   - Gemma 2 não tem papel "system": as instruções ficam dentro do próprio prompt.
#   - A data de hoje NUNCA é fixa: usar a lacuna {data_de_hoje}, preenchida pelo código.
PROMPT_EXTRACAO = """\
Você é um agente que interpreta pedidos para editar eventos do Google Calendar.
Responda SOMENTE com JSON válido, sem markdown, neste formato:
{{"evento_id": "id do evento", "alteracoes": {{"campo": "novo valor"}}}}

Regras:
- Use apenas os campos que o usuário pediu para alterar.
- Preserve os demais campos do evento.
- Para data e hora, use RFC 3339 e o fuso {fuso}.
- Converta horários de 12 horas: "5:30 da tarde" significa
  "17:30:00", e "5:30 da noite" também significa "17:30:00"; nunca use
  "05:30:00" nesses casos.
- "hoje" significa {data_de_hoje}; "amanhã" significa o dia seguinte a
  {data_de_hoje}.
- "depois de amanhã" significa dois dias depois de {data_de_hoje}.
- Quando o usuário disser "a data do evento", altere a data de início e a
  data de término, preservando os horários e a duração do evento.
- Para alterar apenas o fim, mantenha a mesma data do início do evento quando
  o usuário não informar uma data, "hoje" ou "amanhã".
- Se não houver informação suficiente para identificar um único evento ou a
  alteração, use null no campo correspondente e não invente valores.
- A data de hoje é {data_de_hoje}.

Exemplos:
Pedido: "mude o título do evento abc123 para Reunião semanal"
Resposta: {{"evento_id": "abc123", "alteracoes": {{"summary": "Reunião semanal"}}}}

Pedido: "altere a data de término do evento abc123 para 2026-10-28 às 18:00"
Resposta: {{"evento_id": "abc123", "alteracoes": {{"end": {{"dateTime": "2026-10-28T18:00:00-03:00", "timeZone": "{fuso}"}}}}}}

Pedido: "altere o horário de término do evento abc123 para 18:00"
Resposta: {{"evento_id": "abc123", "alteracoes": {{"end": {{"dateTime": "AAAA-MM-DDT18:00:00-03:00", "timeZone": "{fuso}"}}}}}}

Pedido do usuário: {pergunta_do_usuario}
"""

FERRAMENTAS = (
    "get_evento(evento_id, id_calendario='primary')",
    "update_evento(evento_id, evento, id_calendario='primary')",
)
