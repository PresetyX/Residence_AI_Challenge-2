# Agente Editar

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Altera um evento existente do Google Agenda. Recebe o **ID** do evento e só os campos que mudam, em JSON, confere o evento no Google, aplica a alteração e devolve o evento atualizado em JSON. **Não usa LLM** e não interpreta texto livre: quem sabe qual é o evento (o painel Agenda do frontend) já manda o ID.

O Supervisor localiza o evento pelo título e data originais, mostra os dados da edição e só chama este agente depois de uma confirmação explícita ("sim"). Se mais de um evento corresponder, pede o horário de início antes de prosseguir. O painel Agenda também chama este agente diretamente após o usuário salvar o formulário.

## Contrato

Classe `AgenteEditar` em `destrava/tools/editar.py`, mesmo formato de resposta dos outros agentes ([`contrato.md`](contrato.md)).

| Método | Entrada | Saída |
|---|---|---|
| `executar_json(entrada)` | dict ou string JSON (`PedidoEdicao`) | dicionário `RespostaAgente` |

### Entrada

```json
{ "id": "abc123", "titulo": "Reunião com o time", "inicio": "2026-11-20T15:00", "fim": "2026-11-20T16:00" }
```

| Campo | Regra |
|---|---|
| `id` | Obrigatório (texto não vazio) |
| `titulo` | Opcional; se vier, não pode ficar vazio |
| `inicio`, `fim` | Opcionais, mas **vêm juntos** e `inicio` deve ser anterior a `fim`. Sem fuso, valem no horário de `config.FUSO` |
| `descricao`, `local` | Opcionais |

Campos ausentes ficam como estão no Google (o agente envia só o que mudou).

### Saída (sucesso)

`acao` = `evento_editado` e `dados.evento` com o evento atualizado (resumo do Google, pelo `evento_resumido`). `periodo` traz o início e o fim do evento. Etapas do `fluxo`: `validacao` / `google_calendar` / `conferencia`.

### Saída (erro)

`status` = `erro` e `acao` = `evento_nao_editado`, com `erro` = `{"tipo", "mensagem"}`. Pedido inválido não chama o Google; falha ou evento inexistente no Google marca `fluxo.meio` como erro.

## Quem chama

`AgenteSupervisor` no chat e `PUT /calendar/events/{id}` (`backend/calendario.py`) no painel Agenda do frontend. Ver [`supervisor.md`](supervisor.md) e [`api.md`](api.md).

## Dependências do core

- `google_client`: `get_service` com o escopo de **escrita** (`calendar`), `obter_evento` e `atualizar_evento`.
- `config`: `FUSO` e `ESCOPO_CALENDARIO`.
- `models`: `RespostaAgente`, `Fluxo`, `Etapa`, `Periodo`, `ErroInfo`.

## Como testar

```
python -m pytest tests/test_calendario_api.py
```

Os testes simulam o Google, então não precisam de `credentials.json`.

## Limitações

- Não guarda memória entre pedidos.
- Altera a agenda de verdade: exige o escopo de escrita (`token_calendar.json`).
- Não interpreta linguagem natural: precisa do ID do evento.
