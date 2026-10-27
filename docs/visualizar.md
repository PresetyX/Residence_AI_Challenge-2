# Agente Visualizar

> Documentação técnica do **estado atual** do agente. A história (decisões, problemas, testes) fica no Google Docs.

## Objetivo

Mostra, para um período pedido pelo usuário, os eventos da agenda, os horários **ocupados**, os horários **livres** e os **conflitos**.
É um agente somente de leitura: não cria, edita nem exclui nada.

## Contrato

O que entra e o que sai, para o supervisor saber como chamá-lo.

| | |
|---|---|
| **Entrada** | texto: a pergunta do usuário (ex.: "estou livre sexta à tarde?") |
| **Saída** | texto em português, curto, só com dados da agenda |
| **Função de entrada** | `visualizar_agenda(pergunta: str) -> str` *(nome sugerido; confirmar com o grupo)* |

## Fluxo

Quem faz cada passo: o LLM só interpreta e redige, o código busca e calcula.

| # | Passo | Quem |
|---|---|---|
| 1 | Extrai o período e o que o usuário quer ver (livres, ocupados, conflitos) em JSON (`PROMPT_EXTRACAO`) | LLM |
| 2 | Busca os eventos do período no Google Agenda | Código |
| 3 | Calcula ocupados, livres e conflitos | Código |
| 4 | Escolhe o que devolver, conforme o pedido | Código |
| 5 | Escreve a resposta final usando só os dados calculados (`PROMPT_RESPOSTA`) | LLM |

```
pergunta → [LLM] → período + intenção → [API] → eventos → [código] → livres/ocupados/conflitos → [LLM] → resposta
```

## Regras

- **Ocupado:** o intervalo de cada evento.
- **Conflito:** dois eventos se sobrepõem quando `inicio_A < fim_B` e `inicio_B < fim_A`.
- **Livre:** lacuna entre eventos com duração mínima `DURACAO_MINIMA_LIVRE`, dentro do período entre `HORARIO_ACORDAR` e `HORARIO_DORMIR`.
- **O que devolver:** só livres, só ocupados ou os dois, conforme o que o usuário pediu. Se não especificar, devolve os dois.

Os valores (horários, duração mínima, fuso) estão em `destrava/core/config.py`.

## Dependências do core

- `google_client`: `get_service` com o escopo de **leitura** (`calendar.readonly`) e `listar_eventos`.
- `llm_client`: `perguntar(prompt)`.
- `config`: `FUSO`, `HORARIO_ACORDAR`, `HORARIO_DORMIR`, `DURACAO_MINIMA_LIVRE`.
- `prompts/visualizar.py`: `PROMPT_EXTRACAO` e `PROMPT_RESPOSTA`.

## Como testar

*A preencher quando o agente estiver rodando.* Antes de testar, é preciso ter o Ollama ativo, o modelo baixado e o `credentials.json` na raiz (ver README).

Exemplos de pedidos para cobrir cada tipo:

| Tipo | Pedido |
|---|---|
| Ver o dia | "o que tenho amanhã?" |
| Horário livre | "estou livre sexta à tarde?" |
| Conflito | "tenho algum conflito essa semana?" |

## Limitações

- Não guarda memória entre perguntas.
- Lê uma única agenda (a principal).
- Depende do Ollama estar rodando; modelos pequenos (2B) podem errar o formato do JSON.
- Não altera a agenda.
