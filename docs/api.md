# API do backend

> Documentação técnica do **estado atual**. Código em `backend/`. Para subir: `uvicorn backend.main:app` (veja o [README](../README.md)).

O frontend só fala com esta API. Erros de validação voltam como `422`; as rotas de agenda devolvem o envelope `RespostaAgente` ([`contrato.md`](contrato.md)).

## Login e agenda (`backend/calendario.py`)

| Rota | O que faz |
|---|---|
| `POST /auth/google/session` | Login: OAuth do Google (abre o navegador na primeira vez e salva `token_calendar.json`), registra o consentimento e ativa o perfil da conta |
| `POST /auth/logout` | Encerra a sessão no frontend (`204`); o token continua salvo |
| `GET /calendar/events` | Lista os eventos (padrão: de ontem até +60 dias; aceita `inicio` e `fim`) |
| `GET /calendar/events/{id}` | Um evento |
| `POST /calendar/events` | Cria (agente [Criar](criar.md)) |
| `PUT /calendar/events/{id}` | Edita (agente [Editar](editar.md)) |
| `DELETE /calendar/events/{id}` | Exclui (agente [Excluir](excluir.md)) |

## Chat e agendamento do plano (`backend/chat.py`)

| Rota | O que faz |
|---|---|
| `POST /chat/stream` | Chat com o [Supervisor](supervisor.md). Entrada: `{"modelo", "sistema", "mensagens": [{"papel", "conteudo"}]}`. Saída: NDJSON |
| `POST /chat/reiniciar` | Zera as confirmações pendentes (nova conversa) |
| `POST /projetos/agendar` | `{projeto, prazo, tarefas, meta?}`: classifica o prazo e devolve a prévia, sem criar nada |
| `POST /projetos/agendar/confirmar` | `{confirmado}`: cria os eventos da prévia (ou cancela) |

Linhas do NDJSON de `/chat/stream`:

| `tipo` | Significado |
|---|---|
| `status` | Progresso antes da resposta |
| `token` | Pedaço do texto da resposta |
| `acao_agenda` | Evento criado (`acao: "created"` e o `evento`) |
| `sugerir_painel_manual` | A IA não fez o pedido (ex.: editar ou excluir); oferecer o painel Agenda |
| `pedir_projeto` | Fora do escopo: a próxima mensagem vai para o Planejador |
| `fim_conversa` | Pedido concluído: a próxima mensagem abre outra conversa |

## Planejador e prazos (`backend/main.py`)

| Rota | O que faz |
|---|---|
| `POST /projetos` | `{texto, prazo?}`: Planejador + story points ([`planejador.md`](planejador.md)). Erros: `422` (entrada ou prazo inválido, ou prazo que já passou), `502` (resposta da IA fora do contrato), `503` (Ollama ou serviço de story points fora do ar) |
| `POST /prazos/interpretar` | Lê um prazo escrito em texto ("até amanhã", "20/12") |
| `GET /tarefas` | Compromissos da agenda em uma janela (`inicio`, `fim`) |
| `POST /historico` | Registra o tempo real de uma tarefa concluída (`story_points`, `tempo_real_minutos`) na média histórica (`data/historico.json`) |
| `GET /calibracao`, `POST /calibracao` | As 10 tarefas da calibração e o envio dos tempos (ver README) |

## Perfil (`backend/perfil.py`)

| Rota | O que faz |
|---|---|
| `GET /perfil` | Perfil da conta (`?email=`): sono, calibração e se o onboarding está pendente |
| `PUT /perfil/sono` | Salva a hora de dormir e de acordar (texto livre aceito) |
| `POST /perfil/interpretar` | Lê uma resposta do onboarding (horário ou duração) |

O perfil fica em `data/perfis.json` por e-mail, até o banco de dados dos story points ficar pronto.

## Serviço de story points (`backend/servidor_story_points.py`)

Roda no servidor de IA, separado do backend (ver "Servidor de IA compartilhado" no README): `GET /saude` e `POST /story-points`. Com `CHAVE_API_IA` definida, exige o cabeçalho `X-API-Key`.

## Como testar

```
python -m pytest tests/test_calendario_api.py tests/test_chat_stream.py tests/test_agendar_projeto_api.py tests/test_projetos_prazo.py tests/test_perfil.py tests/test_calibracao.py tests/test_servidor_ia.py
```
