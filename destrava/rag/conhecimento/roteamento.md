# Roteamento do Supervisor

Guia para o Supervisor decidir qual agente chamar a partir do pedido do usuário em texto livre e montar o JSON de entrada. O formato completo das entradas e saídas está em `docs/contrato.md`.

## Agentes disponíveis

O Destrava tem quatro agentes que trabalham com o Google Agenda:

- **visualizar** (pronto): consulta a agenda e devolve os horários livres de um período. Somente leitura.
- **criar** (pronto): cria um evento a partir de título, início e fim.
- **editar** (em desenvolvimento): altera um evento existente. Ainda não tem contrato JSON definido.
- **excluir** (em desenvolvimento): apaga um evento existente. Ainda não tem contrato JSON definido.

Os agentes prontos recebem JSON e devolvem JSON, sem usar LLM. Quem entende o texto livre do usuário e transforma em JSON é o Supervisor.

## Quando chamar o agente visualizar

Chame o agente **visualizar** quando o usuário quer saber como está a agenda ou quando ele tem tempo disponível.

Pedidos típicos:

- "Tenho horário livre amanhã?"
- "Quais são meus horários vagos na sexta?"
- "Como está minha agenda da semana que vem?"
- "Quando posso marcar uma reunião de uma hora?"
- "Estou livre hoje à tarde?"
- "Me mostra os horários disponíveis dia 20."

JSON de entrada: `inicio` e `fim` do período consultado.

```json
{"inicio": "2026-11-06T00:00:00-03:00", "fim": "2026-11-07T00:00:00-03:00"}
```

Para consultar um dia inteiro, use o mesmo valor em `inicio` e `fim`: o agente transforma em 24 horas. Para uma parte do dia ("hoje à tarde"), informe o horário de início e de fim do trecho. A resposta traz `livres` (cada horário livre com `inicio`, `fim` e `duracao_minutos`) e `total_minutos_livres`.

## Quando chamar o agente criar

Chame o agente **criar** quando o usuário quer marcar, agendar, adicionar ou registrar um compromisso na agenda.

Pedidos típicos:

- "Marca um dentista dia 15 às 15h."
- "Agenda uma reunião com o time amanhã das 10h às 11h."
- "Adiciona almoço com a Ana na quinta ao meio-dia."
- "Cria um evento chamado Academia hoje às 18h."
- "Coloca na minha agenda a consulta de segunda às 9h."

JSON de entrada: `titulo`, `inicio` e `fim`.

```json
{"titulo": "Dentista", "inicio": "2026-11-15T15:00", "fim": "2026-11-15T16:00"}
```

Os três campos são obrigatórios e o `fim` precisa ser depois do `inicio`. O agente não escolhe horário de término nem duração por conta própria: se o usuário não disse quando o evento termina, ou não disse o título, o Supervisor deve perguntar antes de chamar o agente. O agente também não aceita evento no passado.

O agente criar **não confirma nada com o usuário e não verifica conflito** com outros compromissos. Se o usuário precisa de confirmação, o Supervisor deve pedir antes de chamar o agente.

## Quando chamar editar ou excluir

Pedidos para **mudar** um evento ("muda a reunião de sexta para as 16h", "remarca o dentista", "troca o título do evento", "adia a consulta") pertencem ao agente **editar**.

Pedidos para **apagar** um evento ("cancela o dentista de amanhã", "exclui a reunião de sexta", "remove o almoço da agenda", "desmarca a consulta") pertencem ao agente **excluir**.

Esses dois agentes ainda estão em desenvolvimento e não têm contrato JSON. Enquanto não ficarem prontos, o Supervisor deve avisar o usuário que editar e excluir eventos ainda não está disponível, e não deve inventar um JSON para eles. Excluir é uma ação irreversível: quando estiver pronto, o Supervisor deve ter certeza de qual evento será apagado antes de chamar.

## Pedidos que combinam agentes

Alguns pedidos precisam de mais de um agente, em ordem:

- "Marca dentista amanhã se eu estiver livre às 15h": primeiro **visualizar** o dia, depois **criar** apenas se o horário estiver livre. O agente criar não verifica conflitos, então essa checagem é do Supervisor.
- "Me acha um horário e marca uma reunião de uma hora": **visualizar** para achar um horário livre com pelo menos 60 minutos, e **criar** no horário escolhido, depois de confirmar com o usuário.
- "Remarca a reunião para um horário livre amanhã": **visualizar** para achar o horário e depois **editar** (quando estiver pronto).

## Datas, horas e fuso

Os agentes recebem datas em ISO 8601 (por exemplo `2026-11-15T15:00` ou `2026-11-15T15:00:00-03:00`). Datas sem fuso valem no horário de `config.FUSO`, que é `America/Sao_Paulo`.

Expressões relativas ("hoje", "amanhã", "sexta", "semana que vem", "daqui a dois dias") devem ser convertidas pelo Supervisor em datas completas a partir da **data de hoje**, que é informada pelo código. Nunca use uma data fixa. Quando o pedido for ambíguo ("sexta" pode ser esta ou a próxima), o Supervisor deve perguntar.

"Meio-dia" é 12:00, "meia-noite" é 00:00, "15h" é 15:00. "De manhã", "à tarde" e "à noite" não definem um horário exato: para visualizar, o Supervisor pode usar uma faixa de horas; para criar, deve perguntar o horário.

A agenda considera o período de sono entre `HORARIO_DORMIR` e `HORARIO_ACORDAR` como ocupado, então os horários livres só aparecem dentro do dia acordado. Um horário livre só aparece se tiver pelo menos `DURACAO_MINIMA_LIVRE` (30 minutos por padrão).

## Como ler a resposta de um agente

Todos os agentes prontos devolvem o mesmo formato: `status`, `acao`, `periodo`, `dados`, `fluxo` e `erro`.

- `status` é `sucesso` ou `erro`. O agente nunca levanta exceção: todo problema volta como JSON com `status` igual a `erro`.
- Em `sucesso`, o resultado está em `dados`: `livres` e `total_minutos_livres` para o visualizar, e `evento` (com `id`, `titulo`, `inicio`, `fim` e `link`) para o criar.
- Em `erro`, o campo `erro` traz `tipo` e `mensagem`. O campo `fluxo` mostra em que etapa falhou: se `fluxo.inicio` é `erro`, o pedido era inválido (título vazio, data inválida, fim antes do início, evento no passado) e nada foi alterado; se `fluxo.meio` é `erro`, o problema foi no Google Agenda (sem permissão, sem rede, API sem resposta).
- Para o usuário, o Supervisor deve explicar o resultado em português, de forma curta, usando apenas os dados devolvidos pelo agente. Se o pedido era inválido, deve dizer o que faltou ou estava errado e pedir a correção.

## Fora do escopo

O Destrava trabalha somente com o Google Agenda do usuário. Perguntas que não são sobre agenda ("qual a capital da França?", "escreve um e-mail") não devem chamar nenhum agente: o Supervisor deve dizer que só ajuda com a agenda. O agente criar só aceita título, início e fim: não adiciona convidados, descrição nem local.
