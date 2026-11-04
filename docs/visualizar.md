# Agente de Visualização

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Consultar a agenda do usuário no Google Agenda e informar, para o período pedido, os **horários livres**.
É um agente somente de leitura: não cria, edita nem exclui nada. **Não usa LLM**: recebe um JSON com o período e devolve um JSON.

## Contrato

Classe `AgenteVisualizar` em `destrava/agents/visualizar.py`.

| Método | Entrada | Saída | Uso |
|---|---|---|---|
| `executar_json(entrada)` | dict ou string JSON com `inicio` e `fim` | dicionário com a resposta padrão (abaixo) | Supervisor e `cli.py` |
| `executar(inicio, fim)` | período em `datetime` | dicionário com ocupados, livres, conflitos e totais | uso interno e `scripts/teste_visualizar.py` |

### Entrada

```json
{ "inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05T00:00:00-03:00" }
```

Validada por `PedidoVisualizacao` (`destrava/core/models.py`):

- `inicio` e `fim` em ISO 8601. Aceita só a data (`"2026-11-04"`), que vale meia-noite.
- `inicio` e `fim` devem ter fuso os dois, ou nenhum dos dois. Sem fuso, vale `config.FUSO`.
- `fim` igual a `inicio` vira **o dia inteiro** (`fim = inicio + 1 dia`).
- `fim` não pode ser anterior a `inicio`.

### Saída (sucesso)

```json
{
  "status": "sucesso",
  "acao": "agenda_visualizada",
  "periodo": {
    "inicio": "2026-11-04T00:00:00-03:00",
    "fim": "2026-11-05T00:00:00-03:00",
    "duracao_minutos": 1440.0
  },
  "dados": {
    "livres": [
      { "inicio": "2026-11-04T08:00:00-03:00", "fim": "2026-11-04T09:00:00-03:00", "duracao_minutos": 60.0 }
    ],
    "total_minutos_livres": 60.0
  },
  "fluxo": {
    "inicio": { "etapa": "validacao",       "status": "ok", "detalhe": { "inicio": "...", "fim": "..." } },
    "meio":   { "etapa": "google_calendar", "status": "ok", "detalhe": null },
    "fim":    { "etapa": "calculo",         "status": "ok", "detalhe": null }
  },
  "erro": null
}
```

### Saída (erro)

```json
{
  "status": "erro",
  "acao": "agenda_nao_visualizada",
  "periodo": null,
  "dados": null,
  "fluxo": {
    "inicio": { "etapa": "validacao",       "status": "erro",     "detalhe": null },
    "meio":   { "etapa": "google_calendar", "status": "pendente", "detalhe": null },
    "fim":    { "etapa": "calculo",         "status": "pendente", "detalhe": null }
  },
  "erro": { "tipo": "ValidationError", "mensagem": "..." }
}
```

| Campo | O que é |
|---|---|
| `status` | `sucesso` ou `erro` |
| `acao` | `agenda_visualizada` ou `agenda_nao_visualizada` |
| `periodo` | período consultado, no fuso do projeto, com `duracao_minutos`. Fica `null` se o pedido for inválido |
| `dados` | `livres` e `total_minutos_livres`. Fica `null` em erro |
| `fluxo` | as 3 etapas, cada uma com `status` `ok`, `erro` ou `pendente` |
| `erro` | `{"tipo", "mensagem"}` ou `null` |

O agente **não levanta exceção** em `executar_json`: pedido inválido e falha no Google viram JSON de erro.

## Fluxo

Todo o fluxo é feito pelo código, sem LLM.

| Etapa | Nome no JSON | O que faz |
|---|---|---|
| `inicio` | `validacao` | `PedidoVisualizacao` valida o JSON de entrada |
| `meio` | `google_calendar` | busca os eventos do período no Google Agenda (somente leitura) |
| `fim` | `calculo` | converte os eventos e calcula ocupados, livres e conflitos (`agenda_engine`) |

