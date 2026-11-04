# Agente Criar

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Cria um evento no Google Agenda a partir de um JSON com título, início e fim (ou, no caminho em texto, de um pedido em linguagem natural).
Não edita nem exclui eventos, e não verifica conflito com outros compromissos.

## Contrato

O que entra e o que sai, para o supervisor saber como chamá-lo. O formato completo está em [contrato.md](contrato.md).

| | |
|---|---|
| **Entrada** | JSON (`dict` ou string): `{"titulo": "...", "inicio": "...", "fim": "..."}` (ISO 8601; sem fuso vale `config.FUSO`) |
| **Saída** | JSON: `{"evento": {"id", "titulo", "inicio", "fim", "link"}}` ou `{"erro": "Pedido inválido", "detalhes": [...]}` |
| **Função de entrada** | `AgenteCriar().executar_json(entrada) -> dict` (sem LLM) |
| **Caminho em texto** | `AgenteCriar().executar_por_texto(pedido, confirmar=None) -> str` (LLM extrai o evento e escreve a resposta) |

## Fluxo

Caminho em JSON (`executar_json`), sem LLM:

| # | Passo | Quem |
|---|---|---|
| 1 | Valida o pedido com o `PedidoCriacao` (`core/models.py`) | Código |
| 2 | Cria o evento no Google Agenda (`criar_evento_google`) | Código |
| 3 | Devolve o evento criado em JSON | Código |

Caminho em texto (`executar_por_texto`):

| # | Passo | Quem |
|---|---|---|
| 1 | Extrai título, início e fim do pedido em JSON (`PROMPT_EXTRACAO`) | LLM |
| 2 | Pede confirmação, se `confirmar` foi passado | Código |
| 3 | Cria o evento no Google Agenda | Código |
| 4 | Escreve a resposta final usando só os dados retornados (`PROMPT_RESPOSTA`) | LLM |

## Regras

- `titulo` obrigatório (espaços nas pontas são removidos).
- `inicio` e `fim` obrigatórios, com `inicio` anterior ao `fim`.
- Não cria evento no passado.
- Datas sem fuso valem no horário de `config.FUSO`.
- Pedido inválido não chama o Google: devolve `{"erro": "Pedido inválido", ...}`.

Os valores compartilhados (fuso, horários) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service` com o escopo de **escrita** (`calendar`).
- `llm_client`: `perguntar(prompt)` e `extrair_json(texto)` (só no caminho em texto).
- `models`: `PedidoCriacao`.
- `config`: `FUSO` e `ESCOPO_CALENDARIO`.
- `prompts/criar.py`: `PROMPT_EXTRACAO` e `PROMPT_RESPOSTA`.

## Como testar

Sem Google e sem Ollama: `python -m pytest tests/` (o Google é simulado e o LLM é bloqueado no caminho em JSON).

Com o Google real (precisa do `credentials.json` na raiz): `python cli.py`, escolha o agente `2` e cole, por exemplo:

```
{"titulo": "Dentista", "inicio": "2026-11-15T15:00", "fim": "2026-11-15T16:00"}
```

Para testar o caminho em texto (precisa do Ollama): `python -m scripts.teste_criar_real`.

## Limitações

- Não guarda memória entre perguntas.
- Altera a agenda: exige o escopo de escrita.
- Cria o evento na agenda principal e não avisa se ele conflita com outros compromissos.
