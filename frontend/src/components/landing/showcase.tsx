"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpenText,
  CalendarDays,
  CalendarX2,
  ChevronDown,
  CircleCheck,
  CircleDashed,
  CircleX,
  Cpu,
  Eye,
  Hand,
  type LucideIcon,
  MessageSquareText,
  Network,
  RefreshCw,
  Target,
  Workflow,
} from "lucide-react";
import { type ReactNode, useState } from "react";

// ---------------------------------------------------------------------------
// Shared section chrome
// ---------------------------------------------------------------------------

function Section({
  id,
  eyebrow,
  title,
  lead,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lead: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="relative px-5 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="max-w-2xl"
        >
          <p className="text-xs font-semibold tracking-[0.2em] text-violet-400 uppercase">
            {eyebrow}
          </p>
          <h2
            id={`${id}-title`}
            className="mt-3 font-display text-3xl font-semibold tracking-tight text-balance sm:text-4xl"
          >
            {title}
          </h2>
          <p className="mt-4 leading-relaxed text-pretty text-muted">{lead}</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="mt-12"
        >
          {children}
        </motion.div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// 1. Capabilities: cards that expand to show details and an example prompt
// ---------------------------------------------------------------------------

interface Capability {
  icon: LucideIcon;
  title: string;
  summary: string;
  details: string;
  example: string;
}

const CAPABILITIES: Capability[] = [
  {
    icon: Target,
    title: "Metas viram blocos de foco",
    summary: "Diga a meta e o tempo que você tem. O plano sai pronto.",
    details:
      "O Destrava divide o projeto em etapas, calcula quantos blocos cabem nas suas horas livres e agenda todos de uma vez no Google Agenda, sem conflito com o que já existe.",
    example: "Monte um plano para eu fazer meu TCC, tenho 10 horas livres esta semana",
  },
  {
    icon: RefreshCw,
    title: "Replanejamento adaptativo",
    summary: "A semana mudou? O plano muda junto.",
    details:
      "Ganhou ou perdeu tempo, é só avisar. O Destrava mantém os blocos que ainda fazem sentido, ajusta os demais e encaixa ou remove o que for preciso.",
    example: "Consegui mais 2 horas, agora tenho 12 horas livres esta semana",
  },
  {
    icon: CalendarX2,
    title: "Desmarcar sem culpa",
    summary: "Sem tempo nesta semana? Libere a agenda em um pedido.",
    details:
      "O Destrava remove apenas os blocos do plano que ele mesmo criou. Seus compromissos manuais nunca são tocados, e o plano pode ser remontado quando você voltar.",
    example: "Não tenho mais tempo para fazer o TCC esta semana, desmarque tudo",
  },
  {
    icon: Hand,
    title: "Controle manual sempre",
    summary: "Compromissos simples são seus: crie, edite e exclua no painel.",
    details:
      "A IA não executa comandos diretos como “crie um evento às 15h”. Isso não combate a procrastinação. Para compromissos avulsos existe o painel Agenda, com formulário, edição e exclusão com confirmação.",
    example: "Crie um evento para 15h → use o painel manual",
  },
  {
    icon: Eye,
    title: "Horários livres",
    summary: "Descubra quanto tempo você realmente tem.",
    details:
      "O agente de visualização lê seus eventos, considera seus horários de sono e devolve os intervalos livres e os conflitos. É somente leitura: nada é alterado.",
    example: "Quais horários livres eu tenho amanhã?",
  },
  {
    icon: Cpu,
    title: "Escolher o modelo",
    summary: "Gemma no seu dispositivo ou na nuvem, você decide.",
    details:
      "Use o Gemma 2B local para manter tudo no dispositivo, ou os modelos Gemma 4 em nuvem quando precisar de mais desempenho ou precisão. A troca é feita a qualquer momento no chat.",
    example: "Trocar para Gemma 4 26B A4B",
  },
];

function CapabilityCard({ capability, index }: { capability: Capability; index: number }) {
  const [open, setOpen] = useState(false);
  const Icon = capability.icon;
  const panelId = `capability-panel-${index}`;

  return (
    <motion.li
      layout
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 26 }}
      className={`group relative rounded-3xl border bg-ink-900/70 transition-colors ${
        open
          ? "border-violet-400/60 shadow-[0_0_50px_-12px_rgb(124_58_237/0.7)]"
          : "border-purple-500/20 hover:border-purple-400/45"
      }`}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-3xl bg-[radial-gradient(circle_at_30%_0%,rgb(124_58_237/0.2),transparent_60%)] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      />
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
        className="relative flex w-full items-start gap-4 rounded-3xl p-6 text-left"
      >
        <span className="grid size-11 shrink-0 place-items-center rounded-xl border border-purple-500/30 bg-violet-600/20 text-violet-300 transition group-hover:shadow-[0_0_24px_rgb(124_58_237/0.55)]">
          <Icon className="size-5" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-display font-semibold">{capability.title}</span>
          <span className="mt-1 block text-sm leading-relaxed text-muted">
            {capability.summary}
          </span>
        </span>
        <ChevronDown
          aria-hidden="true"
          className={`mt-1 size-4.5 shrink-0 text-muted transition-transform duration-300 ${open ? "rotate-180 text-violet-300" : ""}`}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={panelId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="relative overflow-hidden"
          >
            <div className="px-6 pb-6">
              <p className="text-sm leading-relaxed text-slate-300">{capability.details}</p>
              <p className="mt-4 flex items-start gap-2 rounded-xl border border-purple-500/20 bg-ink-950/70 px-3.5 py-2.5 text-sm text-violet-200">
                <MessageSquareText className="mt-0.5 size-4 shrink-0 text-violet-400" aria-hidden="true" />
                <span>
                  <span className="sr-only">Exemplo de pedido: </span>“{capability.example}”
                </span>
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}

// ---------------------------------------------------------------------------
// 2. Architecture: pick a layer of the pipeline to read what it does
// ---------------------------------------------------------------------------

interface Layer {
  id: string;
  icon: LucideIcon;
  name: string;
  role: string;
  description: string;
  tags: string[];
}

const LAYERS: Layer[] = [
  {
    id: "chat",
    icon: MessageSquareText,
    name: "Chat",
    role: "Onde você pede",
    description:
      "Você descreve a meta e o tempo disponível em texto livre. A interface mostra a resposta em tempo real e transforma cada plano em um cartão com os blocos agendados.",
    tags: ["Linguagem natural", "Respostas em tempo real", "Cartões de plano"],
  },
  {
    id: "supervisor",
    icon: Network,
    name: "Supervisor",
    role: "Quem interpreta",
    description:
      "O Supervisor usa o modelo Gemma escolhido para separar planejamento de comando direto. Pedidos de planejamento viram chamadas aos agentes; comandos diretos são recusados e encaminhados ao painel manual.",
    tags: ["Gemma 2B local", "Gemma 4 na nuvem", "Só planejamento"],
  },
  {
    id: "agents",
    icon: Workflow,
    name: "Agentes",
    role: "Quem executa",
    description:
      "Cada agente faz uma única coisa: visualizar, criar, editar, excluir ou planejar. Os agentes de agenda recebem JSON e devolvem JSON sem usar LLM, o que torna cada ação previsível e fácil de testar.",
    tags: ["Visualizar", "Criar", "Editar", "Excluir", "Planejador"],
  },
  {
    id: "rag",
    icon: BookOpenText,
    name: "RAG",
    role: "De onde vem o contexto",
    description:
      "A base de conhecimento é dividida em trechos, indexada em um banco vetorial Chroma e consultada por busca híbrida: palavras-chave mais significado. O Planejador usa esses trechos para montar planos melhores.",
    tags: ["LangChain", "Chroma", "Embeddings", "Busca híbrida"],
  },
  {
    id: "calendar",
    icon: CalendarDays,
    name: "Google Agenda",
    role: "Onde tudo acontece",
    description:
      "A integração usa a API oficial do Google Calendar com OAuth 2.0. As permissões de leitura e de escrita são pedidas de forma explícita e podem ser revogadas quando você quiser.",
    tags: ["API do Google Calendar", "OAuth 2.0", "Leitura e escrita"],
  },
];

function Architecture() {
  const [activeId, setActiveId] = useState(LAYERS[1].id);
  const active = LAYERS.find((layer) => layer.id === activeId) ?? LAYERS[0];
  const ActiveIcon = active.icon;

  function onKeyDown(event: React.KeyboardEvent, index: number) {
    const delta = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key];
    if (!delta) return;
    event.preventDefault();
    const next = LAYERS[(index + delta + LAYERS.length) % LAYERS.length];
    setActiveId(next.id);
    document.getElementById(`layer-tab-${next.id}`)?.focus();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div
        role="tablist"
        aria-label="Camadas da arquitetura"
        aria-orientation="vertical"
        className="relative flex flex-col gap-2"
      >
        <span
          aria-hidden="true"
          className="absolute top-8 bottom-8 left-[2.15rem] w-px bg-gradient-to-b from-transparent via-purple-500/40 to-transparent"
        />
        {LAYERS.map((layer, index) => {
          const selected = layer.id === activeId;
          const Icon = layer.icon;
          return (
            <button
              key={layer.id}
              id={`layer-tab-${layer.id}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls="layer-panel"
              tabIndex={selected ? 0 : -1}
              onClick={() => setActiveId(layer.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={`relative flex items-center gap-4 rounded-2xl border p-3.5 text-left transition ${
                selected
                  ? "border-violet-400/60 bg-violet-600/15"
                  : "border-transparent hover:border-purple-500/25 hover:bg-white/[0.03]"
              }`}
            >
              <span
                className={`relative grid size-10 shrink-0 place-items-center rounded-xl border transition ${
                  selected
                    ? "border-violet-300/60 bg-violet-600 text-white shadow-[0_0_24px_rgb(124_58_237/0.8)]"
                    : "border-purple-500/30 bg-ink-900 text-violet-300"
                }`}
              >
                <Icon className="size-4.5" aria-hidden="true" />
              </span>
              <span>
                <span className="block text-xs text-muted">{layer.role}</span>
                <span className="block font-display font-semibold">{layer.name}</span>
              </span>
            </button>
          );
        })}
      </div>

      <div
        id="layer-panel"
        role="tabpanel"
        aria-labelledby={`layer-tab-${active.id}`}
        tabIndex={0}
        className="glass relative min-h-72 overflow-hidden rounded-3xl p-7 sm:p-9"
      >
        <div
          aria-hidden="true"
          className="absolute -top-24 -right-24 size-64 rounded-full bg-violet-600/25 blur-3xl"
        />
        <AnimatePresence mode="wait">
          <motion.div
            key={active.id}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={{ duration: 0.25 }}
            className="relative"
          >
            <span className="grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-violet-800 shadow-[0_0_30px_rgb(124_58_237/0.6)]">
              <ActiveIcon className="size-6" aria-hidden="true" />
            </span>
            <p className="mt-6 text-xs font-semibold tracking-[0.18em] text-violet-400 uppercase">
              {active.role}
            </p>
            <h3 className="mt-1 font-display text-2xl font-semibold">{active.name}</h3>
            <p className="mt-4 leading-relaxed text-slate-300">{active.description}</p>
            <ul className="mt-6 flex flex-wrap gap-2">
              {active.tags.map((tag) => (
                <li
                  key={tag}
                  className="rounded-full border border-purple-500/30 bg-violet-600/10 px-3 py-1 text-xs text-violet-200"
                >
                  {tag}
                </li>
              ))}
            </ul>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. Automation: the three-step flow every calendar agent reports back
// ---------------------------------------------------------------------------

type StepStatus = "ok" | "erro" | "pendente";
type Scenario = "plan" | "direct" | "invalid";

const FLOW_STEPS = [
  {
    key: "validacao",
    title: "Validação",
    text: "Confere título, datas e horários de cada bloco. Recusa eventos no passado ou com fim antes do início.",
  },
  {
    key: "google_calendar",
    title: "Google Agenda",
    text: "Só então chama a API do Google Calendar para ler ou gravar o evento.",
  },
  {
    key: "conferencia",
    title: "Conferência",
    text: "Confirma o que foi gravado e devolve id, horários e link do evento.",
  },
] as const;

const SCENARIOS: Record<
  Scenario,
  {
    label: string;
    request: string;
    statuses: StepStatus[];
    responseTitle: string;
    responseNote: string;
    response: string;
    /** Prose replies wrap; JSON keeps its formatting. */
    isProse?: boolean;
  }
> = {
  plan: {
    label: "Planejamento",
    request: "Monte um plano para meu TCC, tenho 10 horas livres esta semana",
    statuses: ["ok", "ok", "ok"],
    responseTitle: "Resposta do agente (por bloco)",
    responseNote:
      "O Supervisor calcula os blocos e chama o agente de criação uma vez para cada um. Todo agente devolve o mesmo formato.",
    response: `{
  "status": "sucesso",
  "acao": "evento_criado",
  "dados": {
    "evento": {
      "titulo": "TCC: Escopo e roteiro",
      "inicio": "2026-11-16T19:00:00-03:00",
      "fim": "2026-11-16T21:00:00-03:00"
    }
  },
  "erro": null
}`,
  },
  direct: {
    label: "Comando direto",
    request: "Crie um evento para 15h com o nome Reunião",
    statuses: ["pendente", "pendente", "pendente"],
    responseTitle: "Resposta do assistente",
    responseNote:
      "Comandos operacionais simples não chegam aos agentes. O assistente explica a proposta do Destrava e aponta para o painel manual.",
    response:
      "O Destrava foi feito para te ajudar a combater a procrastinação e organizar planos complexos! Para compromissos simples, use o painel manual. Me diga qual meta ou projeto você quer destravar hoje!",
    isProse: true,
  },
  invalid: {
    label: "Bloco inválido",
    request: "Um bloco do plano cairia em um horário que já passou",
    statuses: ["erro", "pendente", "pendente"],
    responseTitle: "Resposta do agente",
    responseNote:
      "Erros nunca viram exceção: voltam como JSON, a agenda permanece intacta e o Supervisor escolhe outro horário.",
    response: `{
  "status": "erro",
  "acao": "evento_nao_criado",
  "dados": null,
  "erro": {
    "tipo": "ValidationError",
    "mensagem": "Não é permitido criar eventos no passado."
  }
}`,
  },
};

const STATUS_STYLE: Record<StepStatus, { icon: LucideIcon; label: string; className: string }> = {
  ok: { icon: CircleCheck, label: "Concluída", className: "text-emerald-300 border-emerald-400/40 bg-emerald-500/10" },
  erro: { icon: CircleX, label: "Erro", className: "text-red-300 border-red-400/40 bg-red-500/10" },
  pendente: { icon: CircleDashed, label: "Não executada", className: "text-slate-400 border-slate-500/30 bg-white/[0.03]" },
};

function Automation() {
  const [scenario, setScenario] = useState<Scenario>("plan");
  const current = SCENARIOS[scenario];

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="glass rounded-3xl p-6 sm:p-8">
        <div
          role="group"
          aria-label="Cenário de exemplo"
          className="inline-flex max-w-full flex-wrap rounded-xl border border-purple-500/20 bg-ink-950/70 p-1"
        >
          {(Object.keys(SCENARIOS) as Scenario[]).map((key) => (
            <button
              key={key}
              type="button"
              aria-pressed={scenario === key}
              onClick={() => setScenario(key)}
              className={`relative rounded-lg px-3 py-2 text-sm font-medium transition sm:px-4 ${
                scenario === key ? "text-white" : "text-muted hover:text-white"
              }`}
            >
              {scenario === key && (
                <motion.span
                  layoutId="scenario-pill"
                  className="absolute inset-0 rounded-lg bg-violet-600 shadow-[0_0_20px_rgb(124_58_237/0.6)]"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <span className="relative">{SCENARIOS[key].label}</span>
            </button>
          ))}
        </div>

        <p className="mt-6 text-sm text-muted">
          Pedido: <span className="text-white">“{current.request}”</span>
        </p>

        <ol className="mt-6 space-y-3">
          {FLOW_STEPS.map((step, index) => {
            const status = STATUS_STYLE[current.statuses[index]];
            const StatusIcon = status.icon;
            return (
              <motion.li
                key={`${scenario}-${step.key}`}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.14, duration: 0.35 }}
                className={`flex gap-4 rounded-2xl border p-4 ${status.className}`}
              >
                <StatusIcon className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <div>
                  <p className="font-medium text-white">
                    {index + 1}. {step.title}
                    <span className="ml-2 text-xs font-normal opacity-90">· {status.label}</span>
                  </p>
                  <p className="mt-1 text-sm text-slate-300">{step.text}</p>
                </div>
              </motion.li>
            );
          })}
        </ol>
      </div>

      <div className="glass flex flex-col rounded-3xl p-6 sm:p-8">
        <p className="text-sm font-medium text-white">{current.responseTitle}</p>
        <p className="mt-1 text-sm text-muted">{current.responseNote}</p>
        <AnimatePresence mode="wait">
          <motion.pre
            key={scenario}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            tabIndex={0}
            aria-label="Exemplo de resposta"
            className={`mt-5 flex-1 overflow-x-auto rounded-2xl border border-purple-500/20 bg-ink-950/80 p-4 leading-relaxed text-violet-100 ${
              current.isProse
                ? "font-sans text-sm whitespace-pre-wrap"
                : "font-mono text-[0.8rem]"
            }`}
          >
            <code>{current.response}</code>
          </motion.pre>
        </AnimatePresence>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

export function Showcase() {
  return (
    <>
      <Section
        id="capacidades"
        eyebrow="Capacidades"
        title="Feito para quem vive adiando o que importa"
        lead="Agendar uma reunião é fácil. Difícil é começar o TCC. O Destrava cuida da parte difícil; toque em um cartão para ver como."
      >
        <ul className="grid items-start gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((capability, index) => (
            <CapabilityCard key={capability.title} capability={capability} index={index} />
          ))}
        </ul>
      </Section>

      <Section
        id="arquitetura"
        eyebrow="Arquitetura de IA"
        title="Um supervisor, agentes especialistas e uma base de conhecimento"
        lead="O modelo de linguagem planeja; os agentes executam. Selecione uma camada para entender o papel dela."
      >
        <Architecture />
      </Section>

      <Section
        id="automacao"
        eyebrow="Automação da agenda"
        title="A IA só toca na sua agenda quando existe um plano"
        lead="Compare um pedido de planejamento, um comando direto e um bloco inválido."
      >
        <Automation />
      </Section>
    </>
  );
}
