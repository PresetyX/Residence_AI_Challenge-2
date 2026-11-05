# Contrato JSON dos agentes

Os agentes **recebem JSON e devolvem JSON, sem usar LLM**. Quem interpreta o pedido do usuário (texto livre) é o Supervisor; o agente só valida o que recebeu, fala com o Google Calendar e responde.

A função de entrada de cada agente é `executar_json(entrada)`.

Os dois agentes devolvem o **mesmo JSON** (`RespostaAgente`, em `destrava/core/models.py`); só muda o conteúdo de `acao` e de `dados`.

## Entrada

`entrada` pode ser um `dict` ou uma string JSON. As datas seguem o ISO 8601; sem fuso, valem no horário de `config.FUSO`. Os modelos de entrada ficam em `destrava/core/models.py`.

| Agente | Modelo | Entrada |
|---|---|---|
| visualizar | `PedidoVisualizacao` | `{"inicio": "...", "fim": "..."}` (se `fim` for igual a `inicio`, o período vira o dia inteiro) |
| criar | `PedidoCriacao` | `{"titulo": "...", "inicio": "...", "fim": "..."}` |

## Saída

```json
{
  "status": "sucesso",
  "acao": "agenda_visualizada",
  "periodo": {"inicio": "...", "fim": "...", "duracao_minutos": 1440.0},
  "dados": { "...": "específico de cada agente" },
  "fluxo": {
    "inicio": {"etapa": "validacao",       "status": "ok", "detalhe": {}},
    "meio":   {"etapa": "google_calendar", "status": "ok", "detalhe": null},
    "fim":    {"etapa": "calculo",         "status": "ok", "detalhe": null}
  },
  "erro": null
}
```

| Campo | O que é |
|---|---|
| `status` | `sucesso` ou `erro` |
| `acao` | o que aconteceu (tabela abaixo) |
| `periodo` | período tratado: `inicio`, `fim` (ISO 8601 com fuso) e `duracao_minutos`. `null` se o pedido for inválido |
| `dados` | resultado do agente. `null` em erro |
| `fluxo` | as 3 etapas (`inicio`, `meio`, `fim`), cada uma com `etapa`, `status` (`ok`, `erro` ou `pendente`) e `detalhe` |
| `erro` | `{"tipo", "mensagem"}` ou `null` |

| Agente | `acao` (sucesso / erro) | `dados` | Etapas do `fluxo` (`inicio` / `meio` / `fim`) |
|---|---|---|---|
| visualizar | `agenda_visualizada` / `agenda_nao_visualizada` | `livres` e `total_minutos_livres` | `validacao` / `google_calendar` / `calculo` |
| criar | `evento_criado` / `evento_nao_criado` | `evento` (`id`, `titulo`, `inicio`, `fim`, `link`) | `validacao` / `google_calendar` / `conferencia` |

Detalhes de cada agente: [visualizar.md](visualizar.md) e [criar.md](criar.md).

## Erros

Todo erro vira JSON, e o agente **não levanta exceção** em `executar_json`:

- **Pedido inválido** (título vazio, `fim` antes de `inicio`, data inválida, JSON quebrado...): o Google não é chamado, `fluxo.inicio.status = "erro"`, `meio` e `fim` ficam `pendente`, e `periodo` e `dados` são `null`.
- **Erro do Google** (sem permissão, sem rede, API sem resposta): `fluxo.meio.status = "erro"`, `fim` fica `pendente` e `periodo` é preenchido, porque o pedido era válido.

```json
{
  "status": "erro",
  "acao": "evento_nao_criado",
  "periodo": null,
  "dados": null,
  "fluxo": {
    "inicio": {"etapa": "validacao",       "status": "erro",     "detalhe": null},
    "meio":   {"etapa": "google_calendar", "status": "pendente", "detalhe": null},
    "fim":    {"etapa": "conferencia",     "status": "pendente", "detalhe": null}
  },
  "erro": {"tipo": "ValidationError", "mensagem": "..."}
}
```

## Regras de validação do criar

- `titulo` obrigatório (espaços nas pontas são removidos).
- `inicio` e `fim` obrigatórios, com `inicio` anterior ao `fim`.
- Não cria evento no passado.

## Regras de validação do visualizar

- `inicio` e `fim` em ISO 8601, os dois com fuso ou os dois sem fuso.
- `fim` não pode ser anterior a `inicio`; se for igual, o período vira o dia inteiro.

## Como testar

```
python -m pytest tests/
```

`tests/test_agentes_json.py` simula o Google, então não precisa de `credentials.json`.
