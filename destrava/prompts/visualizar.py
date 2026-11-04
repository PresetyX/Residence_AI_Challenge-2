# Prompts do agente de visualizar
# (lógica do agente: destrava/agents/visualizar.py)
#
# COMO ESTE ARQUIVO FUNCIONA
# Este arquivo guarda SOMENTE texto de prompt, sem lógica. Cada agente tem duas
# constantes (mesmos nomes em todos os agentes, para facilitar a leitura e a revisão):
#
#   PROMPT_EXTRACAO  (passo 1: o LLM entende o pedido)
#     - Entrada: a pergunta/pedido do usuário em linguagem natural.
#     - Saída esperada: APENAS JSON, que o código lê com json.loads().
#         {"inicio": "AAAA-MM-DDTHH:MM", "fim": "AAAA-MM-DDTHH:MM"}  (período a consultar)
#     - Lacunas: {data_de_hoje}, {fuso}, {pergunta_do_usuario}
#     - Inclui exemplos (few-shot): com modelos pequenos como o Gemma 2,
#       exemplos funcionam melhor do que explicações longas.
#
#   PROMPT_RESPOSTA  (passo 2: o LLM escreve a resposta final)
#     - Entrada: dados JÁ calculados/obtidos pelo código, só com as seções que o
#       usuário pediu (o código faz essa escolha antes de montar o prompt).
#     - Saída esperada: texto curto em português (resumo da agenda do período pedido).
#     - Lacunas: {pergunta_do_usuario}, {contexto}
#     - Deve mandar usar SOMENTE os dados informados e não inventar nada.
#
# REGRAS DO GRUPO
#   - Os prompts são modelos com lacunas {entre_chaves}; o agente preenche as
#     lacunas na hora de usar e envia o resultado para perguntar() (core/llm_client.py).
#   - Gemma 2 não tem papel "system": as instruções ficam dentro do próprio prompt.
#   - A data de hoje NUNCA é fixa: usar a lacuna {data_de_hoje}, preenchida pelo código.
#   - Quem cuida deste agente edita só este arquivo. As lacunas listadas acima são
#     uma sugestão inicial, o dono do agente pode ajustar.


# PROMPT_EXTRACAO: pedido do usuário -> JSON com o período
PROMPT_EXTRACAO = """Você extrai o período de uma pergunta sobre agenda.

Hoje é {data_de_hoje}.
Fuso horário: {fuso}.

Retorne APENAS um JSON válido, sem texto antes ou depois.

Formato:
{{"inicio": "AAAA-MM-DDTHH:MM", "fim": "AAAA-MM-DDTHH:MM"}}

Regras:
- "hoje" = o dia de hoje, das 00:00 até 23:59.
- "amanhã" = o dia seguinte, das 00:00 até 23:59.
- "essa semana" ou "esta semana" = de hoje até daqui 7 dias.
- "próximos 7 dias" = de hoje até daqui 7 dias.
- Se houver uma data específica, use esse dia inteiro.
- Se houver um intervalo de datas, use do primeiro dia até o último dia.
- Se não entender, use os próximos 7 dias.
- Não invente datas.
- Não explique nada.
- Responda apenas com o JSON.
- Se o pedido for para criar, editar ou excluir eventos, ainda assim retorne um período padrão (próximos 7 dias), pois a ação em si será tratada por outro agente.

Exemplos:

Pergunta: Quais horários livres eu tenho hoje?
Hoje é 2026-10-28.
Fuso horário: America/Sao_Paulo
Resposta: {{"inicio": "2026-10-28T00:00", "fim": "2026-10-28T23:59"}}

Pergunta: Me mostra meus compromissos de amanhã.
Hoje é 2026-10-28.
Fuso horário: America/Sao_Paulo
Resposta: {{"inicio": "2026-10-29T00:00", "fim": "2026-10-29T23:59"}}

Pergunta: Tenho conflitos no dia 30/10/2026?
Hoje é 2026-10-28.
Fuso horário: America/Sao_Paulo
Resposta: {{"inicio": "2026-10-30T00:00", "fim": "2026-10-30T23:59"}}

Pergunta: Como está minha semana?
Hoje é 2026-10-28.
Fuso horário: America/Sao_Paulo
Resposta: {{"inicio": "2026-10-28T00:00", "fim": "2026-11-04T23:59"}}

Pergunta: Quais são meus horários livres entre 30/10 e 01/11?
Hoje é 2026-10-28.
Fuso horário: America/Sao_Paulo
Resposta: {{"inicio": "2026-10-30T00:00", "fim": "2026-11-01T23:59"}}

Pergunta: {pergunta_do_usuario}
Hoje é {data_de_hoje}.
Fuso horário: {fuso}
Resposta:"""


# PROMPT_RESPOSTA: dados calculados -> texto final em português
# O código (agents/visualizar.py, função responder) já escolhe quais seções
# entram em {contexto}, conforme o que o usuário pediu (livres, ocupados ou
# conflitos). Assim o modelo não tem como mostrar o que não foi pedido.
PROMPT_RESPOSTA = """Você é o Agente de Visualização do Destrava.

Responda ao pedido do usuário usando SOMENTE os dados abaixo.
Inclua apenas as seções presentes nos dados — não invente seções que não foram informadas.

Pedido do usuário:
{pergunta_do_usuario}

Dados disponíveis:
{contexto}

Responda em português brasileiro, de forma curta e clara. Não invente nada."""
