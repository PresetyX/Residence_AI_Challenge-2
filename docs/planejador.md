# Planejador e story points

> Documentação técnica do **estado atual**. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

O Planejador transforma a descrição de um projeto em uma lista de etapas (tarefas). Depois, a rede neural estima os **story points** de cada etapa e o backend converte isso em tempo. Código: `destrava/agents/planejador.py`; prompt: `destrava/prompts/planejador.py`; contexto: RAG da base `planejador` ([`rag.md`](rag.md)).

## Fluxo de `POST /projetos`

| # | Passo | Quem |
|---|---|---|
| 1 | O Supervisor lê o prazo do texto (`core/prazo.py`); sem prazo, o plano sai assim mesmo e a resposta traz `precisa_prazo: true` | Código |
| 2 | O RAG busca trechos da base do Planejador para o prompt | Código |
| 3 | O LLM devolve o plano em JSON (esquema enviado ao Ollama como `format`) | LLM |
| 4 | O agente valida o plano (abaixo) | Código |
| 5 | O embedding BGE-M3 e a rede neural (`modelos/rede_neural.pt`) estimam os story points; o valor do LLM é descartado | Código |
| 6 | `tempo_estimado_minutos` = `story_points × MINUTOS_POR_STORY_POINT` | Código |

## Contrato

`AgentePlanejador().executar(projeto, prazo)` recebe a descrição e o prazo `AAAA-MM-DD` e devolve:

```json
{ "tarefas": [
  { "etapa": 1, "titulo": "...", "objetivo": "...", "entregaveis": "...",
    "demonstracao": "...", "dependencia": 0, "story_points": 3 }
] }
```

Regras validadas em código:

- Campos extras são rejeitados; textos não podem ficar vazios nem só com espaços.
- As etapas vão de 1 a N, sem saltos, repetições ou troca de ordem.
- `dependencia` é `0` (nenhuma) ou a etapa de uma tarefa **anterior**, o que impede ciclos.
- Se o modelo não entender o pedido, devolve `nao_entendi` e o agente levanta `PedidoNaoEntendido`; a API responde `{"tarefas": [], "nao_entendi": true, ...}` e o chat pede o projeto de novo.
- Resposta fora do contrato levanta `ErroPlanejador` (a API responde `502`).

## Story points e tempo

| Item | Valor |
|---|---|
| Estimativa | `backend/story_points.py`: local (torch, `requirements-ia.txt`) ou remota (`STORY_POINTS_URL`, serviço em `backend/servidor_story_points.py`) |
| Tempo por story point | 60 min (`MINUTOS_POR_STORY_POINT`, `core/pomodoro.py`); com a calibração da conta, o tempo da pessoa |
| Sem story points válidos | 60 min por tarefa |

Calibração e sono da conta: seção "Primeira conversa" do [README](../README.md) e `backend/perfil.py`. Treino do modelo: `python -m scripts.treinar_story_points joined_dataset.csv`.

## Como testar

```
python -m pytest tests/test_planejador.py tests/test_minutos_story_points.py tests/test_calibracao.py tests/test_servidor_ia.py
```

Os testes simulam o Ollama e o modelo de story points. Scripts manuais (precisam do Ollama): `python -m scripts.teste_planejador` e `teste_planejador_sem_rag`.

## Limitações

- Depende do Ollama (e do serviço de story points, no modo remoto): sem eles, a API responde `503`.
- O plano segue o contrato, mas a qualidade das etapas depende do modelo e da base de conhecimento.
