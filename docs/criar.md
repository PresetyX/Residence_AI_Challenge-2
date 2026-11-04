# Agente Criar

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Cria um evento no Google Agenda a partir de um JSON com título, início e fim. **Não usa LLM**: recebe um JSON e devolve um JSON.
Não edita nem exclui eventos, e não verifica conflito com outros compromissos.

## Contrato

O que entra e o que sai, para o supervisor saber como chamá-lo. O formato completo está em [contrato.md](contrato.md).

| | |
|---|---|
| **Entrada** | JSON (`dict` ou string): `{"titulo": "...", "inicio": "...", "fim": "..."}` (ISO 8601; sem fuso vale `config.FUSO`) |
| **Saída** | JSON: `{"evento": {"id", "titulo", "inicio", "fim", "link"}}` ou `{"erro": "Pedido inválido", "detalhes": [...]}` |
| **Função de entrada** | `AgenteCriar().executar_json(entrada) -> dict` |

O `executar_json` recebe **um único parâmetro**, `entrada`. Não há parâmetro de confirmação: quem precisa confirmar com o usuário (o Supervisor, por exemplo) deve fazer isso **antes** de chamar o agente.

## Fluxo

| # | Passo | Quem |
|---|---|---|
| 1 | Valida o pedido com o `PedidoCriacao` (`core/models.py`) | Código |
| 2 | Cria o evento no Google Agenda (`criar_evento_google`) | Código |
| 3 | Devolve o evento criado em JSON | Código |

## Regras

- `titulo` obrigatório (espaços nas pontas são removidos).
- `inicio` e `fim` obrigatórios, com `inicio` anterior ao `fim`.
- Não cria evento no passado.
- Datas sem fuso valem no horário de `config.FUSO`.
- Pedido inválido não chama o Google: devolve `{"erro": "Pedido inválido", ...}`.
- Erros da API do Google (sem permissão, sem rede etc.) **não** viram JSON: a exceção sobe para quem chamou.

Os valores compartilhados (fuso, horários) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service` com o escopo de **escrita** (`calendar`).
- `models`: `PedidoCriacao`.
- `config`: `FUSO` e `ESCOPO_CALENDARIO`.

## Como testar

Sem Google: `python -m pytest tests/` (o Google é simulado).

Com o Google real (precisa do `credentials.json` na raiz): `python cli.py`, escolha o agente `2` e cole, por exemplo:

```
{"titulo": "Dentista", "inicio": "2026-11-15T15:00", "fim": "2026-11-15T16:00"}
```

Ou, com confirmação antes de criar: `python -m scripts.teste_criar_real`.

## Limitações

- Altera a agenda: exige o escopo de escrita.
- Cria o evento na agenda principal e não avisa se ele conflita com outros compromissos.
- Erros do Google sobem como exceção (diferente do visualizar, que devolve JSON de erro). Formato a alinhar com o time.
