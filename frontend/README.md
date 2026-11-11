# Destrava · Frontend

Interface web do Destrava (AI Residence Challenge): landing page, login com Google e chat com os agentes de agenda.

Stack: Next.js (App Router), React, Tailwind CSS v4, Framer Motion, Lucide e Zustand.

## Como rodar

```
npm install
npm run dev
```

Abra http://localhost:3000. Por padrão tudo roda com **mocks** no navegador: não precisa do backend nem de credenciais do Google.

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
│   ├── chat/            cabeçalho, seletor de modelo, mensagens, cartão de evento
│   ├── sidebar/         painel Agenda: lista, criação/edição manual, detalhes, exclusão
│   └── ui/              botão, modal, logo
├── store/               Zustand: auth, chat (modelo + mensagens), calendar, ui (painel), toast
├── services/            contratos de API; cada serviço tem versão mock e versão HTTP
├── hooks/               foco e fechamento de popovers
└── lib/                 tipos, modelos, formatação de datas, texto dos termos
```

## Regras da IA (só planejamento)

O Destrava combate a procrastinação; agendar um compromisso avulso não é isso. Por isso:

- **Comandos diretos são recusados** ("crie um evento às 15h", "apague a tarefa X"). A IA responde com a mensagem padrão e oferece o painel manual.
- **A IA só mexe na agenda dentro de um plano:** cria blocos a partir de meta + horas livres, replaneja quando as horas mudam e desmarca os blocos se o usuário desistir.
- **O usuário sempre pode criar, editar e excluir manualmente** no painel Agenda.

As regras ficam em `src/lib/assistant-rules.ts` (`SYSTEM_PROMPT`, enviado em toda requisição de chat) e o mock que as simula em `src/services/mocks/mock-supervisor.ts`.

## Logo

`public/logo-mark.png` é o emblema como máscara branca com transparência; a cor e o brilho vêm do CSS (`.logo-mark` em `globals.css`). Para trocar a arte, substitua o PNG por outro branco com fundo transparente.

## Conectando o backend

Copie `.env.example` para `.env.local` e ajuste:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=false
```

Com `NEXT_PUBLIC_USE_MOCKS=false`, os serviços passam a chamar estes endpoints (definidos em `src/services/`):

| Serviço | Endpoint | Observação |
|---|---|---|
| Auth | `POST /auth/google/session`, `POST /auth/logout` | Recebe o registro de consentimento e os escopos OAuth |
| Chat | `POST /chat/stream` | Envia `modelo`, `sistema` e `mensagens`. Resposta em NDJSON: linhas `token`, `acao_agenda` e `sugerir_painel_manual` |
| Agenda | `GET/POST /calendar/events`, `GET/PUT/DELETE /calendar/events/:id` | Envelope `RespostaAgente` de `docs/contrato.md` |

Os tipos de `src/services/contracts.ts` espelham o contrato JSON dos agentes (`status`, `acao`, `dados`, `erro`...). Os campos `descricao` e `local` ainda não existem no backend e são opcionais.

Esses endpoints são uma **proposta**: o backend hoje expõe os agentes via `executar_json`, sem API HTTP. Ajuste os caminhos nos serviços conforme a API for definida; os componentes não precisam mudar.

## Antes de publicar

- O texto de `src/lib/legal.ts` é um modelo e deve ser revisado por alguém com conhecimento jurídico.
- Troque `CONTACT_EMAIL` em `src/lib/legal.ts` pelo e-mail real da equipe.
- A sessão mock fica no `localStorage`; em produção, use o cookie de sessão do backend.
