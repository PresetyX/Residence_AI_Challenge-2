# Supervisor

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

O Supervisor é a porta de entrada do chat. Ele recebe o pedido em texto livre, usa o LLM (Ollama) para entender o que o usuário quer e chama os agentes da agenda. Nada é criado sem a confirmação ("sim" ou "não") do usuário. Código: `destrava/agents/supervisor.py`; prompt: `destrava/prompts/supervisor.py`.

## O que ele faz hoje

| Pedido | Ação (`acao`) | O que acontece |
|---|---|---|
| Consultar horários ("o que tenho livre amanhã?") | `visualizar` | Chama o agente Visualizar e responde com os horários livres |
| Criar um evento | `criar` | Valida título, data e horário, confere que o horário está livre e fora do sono, e pede confirmação. Com o "sim", chama o agente Criar |
| Editar um evento | `editar` | Localiza pelo título e data originais; se houver um único resultado, mostra as alterações e pede confirmação antes de chamar Editar |
| Excluir um evento | `excluir` | Localiza pelo título e data originais; se houver um único resultado, pede confirmação antes de chamar Excluir |
| Agendar o plano de um projeto | `planejar` | Feito pelas rotas `POST /projetos/agendar` e `/confirmar` (abaixo), não pelo texto do chat |
| Pedido incompleto | `esclarecer` | Devolve uma pergunta ao usuário |
| Fora do escopo | `fora_escopo` | O chat responde com o "não entendi" do Planejador e a próxima mensagem vai para ele |

O Supervisor interpreta só a **última mensagem** (sem histórico) e guarda **uma** confirmação pendente por vez (`evento_pendente`, `operacao_pendente` ou `cronograma_pendente`). Edição e exclusão exigem título e data de início originais; se houver mais de um evento com o mesmo título na data, o usuário informa também o horário de início. Por isso o backend mantém uma instância por processo, com lock: uso local, uma pessoa por backend.

## Resposta

Dicionário com `status`, `acao`, `mensagem` e, quando há, `dados`. Valores de `status`:

| `status` | Significado |
|---|---|
| `sucesso`, `parcial` | Executado (`parcial`: parte dos eventos de um plano foi criada) |
| `confirmacao` | Aguardando "sim" ou "não" |
| `esclarecimento` | Faltou informação; `mensagem` traz a pergunta |
| `cancelado` | O usuário respondeu "não"; nada foi criado |
| `indisponivel` | O Supervisor ainda não faz essa ação |
| `erro` | Falha ou pedido inválido; nada foi criado |

## Prazo

O prazo é lido do texto do pedido por `destrava/core/prazo.py` (`interpretar_prazo`), sem LLM: `20/12`, `20/12/2026`, `2026-12-20`, `20 de dezembro`, `até amanhã`, `depois de amanhã`, `tenho uma semana`, `em 3 meses`, `daqui a 10 dias`, `semana que vem`, `fim do mês`, `até sexta`. Data inexistente (31/02) é erro; prazo que já passou é recusado pela API.

## Agendamento do plano

Fluxo de `preparar_agendamento` e `confirmar_agendamento`:

1. Consulta os horários livres até o prazo (agente Visualizar) e respeita o sono da conta (`config.HORARIO_DORMIR` e `HORARIO_ACORDAR`, ou o que a conta definiu no onboarding).
2. `core/encaixe_pomodoro.py` encaixa **todas** as tarefas nos horários livres, sem criar nada. Cada tarefa vale `story_points × MINUTOS_POR_STORY_POINT` de trabalho (60 min por padrão, ou o tempo calibrado da conta). Sempre sobram pelo menos **2 h livres por dia** (`config.MINIMO_LIVRE_DIA`).
3. Classificação do prazo:

| `classificacao` | Quando | Resultado |
|---|---|---|
| `tranquilo` | Cabe **com** Pomodoro (foco de 25 min, pausa de 5, pausa longa de 15 a cada 4 ciclos; `core/pomodoro.py`) | Prévia com os eventos e as sessões de foco |
| `corrido` | Só cabe **sem** Pomodoro | Prévia sem pausas |
| `impossivel` | Não cabe nem sem Pomodoro | Nenhum evento; a resposta traz `minutos_faltantes_minimos` |

4. A prévia fica em `cronograma_pendente`. Só o "sim" (`confirmar_agendamento(True)`) cria os eventos: antes de criar o primeiro, o Supervisor confere de novo se **todos** os horários continuam livres. "Não" descarta a prévia. Um segundo "sim" não repete a criação.

## Dependências

- `tools/visualizar.py`, `tools/criar.py`, `tools/editar.py`, `tools/excluir.py`, `agents/planejador.py` (`PedidoNaoEntendido`).
- `core/llm_client.py` (`perguntar`, `extrair_json`), `core/prazo.py`, `core/encaixe_pomodoro.py`, `core/pomodoro.py`, `core/config.py`.
- Quem chama: `backend/chat.py` ([`api.md`](api.md)).

## Como testar

```
python -m pytest tests/test_supervisor.py tests/test_supervisor_agendamento.py tests/test_supervisor_contato_planejamento.py tests/test_prazo.py tests/test_chat_stream.py tests/test_agendar_projeto_api.py
```

Os testes simulam o Google e o Ollama. Scripts manuais (precisam do Ollama): `python -m scripts.teste_supervisor_real`, `teste_supervisor_planejador`, `teste_supervisor_agendamento`, `teste_supervisor_periodos`, `teste_classificacao_prazo`.

## Limitações

- Não guarda histórico nem mais de uma confirmação pendente.
- Edição e exclusão localizam pelo título e data informados; correspondências incertas pedem esclarecimento, nunca executam automaticamente.
- O LLM pequeno pode errar a interpretação: por isso o Supervisor valida os dados (`PedidoCriacao`, data futura, horário de sono) e sempre pede confirmação antes de criar.
