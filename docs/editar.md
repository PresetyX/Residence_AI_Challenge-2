# Agente Editar

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.
> Itens em *itálico* são orientações do que escrever. Troque pelo conteúdo real e apague a orientação.

## Objetivo

Altera eventos existentes a partir de um pedido em linguagem natural. O agente
preserva os campos não solicitados e nunca cria ou exclui eventos.

## Contrato

O que entra e o que sai, para o supervisor saber como chamá-lo.

| | |
|---|---|
| **Entrada** | texto: o pedido do usuário (ex.: "altere o título do evento abc123 para Reunião") |
| **Saída** | `{"evento": evento atualizado, "alteracoes": alterações aplicadas}` |
| **Função de entrada** | `editar_evento_agenda(servico, pedido) -> dict[str, Any]` |

## Fluxo

Quem faz cada passo: o LLM só interpreta e redige, o código fala com a API.

| # | Passo | Quem |
|---|---|---|
| 1 | Extrai o ID e as alterações do pedido em JSON (`PROMPT_EXTRACAO`) | LLM |
| 2 | Executa `get_evento` para obter a versão atual | Código |
| 3 | Mescla as alterações e executa `update_evento` | Código |
| 4 | Retorna o evento atualizado e as alterações aplicadas | Código |

## Regras

- Cada item recebido deve ter `id` e `alteracoes`.
- Para linguagem natural, use `editar_evento_agenda(servico, pedido)`.
- Exemplos aceitos: `altere o título do evento abc123 para Reunião` e
  `altere a data de término do evento abc123 para 2026-10-28 às 18:00`.
- O GET sempre ocorre antes do UPDATE, evitando sobrescrever uma versão
  desatualizada do evento.
- Campos não incluídos em `alteracoes` são preservados.
- O agente não resolve ambiguidades silenciosamente: o LLM deve retornar
  `null` quando não conseguir identificar um único evento.
- Tarefas do Google Tasks exibidas no Calendar não são editáveis por este
  agente. Elas devem ser alteradas pela Google Tasks API.

Os valores compartilhados (fuso, horários) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service` com o escopo de **escrita** (`calendar`),
  `get_evento` e `update_evento`.
- `llm_client`: `perguntar(prompt)`.
- `config`: `ESCOPO_CALENDARIO`
- `prompts/editar.py`: `PROMPT_EXTRACAO`.

## Como testar

```python
from destrava.agents.editar import editar_evento_agenda
resultado = editar_evento_agenda(
  servico,
  f"altere o título do evento {evento['id']} para 'Reunião' e mude a data de término para as 18h",
)
```

## Limitações

- Não guarda memória entre perguntas.
- Altera a agenda: exige o escopo de escrita.
- Pode alucinar se o pedido não for claro.
- Causa uma exceção se o evento não existir.
