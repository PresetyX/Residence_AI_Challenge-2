# Prompts do agente de visualizar  (lógica do agente: destrava/agents/visualizar.py)
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
#     - Inclua 2 ou 3 exemplos (few-shot): com modelos pequenos como o Gemma 2,
#       exemplos funcionam melhor do que explicações longas.
#
#   PROMPT_RESPOSTA  (passo 2: o LLM escreve a resposta final)
#     - Entrada: dados JÁ calculados/obtidos pelo código (eventos, horários livres e conflitos).
#     - Saída esperada: texto curto em português (resumo da agenda do período pedido).
#     - Lacunas: {eventos}, {livres}, {conflitos}, {pergunta_do_usuario}
#     - Deve mandar usar SOMENTE os dados informados e não inventar nada.
#
# REGRAS DO GRUPO
#   - Os prompts são modelos com lacunas {entre_chaves}; o agente preenche as
#     lacunas na hora de usar e envia o resultado para perguntar() (core/llm_client.py).
#   - Gemma 2 não tem papel "system": as instruções ficam dentro do próprio prompt.
#   - A data de hoje NUNCA é fixa: usar a lacuna {data_de_hoje}, preenchida pelo código.
#   - Quem cuida deste agente edita só este arquivo. As lacunas listadas acima são
#     uma sugestão inicial, o dono do agente pode ajustar.
