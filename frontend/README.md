# Destrava · Frontend

Interface web do Destrava (AI Residence Challenge): landing page, login com Google e chat com os agentes de agenda.

Stack: Next.js (App Router), React, Tailwind CSS v4, Framer Motion, Lucide e Zustand.

## Como rodar

O frontend sempre conversa com o backend (não há mais mocks no navegador). Na raiz do repositório:

```
uvicorn backend.main:app
```

Depois, nesta pasta:

```
npm install
npm run dev
```

Abra http://localhost:3000 (ou a porta que o Next.js mostrar). O endereço do backend vem de `NEXT_PUBLIC_API_URL` (veja `.env.example`; o padrão é `http://localhost:8000`).

| Comando | O que faz |
|---|---|
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` | Build de produção |
| `npm run typecheck` | Checagem de tipos |

## Estrutura

```
src/
├── app/                 rotas: / (landing) e /chat
├── components/
│   ├── landing/         hero, showcase interativo, modal de consentimento
│   ├── chat/            cabeçalho, seletor de modelo, mensagens, cartões de evento e de plano
│   ├── sidebar/         painel Agenda: lista, criação/edição manual, detalhes, exclusão
│   └── ui/              botão, modal, logo
├── store/               Zustand: auth, chat (modelo + mensagens), calendar, ui (painel), toast
├── services/            chamadas HTTP ao backend e o fluxo do planejador no chat
├── hooks/               foco e fechamento de popovers
└── lib/                 tipos, modelos, formatação de datas, texto dos termos
```

## Endpoints usados

| Serviço | Endpoint | Observação |
|---|---|---|
| Login | `POST /auth/google/session`, `POST /auth/logout` | OAuth do Google feito pelo backend |
| Agenda | `GET/POST /calendar/events`, `GET/PUT/DELETE /calendar/events/:id` | Envelope `RespostaAgente` de `docs/contrato.md` |
| Chat | `POST /chat/stream` | Supervisor. NDJSON: `status`, `token`, `acao_agenda`, `sugerir_painel_manual`, `pedir_projeto` |
| Planejador | `POST /projetos`, `POST /prazos/interpretar` | Etapas + story points. O prazo é lido do próprio texto pelo Supervisor |
| Agendamento do plano | `POST /projetos/agendar`, `POST /projetos/agendar/confirmar` | Classificação do prazo (tranquilo, corrido, impossível), prévia e criação |

## Planejador no chat

Escreva o projeto e, se quiser, o prazo na mesma mensagem: *“Quero criar um app de controle de gastos em React até amanhã”*. O Supervisor lê o prazo do texto: `20/12`, `20/12/2026`, `2026-12-20`, `20 de dezembro`, `até amanhã`, `depois de amanhã`, `tenho uma semana`, `em 3 meses`, `daqui a 10 dias`, `semana que vem`, `fim do mês`, `até sexta`...

- Sem prazo, o plano é feito assim mesmo e o Destrava pergunta só a data.
- Texto que não é projeto (*“banana com azeite”*) volta com o “não entendi” do Planejador; a próxima mensagem vai para ele.
- Depois do plano, o Destrava oferece encaixar as etapas na agenda: mostra a classificação do prazo e a prévia, e só cria os eventos depois do “sim”.

O roteamento fica em `src/services/project-planner.ts` e as chamadas em `src/services/project-service.ts`. Consultas de horários e eventos avulsos vão para o Supervisor (`POST /chat/stream`).

## Regras da IA (só planejamento)

As regras ficam em `src/lib/assistant-rules.ts` (`SYSTEM_PROMPT`, enviado em toda requisição de chat).

## Logo

`public/logo-mark.png` é o emblema como máscara branca com transparência; a cor e o brilho vêm do CSS (`.logo-mark` em `globals.css`). Para trocar a arte, substitua o PNG por outro branco com fundo transparente.

## Antes de publicar

- O texto de `src/lib/legal.ts` é um modelo e deve ser revisado por alguém com conhecimento jurídico.
- Troque `CONTACT_EMAIL` em `src/lib/legal.ts` pelo e-mail real da equipe.
- A sessão do usuário fica no `localStorage`; em produção, use um cookie de sessão do backend.
