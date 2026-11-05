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
| **Saída** | JSON no mesmo formato do visualizar: `{"status", "acao", "periodo", "dados", "fluxo", "erro"}`, com `dados` = `{"evento": {"id", "titulo", "inicio", "fim", "link"}}` |
| **Função de entrada** | `AgenteCriar().executar_json(entrada) -> dict` |

O `executar_json` recebe **um único parâmetro**, `entrada`. Não há parâmetro de confirmação: quem precisa confirmar com o usuário (o Supervisor, por exemplo) deve fazer isso **antes** de chamar o agente.

## Saída

Sucesso:

```json
{
  "status": "sucesso",
  "acao": "evento_criado",
  "periodo": {"inicio": "2026-11-15T15:00:00-03:00", "fim": "2026-11-15T16:00:00-03:00", "duracao_minutos": 60.0},
  "dados": {
    "evento": {
      "id": "abc123",
      "titulo": "Dentista",
      "inicio": "2026-11-15T15:00:00-03:00",
      "fim": "2026-11-15T16:00:00-03:00",
      "link": "https://www.google.com/calendar/event?eid=..."
    }
  },
  "fluxo": {
    "inicio": { "etapa": "validacao",       "status": "ok", "detalhe": { "titulo": "...", "inicio": "...", "fim": "..." } },
    "meio":   { "etapa": "google_calendar", "status": "ok", "detalhe": { "evento_id": "abc123" } },
    "fim":    { "etapa": "conferencia",     "status": "ok", "detalhe": { "periodo_confere": true } }
  },
  "erro": null
}
```

Erro (ex.: título vazio): `status: "erro"`, `acao: "evento_nao_criado"`, `periodo` e `dados` nulos, `fluxo.inicio.status = "erro"` (as outras etapas ficam `pendente`) e `erro: {"tipo", "mensagem"}`. Nada é criado.

| Campo | O que é |
|---|---|
| `status` | `sucesso` ou `erro` |
| `acao` | `evento_criado` ou `evento_nao_criado` |
| `periodo` | período do evento pedido, com `duracao_minutos`. Fica `null` se o pedido for inválido |
| `dados` | `evento` criado. Fica `null` em erro |
| `fluxo` | as 3 etapas, cada uma com `status` `ok`, `erro` ou `pendente` |
| `erro` | `{"tipo", "mensagem"}` ou `null` |

## Fluxo

| Etapa | Nome no JSON | O que faz |
|---|---|---|
| `inicio` | `validacao` | `PedidoCriacao` (`core/models.py`) valida o JSON de entrada |
| `meio` | `google_calendar` | cria o evento no Google Agenda (`criar_evento_google`) |
| `fim` | `conferencia` | confere se o início e o fim devolvidos pelo Google são os pedidos (`fluxo.fim.detalhe.periodo_confere`) |

Regras do fluxo:

- Erro na `validacao`: o Google não é chamado, e `meio` e `fim` ficam `pendente`.
- Erro no `google_calendar` (credencial, rede, permissão, API sem o id do evento): `meio` vira `erro`, `fim` fica `pendente`, e `periodo` é preenchido porque o pedido era válido.
- Se o Google devolver outro período, o evento é criado e a resposta é `sucesso`, com `periodo_confere: false` na `conferencia`.
- O `executar_json` **não levanta exceção**: todo erro vira JSON.

## Regras

- `titulo` obrigatório (espaços nas pontas são removidos).
- `inicio` e `fim` obrigatórios, com `inicio` anterior ao `fim`.
- Não cria evento no passado.
- Datas sem fuso valem no horário de `config.FUSO`.
- Pedido inválido não chama o Google: devolve `status: "erro"`.

Os valores compartilhados (fuso, horários) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service` com o escopo de **escrita** (`calendar`).
- `models`: `PedidoCriacao` (entrada) e `RespostaAgente`, `Periodo`, `Fluxo`, `Etapa`, `ErroInfo` (saída, compartilhados com o visualizar).
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
