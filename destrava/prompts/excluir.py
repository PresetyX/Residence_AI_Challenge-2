# Prompts do agente de excluir  (lógica do agente: destrava/agents/excluir.py)
#
# COMO ESTE ARQUIVO FUNCIONA
# Este arquivo guarda SOMENTE texto de prompt, sem lógica. Cada agente tem duas
# constantes (mesmos nomes em todos os agentes, para facilitar a leitura e a revisão):
#
#   PROMPT_EXTRACAO  (passo 1: o LLM entende o pedido)
#     - Entrada: a pergunta/pedido do usuário em linguagem natural.
#     - Saída esperada: APENAS JSON, que o código lê com json.loads().
#         {"evento": "..."}  (qual evento excluir, por título e/ou data; o formato exato é definido pelo dono do agente)
#     - Lacunas: {data_de_hoje}, {fuso}, {pergunta_do_usuario}
#     - Inclua 2 ou 3 exemplos (few-shot): com modelos pequenos como o Gemma 2,
#       exemplos funcionam melhor do que explicações longas.
#
#   PROMPT_RESPOSTA  (passo 2: o LLM escreve a resposta final)
#     - Entrada: dados JÁ calculados/obtidos pelo código (o evento excluído pelo código na API).
#     - Saída esperada: texto curto em português (confirmação do que foi excluído).
#     - Lacunas: {evento_excluido}, {pergunta_do_usuario}
#     - Deve mandar usar SOMENTE os dados informados e não inventar nada.
#
# REGRAS DO GRUPO
#   - Os prompts são modelos com lacunas {entre_chaves}; o agente preenche as
#     lacunas na hora de usar e envia o resultado para perguntar() (core/llm_client.py).
#   - Gemma 2 não tem papel "system": as instruções ficam dentro do próprio prompt.
#   - A data de hoje NUNCA é fixa: usar a lacuna {data_de_hoje}, preenchida pelo código.
#   - Quem cuida deste agente edita só este arquivo. As lacunas listadas acima são
#     uma sugestão inicial, o dono do agente pode ajustar.
"""Prompts usados pelo agente de exclusão de eventos."""


PROMPT_EXTRACAO = """
Você faz parte de um agente que exclui eventos do Google Calendar.
Sua única tarefa neste passo é interpretar o pedido do usuário e devolver os
dados necessários para o código localizar o evento.

Data de hoje: {data_de_hoje}
Fuso horário: {fuso}
Pedido do usuário: {pergunta_do_usuario}

Retorne APENAS um objeto JSON válido, sem markdown, sem explicações e sem texto
antes ou depois do JSON, exatamente com estas chaves:

{{
  "titulo": "texto do título ou null",
  "data": "AAAA-MM-DD ou null",
  "horario": "HH:MM ou null"
}}

Regras:
- "titulo" deve conter somente a parte do pedido que identifica o evento.
- Resolva datas relativas usando a data de hoje informada acima.
  Exemplos: hoje, amanhã, depois de amanhã, sexta-feira.
- "data" deve ser uma data absoluta no formato AAAA-MM-DD.
- Preencha "horario" somente quando o usuário informar ou deixar um horário
  claramente identificável. Caso contrário, use null.
- Não invente data, horário ou título.
- Se o usuário não informar uma data e ela não puder ser inferida, use null.
- Se o usuário não informar um título, use null.
- Não decida se o evento existe e não diga se ele deve ser excluído. O código
  fará essa verificação no Google Calendar.

Exemplos:

Data de hoje: 2026-10-27
Pedido: cancele o dentista de amanhã
Saída:
{{"titulo":"dentista","data":"2026-10-28","horario":null}}

Data de hoje: 2026-10-27
Pedido: apague a reunião Projeto IA de hoje às 14h
Saída:
{{"titulo":"reunião Projeto IA","data":"2026-10-27","horario":"14:00"}}

Data de hoje: 2026-10-27
Pedido: remova academia
Saída:
{{"titulo":"academia","data":null,"horario":null}}
""".strip()


PROMPT_RESPOSTA = """
Você escreve a resposta final de um agente que acabou de excluir um evento do
Google Calendar.

Pedido original do usuário:
{pergunta_do_usuario}

Dados do evento que o código realmente excluiu:
{evento_excluido}

Escreva uma confirmação curta e natural em português brasileiro, com no máximo
duas frases.

Regras:
- Use SOMENTE os dados informados acima.
- Não invente título, data, horário ou qualquer outra informação.
- Deixe claro que o evento foi excluído.
- Não mencione JSON, API, código, modelo ou detalhes técnicos.
""".strip()
