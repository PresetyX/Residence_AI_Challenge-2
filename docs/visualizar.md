# Agente de Visualização

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Consultar a agenda do usuário no Google Agenda e informar, para o período pedido, os **compromissos**, os **horários livres** e os **conflitos** entre eventos.
É um agente somente de leitura: não cria, edita nem exclui nada.

## Contrato

Classe `AgenteVisualizar` em `destrava/agents/visualizar.py`.

| Método | Entrada | Saída | Uso |
|---|---|---|---|
| `executar_por_texto(pergunta)` | texto livre (ex.: "quais meus horários livres amanhã?") | texto curto em português | Hoje: `cli.py` |
| `executar(inicio, fim)` | período em `datetime` | dicionário com os dados calculados | Futuro: Supervisor (sem LLM) |

Dicionário devolvido por `executar`:

| Chave | Conteúdo |
|---|---|
| `ocupados` | lista com `id`, `titulo`, `inicio`, `fim`, `tipo` (`evento`, `dia_inteiro` ou `sono`) |
| `livres` | lista com `inicio`, `fim`, `duracao_minutos` |
| `conflitos` | lista com `ids_eventos`, `inicio_sobreposicao`, `fim_sobreposicao` |
| `total_minutos_livres` / `total_minutos_ocupados` | totais do período |

As datas saem como texto ISO 8601, no fuso do projeto.

## Fluxo

O código conduz o fluxo e chama o LLM em dois momentos. O LLM interpreta e redige; o código busca, calcula e filtra.

| # | Passo | Quem |
|---|---|---|
| 1 | Recusa pedidos de ação (criar, editar, excluir) por palavras-chave | Código |
| 2 | Monta o `PROMPT_EXTRACAO` com a data de hoje, o fuso e a pergunta | Código |
| 3 | Devolve o período em JSON: `{"inicio": "...", "fim": "..."}` | LLM |
| 4 | Lê o JSON (`json.loads`); se falhar, usa os próximos 7 dias | Código |
| 5 | Busca os eventos do período no Google Agenda (somente leitura) | Código |
| 6 | Converte os eventos e calcula ocupados, livres e conflitos (`agenda_engine`) | Código |
| 7 | Escolhe as seções pedidas (livres, compromissos, conflitos) por palavras-chave | Código |
| 8 | Escreve a resposta usando só as seções escolhidas (`PROMPT_RESPOSTA`) | LLM |

```
pergunta → [código: recusa?] → [LLM: período] → [Google: eventos] → [código: cálculo + filtro] → [LLM: resposta]
```

Não há *tool calling*: o fluxo é fixo e conduzido pelo código. O LLM só recebe texto e devolve texto; nunca acessa a agenda.

## Regras

**Cálculo** (`destrava/core/agenda_engine.py`):

- **Ocupado:** o intervalo de cada evento com horário, mais o período de sono (entre `HORARIO_DORMIR` e `HORARIO_ACORDAR`).
- **Dia inteiro:** sempre aparece na lista; só ocupa horário se `DIA_INTEIRO_BLOQUEIA = True` (padrão: `False`, como o Google).
- **Conflito:** dois eventos se sobrepõem quando `inicio_A < fim_B` e `inicio_B < fim_A`.
- **Livre:** lacuna sem eventos, fora do sono, com duração mínima `DURACAO_MINIMA_LIVRE`.

**Seções devolvidas** (detecção por palavras-chave na pergunta):

| Seção | Palavras que ativam |
|---|---|
| Livres | livre, livres, disponível, disponivel, vago, vagos |
| Conflitos | conflit (conflito, conflitos, conflitante), sobrepõe, sobrepoe, colide, colidem |
| Compromissos | ocupado, ocupados, compromisso, compromissos, evento, eventos |
| Pedido de ação (recusa) | crie, criar, edite, editar, exclua, excluir, apague, apagar, delete, deletar, adicione, adicionar, modifique, modificar, remova, remover |

Se nenhuma seção for ativada, o agente mostra as três. A palavra "agenda" não ativa nada, porque aparece em quase toda pergunta.

Os valores (horários, duração mínima, fuso, modelo) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service([config.ESCOPO_SOMENTE_LEITURA])` (token em `token_readonly.json`) e `listar_eventos`.
- `llm_client`: `perguntar(prompt)` e `ErroLLM` (Ollama, modelo `gemma2:2b`).
- `agenda_engine`: `montar_visualizacao` e `normalizar_fuso`.
- `config`: `FUSO`, `HORARIO_ACORDAR`, `HORARIO_DORMIR`, `DURACAO_MINIMA_LIVRE`, `DIA_INTEIRO_BLOQUEIA`, `ESCOPO_SOMENTE_LEITURA`.
- `prompts/visualizar.py`: `PROMPT_EXTRACAO` e `PROMPT_RESPOSTA`.

## Como testar

Antes, é preciso ter o Ollama ativo, o modelo baixado e o `credentials.json` na raiz (ver README). Na raiz do projeto:

```
python cli.py                                  # chat: pergunta em texto livre
python -m scripts.teste_visualizar 2026-10-29  # um dia fixo, sem a etapa de interpretação
```

Exemplos de pedidos para cobrir cada tipo:

| Tipo | Pedido |
|---|---|
| Livres | "quais meus horários livres amanhã?" |
| Compromissos | "quais meus compromissos hoje?" |
| Conflitos | "tenho conflito de horário esta semana?" |
| Tudo | "como está minha agenda na sexta?" |
| Recusa | "crie uma reunião amanhã às 10h" |

Ainda não há testes automáticos para este agente.

## Limitações

- **Período padrão silencioso:** se o LLM devolver um JSON inválido (inclusive com marcação ```json), o agente usa os próximos 7 dias sem avisar.
- **Palavras-chave:** a recusa e a escolha de seções dependem de listas fixas; outras formas de perguntar podem não ser reconhecidas.
- **Fim do dia em 23:59:** o último minuto do dia fica fora da consulta.
- **Datas repetidas:** em consultas de um dia, os horários aparecem com a data ("29/10 09:00 às 29/10 10:00").
- **Modelo pequeno:** o Gemma 2 2B pode errar a interpretação ou a redação, e não tem *function calling* nativo.
- Não guarda memória entre perguntas.