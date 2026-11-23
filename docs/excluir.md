# Agente Excluir

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Exclui um evento do Google Agenda a partir do **ID**. Confere que o evento existe e não está cancelado, exclui e devolve o resultado em JSON. **Não usa LLM** e não interpreta texto livre. Como a exclusão não tem volta, a **confirmação do usuário acontece antes** da chamada (no painel Agenda, que mostra o modal de exclusão).

Por enquanto o Supervisor não chama este agente: pedidos de exclusão no chat voltam como `indisponivel` e o chat oferece o painel manual.

## Contrato

Arquivo `destrava/agents/excluir.py`.

| Função ou método | Entrada | Saída |
|---|---|---|
| `AgenteExcluir().executar_json(entrada)` | `{"id": "..."}` | dicionário `RespostaAgente` ([`contrato.md`](contrato.md)) |
| `excluir_evento_agenda(id_evento)` | ID do evento | `{"sucesso", "codigo", "id_evento", "mensagem"}` |

Códigos de `excluir_evento_agenda`:

| `codigo` | Quando |
|---|---|
| `excluido` | Evento excluído |
| `id_invalido` | ID vazio ou que não é texto (o Google não é chamado) |
| `nao_encontrado` | O evento não existe, ou já está cancelado ou excluído |
| `sem_permissao` | O Google recusou a consulta ou a exclusão |
| `erro_google_calendar` | Outro erro HTTP da API |
| `erro_inesperado` | Falha fora da API (rede, por exemplo) |

### Saída em JSON

- Sucesso: `acao` = `evento_excluido` e `dados` = `{"evento_id", "titulo"}`.
- Erro: `status` = `erro`, `acao` = `evento_nao_excluido` e `erro` = `{"tipo": <codigo>, "mensagem"}`.

Etapas do `fluxo`: `validacao` / `google_calendar` / `conferencia`.

## Quem chama

`DELETE /calendar/events/{id}` (`backend/calendario.py`), usado pelo painel Agenda. Ver [`api.md`](api.md).

## Dependências do core

- `google_client`: `get_service` com o escopo de **escrita** (`calendar`), `obter_evento` e `excluir_evento`.
- `config`: `ESCOPO_CALENDARIO`.

## Como testar

```
python -m pytest tests/test_calendario_api.py
```

Os testes simulam o Google, então não precisam de `credentials.json`.

## Limitações

- Não guarda memória entre pedidos.
- Exclui de verdade: exige o escopo de escrita e a confirmação do usuário antes da chamada.
- Não interpreta linguagem natural: precisa do ID do evento.
