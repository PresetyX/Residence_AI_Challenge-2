# Contrato JSON dos agentes

Os agentes **recebem JSON e devolvem JSON, sem usar LLM**. Quem interpreta o pedido do usuário (texto livre) é o Supervisor; o agente só valida o que recebeu, fala com o Google Calendar e responde.

Cada agente também tem `executar_por_texto(...)`, um caminho opcional em que o LLM entende o pedido e escreve a resposta. O contrato abaixo vale para o caminho em JSON: `executar_json(entrada)`.

## Entrada

`entrada` pode ser um `dict` ou uma string JSON. As datas seguem o ISO 8601; sem fuso, valem no horário de `config.FUSO`. Os modelos de entrada ficam em `destrava/core/models.py`.

| Agente | Modelo | Entrada |
|---|---|---|
| visualizar | `PedidoVisualizacao` | `{"inicio": "...", "fim": "..."}` (se `fim` for igual a `inicio`, o período vira o dia inteiro) |
| criar | `PedidoCriacao` | `{"titulo": "...", "inicio": "...", "fim": "..."}` |

## Saída

| Agente | Saída |
|---|---|
| visualizar | `{"livres": [...], "total_minutos_livres": ...}` |
| criar | `{"evento": {"id", "titulo", "inicio", "fim", "link"}}` |

```json
{
  "evento": {
    "id": "abc123",
    "titulo": "Dentista",
    "inicio": "2026-11-15T15:00:00-03:00",
    "fim": "2026-11-15T16:00:00-03:00",
    "link": "https://www.google.com/calendar/event?eid=..."
  }
}
```

## Pedido inválido

Se a entrada não passar na validação, o agente **não chama o Google** e devolve:

```json
{
  "erro": "Pedido inválido",
  "detalhes": [
    {"type": "value_error", "loc": ["titulo"], "msg": "Value error, O título do evento é obrigatório.", "input": ""}
  ]
}
```

Erros da API do Google (sem permissão, sem rede etc.) **não** viram JSON: a exceção sobe para quem chamou.

## Regras de validação do criar

- `titulo` obrigatório (espaços nas pontas são removidos).
- `inicio` e `fim` obrigatórios, com `inicio` anterior ao `fim`.
- Não cria evento no passado.

## Como testar

```
python -m pytest tests/
```

`tests/test_agentes_json.py` simula o Google e bloqueia o LLM (o teste falha se o caminho em JSON tentar chamá-lo), então não precisa de `credentials.json` nem do Ollama.
