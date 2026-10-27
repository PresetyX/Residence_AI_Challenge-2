# Agente Editar

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.
> Itens em *itálico* são orientações do que escrever. Troque pelo conteúdo real e apague a orientação.

## Objetivo

Altera um evento existente da agenda a partir de um pedido em linguagem natural.
*Escreva em 2 ou 3 linhas o que o agente faz e o que não faz.*

## Contrato

O que entra e o que sai, para o supervisor saber como chamá-lo.

| | |
|---|---|
| **Entrada** | texto: o pedido do usuário (ex.: "mude a reunião de sexta para as 16h") |
| **Saída** | texto em português confirmando o resultado |
| **Função de entrada** | `editar_evento_agenda(pedido: str) -> str` *(nome sugerido; confirmar com o grupo)* |

## Fluxo

Quem faz cada passo: o LLM só interpreta e redige, o código fala com a API.

| # | Passo | Quem |
|---|---|---|
| 1 | Extrai do pedido os dados em JSON (`PROMPT_EXTRACAO`) | LLM |
| 2 | Localiza o evento e aplica a alteração no Google Agenda | Código |
| 3 | Escreve a resposta final usando só os dados retornados (`PROMPT_RESPOSTA`) | LLM |

*Ajuste os passos se o seu agente tiver mais etapas.*

## Regras

*Defina as regras do agente.* Exemplos de decisões: como identificar o evento certo (título, data); o que fazer se houver mais de um candidato; quais campos podem ser alterados.

Os valores compartilhados (fuso, horários) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service` com o escopo de **escrita** (`calendar`).
- `llm_client`: `perguntar(prompt)`.
- `config`: *liste só o que este agente usa.*
- `prompts/editar.py`: `PROMPT_EXTRACAO` e `PROMPT_RESPOSTA`.

## Como testar

*Preencha quando o agente estiver rodando: o que precisa estar ativo e 3 a 5 pedidos de exemplo com o resultado esperado.*

## Limitações

- Não guarda memória entre perguntas.
- Altera a agenda: exige o escopo de escrita.
- *Acrescente as limitações reais que aparecerem.*
