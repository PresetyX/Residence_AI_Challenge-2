# Contrato JSON — Planejador → Supervisor (P3)


## Objetivo

O Planejador divide o projeto em tarefas, consulta a rede neural para estimar a duração de cada uma e envia ao Supervisor um JSON com as tarefas e seus tempos finais. O Supervisor **não precisa chamar  a rede neural**: ele recebe o planejamento para validar os dados e organizar o encaixe na agenda.

## Entrada do Supervisor

O contrato prevê o recebimento de um objeto JSON (`dict` ou string JSON, conforme a interface que o grupo decidir) com os seguintes campos:

| Campo | Tipo | Descrição |
|---|---|---|
| `projeto` | `string` | Nome ou descrição do projeto. |
| `prazo` | `string` | Data-limite do projeto, no formato `AAAA-MM-DD` (proposta). |
| `tarefas` | `array` | Lista de tarefas geradas pelo Planejador. |

Cada objeto em `tarefas` contém:

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | `string` | Identificador único da tarefa. |
| `titulo` | `string` | Nome da tarefa. |
| `categoria` | `string` | Categoria da atividade; valores permitidos ainda a definir. |
| `tamanho` | `int` | Tamanho da tarefa, provisoriamente de **1 a 3**. |
| `complexidade` | `int` | Complexidade da tarefa, provisoriamente de **1 a 10**. |
| `tempo_estimado` | `int` | Estimativa **final da rede neural**, em minutos. |


## Exemplo de entrada

```json
{
  "projeto": "Desenvolver uma API REST",
  "prazo": "2026-11-15",
  "tarefas": [
    {
      "id": "T001",
      "titulo": "Implementar as rotas",
      "categoria": "programacao",
      "tamanho": 2,
      "complexidade": 7,
      "tempo_estimado": 110
    },
    {
      "id": "T002",
      "titulo": "Testar os endpoints",
      "categoria": "testes",
      "tamanho": 1,
      "complexidade": 4,
      "tempo_estimado": 60
    }
  ]
}
```


## Validações propostas

- Todos os campos do exemplo são obrigatórios nesta versão.
- `projeto` e `titulo` não podem estar vazios.
- `prazo` deve ser uma data válida.
- `id` não pode se repetir entre as tarefas do mesmo planejamento.
- `tamanho` deve ser um inteiro entre **1 e 3** (escala provisória).
- `complexidade` deve ser um inteiro entre **1 e 10** (escala provisória).
- `tempo_estimado` deve ser um inteiro maior que zero, representando minutos.
- A lista de categorias permitidas ainda será definida com o grupo.

## Uso dos dados pelo Supervisor

1. Receber e validar o JSON do Planejador.
2. Solicitar à Visualização os horários livres até o prazo.
3. Aplicar as regras de planejamento definidas pelo grupo e enviar tarefas, horários livres e restrições ao algoritmo de encaixe em Python.
4. Preparar uma prévia para confirmação do estudante.
5. Somente após a confirmação, encaminhar os eventos ao Agendamento.


## Como testar

Os testes de validação do contrato estão em `tests/test_supervisor.py`. Para executá-los, abra o terminal **na raiz do repositório** e rode:

```bash
python -m pytest tests/test_supervisor.py -v
```



**Resultado esperado:** `2 passed`.