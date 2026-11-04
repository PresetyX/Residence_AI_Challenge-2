# Contrato JSON dos agentes

Todos os agentes (visualizar, criar, editar, excluir) devolvem **o mesmo formato de JSON**. Só o conteúdo de `dados` muda de um agente para outro. Assim o supervisor lê qualquer agente do mesmo jeito.

O código do contrato fica em `destrava/core/resposta.py`.

## Formato

```json
{
  "agente": "criar",
  "status": "sucesso",
  "acao": "evento_criado",
  "mensagem": "Pronto! Criei a Reunião em 15/11/2026, das 14:00 às 15:00.",
  "periodo": {
    "inicio": "2026-11-15T14:00:00-03:00",
    "fim": "2026-11-15T15:00:00-03:00",
    "duracao_minutos": 60.0
  },
  "dados": { "...": "específico de cada agente" },
  "fluxo": {
    "inicio": { "etapa": "extracao",        "status": "ok", "detalhe": { "...": "o que o LLM extraiu" } },
    "meio":   { "etapa": "google_calendar", "status": "ok", "detalhe": { "...": "o que a API fez" } },
    "fim":    { "etapa": "resposta",        "status": "ok", "detalhe": null }
  },
  "erro": null
}
```

| Campo | O que é |
|---|---|
| `agente` | `visualizar`, `criar`, `editar` ou `excluir` |
| `status` | `sucesso`, `erro` ou `cancelado` (usuário não confirmou) |
| `acao` | o que aconteceu, em snake_case (tabela abaixo) |
| `mensagem` | texto final para o usuário, montado pelo código a partir dos dados reais (sem LLM) |
| `periodo` | período tratado: `inicio`, `fim` (ISO 8601 com fuso) e `duracao_minutos` |
| `dados` | resultado do agente |
| `fluxo` | as 3 etapas que todo agente segue, cada uma com `status` `ok`, `erro`, `cancelado` ou `pendente` |
| `erro` | `{"tipo", "mensagem"}` ou `null` |

## As 3 etapas (iguais para todos)

| Etapa | Nome no JSON | Quem faz |
|---|---|---|
| `inicio` | `extracao` | LLM entende o pedido e devolve JSON (`PROMPT_EXTRACAO`) |
| `meio` | `google_calendar` | código fala com a API do Google |
| `fim` | `resposta` | código monta a mensagem e o JSON final (**sem LLM**) |

Regras do fluxo:

- Erro no `inicio` ou no `meio` → `status: "erro"` e as etapas seguintes ficam `pendente`.
- Erro no `fim` (ex.: falha ao montar o texto) → a ação **já foi feita**, então `status` continua `sucesso`, `fluxo.fim.status` vira `erro` e `mensagem` vira `"Ação concluída."`.
- O executor nunca levanta exceção: todo erro vira JSON.

## Ações de cada agente

| Agente | `acao` (sucesso) | `acao` (erro/cancelado) | `dados` |
|---|---|---|---|
| visualizar | `agenda_visualizada` | `agenda_nao_visualizada` | `ocupados`, `livres`, `conflitos`, `total_minutos_livres`, `total_minutos_ocupados` |
| criar | `evento_criado` | `evento_nao_criado` | `evento` (`id`, `titulo`, `inicio`, `fim`, `duracao_minutos`, `link`) e `periodo_confere` |
| editar | `evento_editado` | `evento_nao_editado` | *sugestão:* `evento` (antes/depois) e `periodo_confere` |
| excluir | `evento_excluido` | `evento_nao_excluido` | *sugestão:* `evento` excluído |

No agente de criar, `periodo` é lido **da resposta do Google** (não do pedido) e `periodo_confere` diz se ele bate com o início e o fim pedidos.

## Como um agente novo segue o contrato

O LLM é chamado **uma única vez**, no `inicio`, para entender o pedido. A resposta (`mensagem`) e o JSON são montados pelo código, o que deixa a saída mais rápida e sem risco de o modelo inventar texto.

Cada agente escreve três funções e chama `executar_fluxo`:

```python
from destrava.core.llm_client import extrair_json, perguntar
from destrava.core.resposta import Periodo, ResultadoExecucao, executar_fluxo


class AgenteExcluir:
    def executar_por_texto(self, pergunta, confirmar=None):

        def extrair(texto):                      # INÍCIO
            return extrair_json(perguntar(PROMPT_EXTRACAO.format(...)))

        def executar(extraido):                  # MEIO
            evento = ...                         # chama o Google
            return ResultadoExecucao(
                dados={"evento": evento},
                periodo=Periodo.de(inicio, fim),
                detalhe={"evento_id": evento["id"]},
            )

        return executar_fluxo(
            agente="excluir",
            acao_sucesso="evento_excluido",
            acao_erro="evento_nao_excluido",
            pergunta=pergunta,
            extrair=extrair,
            executar=executar,
            montar_mensagem=lambda r: ...,       # FIM (código, sem LLM): recebe o ResultadoExecucao
            confirmar=confirmar,                 # opcional: pede confirmação antes do meio
        )
```

Para ler o JSON que o modelo devolveu, use sempre `extrair_json()` (`core/llm_client.py`): ela tira blocos ```` ```json ```` e texto extra que o Gemma às vezes coloca.

Para obter a resposta: `resposta.para_dict()` (dicionário) ou `resposta.para_json()` (texto).

## Como testar

```
python -m pytest tests/
```

`tests/test_contrato_agentes.py` simula o Google e o LLM, então não precisa de `credentials.json` nem do Ollama.