```
JSON {inicio, fim} → [validação] → [Google: eventos] → [cálculo] → JSON de resposta
```

Regras do fluxo:

- Erro na `validacao`: `meio` e `fim` ficam `pendente`.
- Erro no `google_calendar` (credencial, rede, API): `meio` vira `erro`, `fim` fica `pendente`, e `periodo` é preenchido porque o pedido era válido.
- O `executar` faz o `meio` e o `fim` numa única chamada. Por isso, se ele falhar, o erro é sempre registrado no `meio`, mesmo que tenha ocorrido no cálculo.

## Regras

**Cálculo** (`destrava/core/agenda_engine.py`):

- **Ocupado:** o intervalo de cada evento com horário, mais o período de sono (entre `HORARIO_DORMIR` e `HORARIO_ACORDAR`).
- **Dia inteiro:** sempre aparece na lista; só ocupa horário se `DIA_INTEIRO_BLOQUEIA = True` (padrão: `False`, como o Google).
- **Conflito:** dois eventos se sobrepõem quando `inicio_A < fim_B` e `inicio_B < fim_A`.
- **Livre:** lacuna sem eventos, fora do sono, com duração mínima `DURACAO_MINIMA_LIVRE`.

**O que o JSON devolve:** por enquanto só `livres` e `total_minutos_livres`. Ocupados, conflitos e `total_minutos_ocupados` são calculados pelo `executar`, mas não saem em `executar_json`.

Os valores (horários, duração mínima, fuso) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service([config.ESCOPO_SOMENTE_LEITURA])` (token em `token_readonly.json`) e `listar_eventos`.
- `agenda_engine`: `montar_visualizacao` e `normalizar_fuso`.
- `models`: `PedidoVisualizacao` (entrada) e `RespostaVisualizacao`, `Periodo`, `FluxoVisualizacao`, `Etapa`, `ErroInfo` (saída).
- `config`: `FUSO`, `HORARIO_ACORDAR`, `HORARIO_DORMIR`, `DURACAO_MINIMA_LIVRE`, `DIA_INTEIRO_BLOQUEIA`, `ESCOPO_SOMENTE_LEITURA`.

## Como testar

Precisa do `credentials.json` na raiz (ver README). Não precisa do Ollama. Na raiz do projeto:

```
python cli.py                                  # cola um JSON de período e vê a resposta
python -m scripts.teste_visualizar 2026-11-04  # um dia fixo, com ocupados, livres e conflitos
```

Exemplos de entrada para o `cli.py`:

| Caso | JSON |
|---|---|
| Um dia | `{"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05T00:00:00-03:00"}` |
| Só a data, dia inteiro | `{"inicio": "2026-11-04", "fim": "2026-11-04"}` |
| Uma semana | `{"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-11T00:00:00-03:00"}` |
| Parte do dia | `{"inicio": "2026-11-04T14:00:00-03:00", "fim": "2026-11-04T18:00:00-03:00"}` |
| Erro: data inválida | `{"inicio": "banana", "fim": "2026-11-05"}` |
| Erro: falta o `fim` | `{"inicio": "2026-11-04T00:00:00-03:00"}` |
| Erro: `fim` antes do `inicio` | `{"inicio": "2026-11-05", "fim": "2026-11-04"}` |
| Erro: fuso em um lado só | `{"inicio": "2026-11-04T00:00:00-03:00", "fim": "2026-11-05"}` |

O `scripts/teste_visualizar.py` chama `executar` direto, então mostra ocupados e conflitos, que o JSON do contrato não devolve.

Ainda não há testes automáticos para este agente.

## Limitações

- **Só livres:** `dados` não traz ocupados nem conflitos.
- **Erro do cálculo aparece no `meio`:** `meio` e `fim` rodam juntos, então não dá para separar onde falhou.
- **`mensagem` do erro de validação:** vem do Pydantic, em texto longo e com várias linhas.
- **Nomes das etapas em aberto:** `validacao`, `google_calendar` e `calculo` ainda precisam ser alinhados com o time.
