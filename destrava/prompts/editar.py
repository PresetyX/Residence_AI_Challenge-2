# Prompts do agente de editar  (lógica do agente: destrava/agents/editar.py)
#
# COMO ESTE ARQUIVO FUNCIONA
# Este arquivo guarda SOMENTE texto de prompt, sem lógica. Cada agente tem uma
# constante (mesmo nome em todos os agentes, para facilitar a leitura e a revisão):
#
#   PROMPT_EXTRACAO  (passo 1: o LLM entende o pedido)
#     - Entrada: a pergunta/pedido do usuário em linguagem natural.
#     - Saída esperada: APENAS JSON, que o código lê com json.loads().
#         {"evento": "...", "novos_campos": {...}}  (qual evento alterar e o que mudar; o formato exato é definido pelo dono do agente)
#     - Lacunas: {data_de_hoje}, {fuso}, {pergunta_do_usuario}
#     - Inclua 2 ou 3 exemplos (few-shot): com modelos pequenos como o Gemma 2,
#       exemplos funcionam melhor do que explicações longas.
#
#   A resposta ao usuário NÃO usa LLM: o texto é montado pelo código do agente
#   (montar_mensagem em agents/editar.py), para a saída ser mais rápida.
#
# REGRAS DO GRUPO
#   - Os prompts são modelos com lacunas {entre_chaves}; o agente preenche as
#     lacunas na hora de usar e envia o resultado para perguntar() (core/llm_client.py).
#   - Gemma 2 não tem papel "system": as instruções ficam dentro do próprio prompt.
#   - A data de hoje NUNCA é fixa: usar a lacuna {data_de_hoje}, preenchida pelo código.
#   - Quem cuida deste agente edita só este arquivo. As lacunas listadas acima são
#     uma sugestão inicial, o dono do agente pode ajustar.
