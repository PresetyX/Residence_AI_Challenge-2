/**
 * Mock of the Supervisor. It applies the rules in lib/assistant-rules.ts with keyword
 * matching so the UI is fully explorable without the backend:
 *
 *   - direct commands ("crie um evento às 15h") are refused, never executed;
 *   - a goal + available hours becomes a plan: a batch of focus blocks in the calendar;
 *   - a change in available hours re-fits the plan's blocks;
 *   - giving up on the goal clears the plan's blocks.
 *
 * None of this ships to production; the real model receives SYSTEM_PROMPT instead.
 */
import { DIRECT_COMMAND_REFUSAL } from "@/lib/assistant-rules";
import { formatLongDate, formatTime, formatTimeRange } from "@/lib/format";
import { getModel } from "@/lib/models";
import type { CalendarAction, CalendarEvent, ModelId } from "@/lib/types";
import { buildDeletePayload, calendarService } from "../calendar-service";
import { delay } from "../http";
import type { InferenceChunk, InferenceRequest } from "../inference-service";

interface Reply {
  text: string;
  actions?: CalendarAction[];
  suggestsManualPanel?: boolean;
}

/** Milliseconds per streamed word and "thinking" time before the first token. */
const MODEL_PACING: Record<ModelId, { thinkMs: number; wordMs: number }> = {
  "gemma-2b": { thinkMs: 1100, wordMs: 48 },
  "gemma-4-26b-a4b-q4_0": { thinkMs: 600, wordMs: 16 },
  "gemma-4-12b-sfp8": { thinkMs: 750, wordMs: 26 },
};

const HOUR_MS = 60 * 60 * 1000;
const BLOCK_HOURS = 2;
const MAX_PLAN_HOURS = 40;
const DAY_START_HOUR = 7;
const DAY_END_HOUR = 23;
const WEEKDAYS = ["domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado"];

/** A goal or an hour budget mentioned in an earlier turn, waiting for its other half. */
let pendingGoal: string | null = null;
let pendingHours: number | null = null;
/** Planning window ("nas próximas duas semanas") mentioned before the plan was complete. */
let pendingDays: number | null = null;

export function resetMockSupervisor(): void {
  pendingGoal = null;
  pendingHours = null;
  pendingDays = null;
}

/** True while the Supervisor is waiting for the other half of a plan (goal or hours). */
export function mockHasPendingPlan(): boolean {
  return pendingGoal !== null || pendingHours !== null;
}

/** Hands over a goal the user already gave elsewhere in the conversation. */
export function mockSetPendingGoal(goal: string): void {
  pendingGoal = goal;
}

const normalize = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

const plural = (count: number, one: string, many: string) =>
  `${count} ${count === 1 ? one : many}`;

// ---------------------------------------------------------------------------
// Intent detection
// ---------------------------------------------------------------------------

const PLAN_CANCEL =
  /(nao tenho mais tempo|nao vou ter tempo|nao terei tempo|fiquei sem tempo|desist)|\b(desmarqu|cancel|remov|apag|exclu)\w*\s+(tudo|todos|todas|o plano|meu plano|o cronograma|os blocos)/;
const DIRECT_VERB =
  /\b(cri[ae]|criar|agend|mar[cq]|adicion|reserv|apag|exclu|delet|remov|cancel|desmarqu|edit|alter|mud[ae]|remar[cq]|reagend|troc|adi[ae])/;
const SINGLE_ITEM = /\b(evento|compromisso|reuniao|lembrete|tarefa|consulta|horario d[oae])\b/;
const PLAN_WORD = /\b(plano|planej|cronograma)/;
const PLANNING =
  /\b(plano|planej|cronograma|organiz|mont[ae]|meta|projeto|tcc|estud|prova|destrav|dividi|quebr|prazo)|preciso (fazer|entregar|terminar)/;
const VIEW = /\b(livres?|disponi|minha agenda|compromissos)\b/;
const CONTRACT = /\b(json|contrato|codigo|api)\b/;

interface HourBudget {
  total?: number;
  delta?: number;
}

/** "tenho 10 horas livres" -> total; "consegui mais 2 horas" -> delta. Ignores "às 15h". */
function parseHours(text: string): HourBudget {
  const total =
    text.match(/\btenho\s+(?:agora\s+)?(?:so\s+|apenas\s+)?(\d{1,2})\s*(?:horas?|h)\b/) ??
    text.match(/\b(\d{1,2})\s*(?:horas?|h)\s+(?:livres?|disponiveis|por semana|(?:n?esta|na) semana)/);
  const delta = text.match(/\b(mais|menos)\s+(\d{1,2})\s*(?:horas?|h)\b/);
  return {
    total: total ? Number(total[1]) : undefined,
    delta: delta ? Number(delta[2]) * (delta[1] === "mais" ? 1 : -1) : undefined,
  };
}

const WEEK_WORDS: Record<string, number> = { uma: 1, duas: 2, dois: 2, tres: 3, quatro: 4 };
const DEFAULT_DAYS = 7;
const MAX_DAYS = 28;

/** "nas próximas duas semanas" -> 14; "nos próximos 10 dias" -> 10; "esta semana" -> 7. */
function parseHorizonDays(text: string): number | undefined {
  const weeks = text.match(/\b(\d|uma|duas|dois|tres|quatro)\s+semanas?\b/);
  if (weeks) return Math.min((WEEK_WORDS[weeks[1]] ?? Number(weeks[1])) * 7, MAX_DAYS);
  const days = text.match(/\b(\d{1,2})\s+dias\b/);
  if (days) return Math.min(Math.max(Number(days[1]), 1), MAX_DAYS);
  return undefined;
}

export function parseGoal(original: string): string | null {
  // "projeto chamado DUAT", "no projeto DUAT", "projeto Nota Dez": a proper name after "projeto".
  const projectName = original.match(
    /\bprojeto\s+(?:chamad[oa]\s+|denominad[oa]\s+|intitulad[oa]\s+)?["“']?(\p{Lu}[\p{L}\d-]*(?:\s+\p{Lu}[\p{L}\d-]*){0,3})/u,
  );
  if (projectName) return projectName[1];

  const named = original.match(
    /\b(tcc|monografia|disserta[çc][ãa]o|tese|artigo|portf[óo]lio|relat[óo]rio)\b/i,
  );
  if (named) return named[1].length <= 3 ? named[1].toUpperCase() : capitalize(named[1].toLowerCase());

  const withSubject = original.match(
    /\b(prova|trabalho|projeto|curso|apresenta[çc][ãa]o|concurso|certifica[çc][ãa]o)\s+(?:de|do|da|sobre)\s+[\p{L}\d]+(?:\s+(?!na\b|no\b|em\b|esta\b|nesta\b|para\b|e\b|que\b|tenho\b|com\b)[\p{L}\d]+)?/iu,
  );
  if (withSubject) return capitalize(withSubject[0].toLowerCase());

  const study = original.match(/\bestudar\s+(?:para\s+)?(?:a\s+|o\s+)?([\p{L}\d]+)/iu);
  if (study) return `Estudo de ${study[1].toLowerCase()}`;
  return null;
}

// ---------------------------------------------------------------------------
// Planning engine
// ---------------------------------------------------------------------------

/** 10 h -> [2, 2, 2, 2, 2]; 7 h -> [2, 2, 2, 1]. */
function splitIntoBlocks(hours: number): number[] {
  const blocks = Array<number>(Math.floor(hours / BLOCK_HOURS)).fill(BLOCK_HOURS);
  if (hours % BLOCK_HOURS) blocks.push(hours % BLOCK_HOURS);
  return blocks;
}

function phaseName(index: number, count: number): string {
  if (count === 1) return "Sessão de foco";
  if (index === 0) return "Escopo e roteiro";
  if (index === count - 1) return "Revisão e fechamento";
  if (index === 1 && count >= 4) return "Pesquisa e referências";
  return "Desenvolvimento";
}

/**
 * Candidate block starts for the next 7 days: evenings first (mornings on weekends),
 * then a second and third pass so bigger budgets still fit.
 */
function candidateStarts(now: Date, days: number): Date[] {
  const passes: Array<{ weekday: number; weekend: number }> = [
    { weekday: 19, weekend: 9 },
    { weekday: 7, weekend: 14 },
    { weekday: 12, weekend: 17 },
  ];
  const starts: Date[] = [];
  for (const pass of passes) {
    for (let offset = 1; offset <= days; offset++) {
      const start = new Date(now);
      start.setDate(start.getDate() + offset);
      const isWeekend = start.getDay() === 0 || start.getDay() === 6;
      start.setHours(isWeekend ? pass.weekend : pass.weekday, 0, 0, 0);
      starts.push(start);
    }
  }
  return starts;
}

interface Slot {
  start: Date;
  end: Date;
}

const overlaps = (slot: Slot, event: Pick<CalendarEvent, "start" | "end">) =>
  slot.start.getTime() < Date.parse(event.end) && slot.end.getTime() > Date.parse(event.start);

/** Picks `count` free 2-hour windows that do not collide with anything on the calendar. */
function pickFreeSlots(count: number, busy: CalendarEvent[], days = DEFAULT_DAYS): Slot[] {
  const picked: Slot[] = [];
  for (const start of candidateStarts(new Date(), days)) {
    if (picked.length === count) break;
    const slot = { start, end: new Date(start.getTime() + BLOCK_HOURS * HOUR_MS) };
    if (busy.some((event) => overlaps(slot, event))) continue;
    picked.push(slot);
  }
  return picked;
}

const planHours = (events: CalendarEvent[]) =>
  events.reduce((sum, event) => sum + (Date.parse(event.end) - Date.parse(event.start)) / HOUR_MS, 0);

function planTable(events: CalendarEvent[]): string[] {
  return [
    "| Dia | Horário | Etapa |",
    "|---|---|---|",
    ...events.map(
      (event) =>
        `| ${capitalize(formatLongDate(event.start).replace(/ de \d{4}$/, ""))} | ${formatTimeRange(event.start, event.end)} | ${event.title.split(": ")[1] ?? event.title} |`,
    ),
  ];
}

function blockInput(goal: string, index: number, count: number, start: Date, hours: number) {
  return {
    title: `${goal}: ${phaseName(index, count)}`,
    description: `Bloco ${index + 1} de ${count} do plano “${goal}”, criado pelo Destrava.`,
    start: start.toISOString(),
    end: new Date(start.getTime() + hours * HOUR_MS).toISOString(),
    location: "",
  };
}

/** The plan the user is most likely talking about: named in the message, else the latest. */
async function findActivePlan(text: string): Promise<{ goal: string; events: CalendarEvent[] } | null> {
  const planned = (await calendarService.listEvents()).filter((event) => event.planGoal);
  if (planned.length === 0) return null;

  const goals = [...new Set(planned.map((event) => event.planGoal as string))];
  const latest = [...planned].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0];
  const goal = goals.find((name) => text.includes(normalize(name))) ?? (latest.planGoal as string);
  return { goal, events: planned.filter((event) => event.planGoal === goal) };
}

async function createPlan(goal: string, requestedHours: number, days = DEFAULT_DAYS): Promise<Reply> {
  const hours = Math.min(requestedHours, MAX_PLAN_HOURS);
  const durations = splitIntoBlocks(hours);
  const slots = pickFreeSlots(durations.length, await calendarService.listEvents(), days).sort(
    (a, b) => a.start.getTime() - b.start.getTime(),
  );

  const events = await Promise.all(
    slots.map((slot, index) =>
      calendarService.createEvent(
        blockInput(goal, index, slots.length, slot.start, durations[index]),
        goal,
      ),
    ),
  );
  pendingGoal = null;
  pendingHours = null;
  pendingDays = null;

  return {
    text: [
      `Bora destravar **${goal}**! Dividi as suas **${hours} horas** em ${plural(events.length, "bloco de foco", "blocos de foco")} nos próximos ${days} dias, sem conflito com o que já está na agenda.`,
      "",
      ...planTable(events),
      "",
      "Comece pelo primeiro bloco: o mais difícil é abrir o arquivo. Se o seu tempo mudar, é só me avisar (*“agora tenho 12 horas livres”*) que eu reorganizo tudo.",
    ].join("\n"),
    actions: events.map((event) => ({ type: "created", eventId: event.id, snapshot: event })),
  };
}

async function adaptPlan(
  plan: { goal: string; events: CalendarEvent[] },
  budget: HourBudget,
): Promise<Reply> {
  const currentHours = planHours(plan.events);
  const targetHours = Math.min(budget.total ?? currentHours + (budget.delta ?? 0), MAX_PLAN_HOURS);
  if (targetHours <= 0) return cancelPlan(plan);
  if (targetHours === currentHours) {
    return {
      text: `O plano **${plan.goal}** já ocupa exatamente **${currentHours} horas**. Não precisei mudar nada.`,
    };
  }

  const existing = [...plan.events].sort((a, b) => a.start.localeCompare(b.start));
  const durations = splitIntoBlocks(targetHours);
  const kept = existing.slice(0, durations.length);
  const surplus = existing.slice(durations.length);
  const actions: CalendarAction[] = [];

  await Promise.all(
    surplus.map((event) => calendarService.deleteEvent(buildDeletePayload(event, "plano_ia"))),
  );
  surplus.forEach((event) => actions.push({ type: "deleted", eventId: event.id, snapshot: event }));

  // New blocks may land between the kept ones, so order everything before naming phases.
  const newSlots = pickFreeSlots(durations.length - kept.length, await calendarService.listEvents());
  const timeline = [
    ...kept.map((event) => ({ start: new Date(event.start), event })),
    ...newSlots.map((slot) => ({ start: slot.start, event: undefined as CalendarEvent | undefined })),
  ].sort((a, b) => a.start.getTime() - b.start.getTime());

  const result = await Promise.all(
    timeline.map(async ({ start, event }, index) => {
      const input = blockInput(plan.goal, index, timeline.length, start, durations[index]);
      if (!event) {
        const created = await calendarService.createEvent(input, plan.goal);
        actions.push({ type: "created", eventId: created.id, snapshot: created });
        return created;
      }
      if (event.title === input.title && event.end === input.end) return event;
      const updated = await calendarService.updateEvent(event.id, {
        ...input,
        location: event.location,
      });
      actions.push({ type: "updated", eventId: updated.id, snapshot: updated });
      return updated;
    }),
  );

  const count = (type: CalendarAction["type"]) => actions.filter((action) => action.type === type).length;
  const changes = [
    count("created") && plural(count("created"), "bloco novo", "blocos novos"),
    count("updated") && plural(count("updated"), "bloco ajustado", "blocos ajustados"),
    count("deleted") && plural(count("deleted"), "bloco removido", "blocos removidos"),
  ].filter(Boolean);

  return {
    text: [
      `Replanejei **${plan.goal}**: de ${currentHours} h para **${targetHours} h** nesta semana (${changes.join(", ")}).`,
      "",
      ...planTable(result),
      "",
      targetHours > currentHours
        ? "Mais tempo, mais avanço. Mantive os blocos que você já tinha e encaixei os novos nos horários livres."
        : "Menos tempo, mesmo foco. Priorizei os primeiros blocos para você não perder o ritmo.",
    ].join("\n"),
    actions: actions.sort((a, b) => a.snapshot.start.localeCompare(b.snapshot.start)),
  };
}

async function cancelPlan(plan: { goal: string; events: CalendarEvent[] }): Promise<Reply> {
  await Promise.all(
    plan.events.map((event) => calendarService.deleteEvent(buildDeletePayload(event, "plano_ia"))),
  );
  return {
    text: [
      `Tudo bem, acontece. Desmarquei ${plural(plan.events.length, "bloco", "blocos")} do plano **${plan.goal}** e liberei **${planHours(plan.events)} horas** na sua agenda.`,
      "",
      "Seus compromissos manuais continuam intactos. Quando tiver tempo de novo, me diga quantas horas livres você tem e eu remonto o plano.",
    ].join("\n"),
    actions: plan.events
      .sort((a, b) => a.start.localeCompare(b.start))
      .map((event) => ({ type: "deleted", eventId: event.id, snapshot: event })),
  };
}

// ---------------------------------------------------------------------------
// Read-only and informational replies
// ---------------------------------------------------------------------------

function parseDay(text: string, now: Date): Date {
  const day = new Date(now);
  day.setHours(0, 0, 0, 0);

  const numeric = text.match(/\b(\d{1,2})\/(\d{1,2})\b/);
  if (numeric) {
    day.setMonth(Number(numeric[2]) - 1, Number(numeric[1]));
    if (day < now) day.setFullYear(day.getFullYear() + 1);
    return day;
  }
  if (text.includes("depois de amanha")) day.setDate(day.getDate() + 2);
  else if (text.includes("amanha")) day.setDate(day.getDate() + 1);
  else if (!/\bhoje\b/.test(text)) {
    const weekday = WEEKDAYS.findIndex((name) => new RegExp(`\\b${name}\\b`).test(text));
    if (weekday >= 0) day.setDate(day.getDate() + ((weekday - day.getDay() + 7) % 7 || 7));
    else day.setDate(day.getDate() + 1);
  }
  return day;
}

async function replyView(text: string): Promise<Reply> {
  const day = parseDay(text, new Date());
  const dayStart = new Date(day);
  dayStart.setHours(DAY_START_HOUR, 0, 0, 0);
  const dayEnd = new Date(day);
  dayEnd.setHours(DAY_END_HOUR, 0, 0, 0);

  const busy = (await calendarService.listEvents()).filter((event) =>
    overlaps({ start: dayStart, end: dayEnd }, event),
  );

  const free: Slot[] = [];
  let cursor = dayStart;
  for (const event of busy) {
    const start = new Date(event.start);
    if (start > cursor) free.push({ start: cursor, end: start });
    const end = new Date(event.end);
    if (end > cursor) cursor = end;
  }
  if (cursor < dayEnd) free.push({ start: cursor, end: dayEnd });

  const minutesOf = (slot: Slot) => (slot.end.getTime() - slot.start.getTime()) / 60000;
  const totalHours = Math.round((free.reduce((sum, slot) => sum + minutesOf(slot), 0) / 60) * 10) / 10;
  const rows = free.map((slot) => {
    const minutes = minutesOf(slot);
    const duration = `${Math.floor(minutes / 60)} h${minutes % 60 ? ` ${minutes % 60} min` : ""}`;
    return `| ${formatTime(slot.start.toISOString())} | ${formatTime(slot.end.toISOString())} | ${duration} |`;
  });

  return {
    text: [
      `Consultei sua agenda de **${formatLongDate(day.toISOString())}**.`,
      "",
      busy.length === 0
        ? "Você não tem compromissos nesse dia."
        : `Compromissos: ${busy.map((event) => `**${event.title}** (${formatTimeRange(event.start, event.end)})`).join(", ")}.`,
      "",
      "### Horários livres",
      "",
      "| Início | Fim | Duração |",
      "|---|---|---|",
      ...rows,
      "",
      `Total livre: **${totalHours} h**. Qual meta você quer encaixar nesse tempo?`,
    ].join("\n"),
  };
}

function replyContract(): Reply {
  return {
    text: [
      "Cada agente recebe um JSON e devolve um JSON no mesmo formato. Quando monto um plano, envio um pedido como este ao agente **criar** para cada bloco:",
      "",
      "```json",
      "{",
      '  "titulo": "TCC: Escopo e roteiro",',
      '  "inicio": "2026-11-16T19:00",',
      '  "fim": "2026-11-16T21:00"',
      "}",
      "```",
      "",
      "E é assim que o Supervisor o chama em Python:",
      "",
      "```python",
      "from destrava.agents import criar",
      "",
      "for bloco in plano:",
      "    resposta = criar.executar_json(bloco)",
      '    if resposta["status"] == "erro":',
      '        print(resposta["erro"]["mensagem"])',
      "```",
      "",
      "A resposta sempre traz `status`, `acao`, `periodo`, `dados`, `fluxo` e `erro`. Pedidos inválidos voltam como `\"status\": \"erro\"`, sem alterar a agenda.",
    ].join("\n"),
  };
}

function replyDefault(modelId: ModelId): Reply {
  const model = getModel(modelId);
  return {
    text: [
      `Olá! Sou o **Destrava**. Estou aqui para te ajudar a parar de adiar e tirar projetos do papel. Estou respondendo com o modelo **${model.shortName}** (${model.description.toLowerCase()}).`,
      "",
      "Funciona assim:",
      "",
      "1. **Você me conta a meta e o tempo que tem.** *“Monte um plano para eu fazer meu TCC, tenho 10 horas livres esta semana.”*",
      "2. **Eu divido em blocos de foco** e agendo tudo nos seus horários livres.",
      "3. **Se a semana mudar, eu replanejo.** *“Agora tenho 12 horas”* ou *“não tenho mais tempo, desmarque tudo”*.",
      "",
      "Compromissos simples, como uma reunião às 15h, você cria direto no painel **Agenda**.",
      "",
      "Qual meta ou projeto você quer destravar hoje?",
    ].join("\n"),
  };
}

// ---------------------------------------------------------------------------

async function buildReply(original: string, modelId: ModelId): Promise<Reply> {
  const text = normalize(original);
  const budget = parseHours(text);
  const hasBudget = budget.total !== undefined || budget.delta !== undefined;
  const plan = await findActivePlan(text);
  const refusal: Reply = { text: DIRECT_COMMAND_REFUSAL, suggestsManualPanel: true };

  if (PLAN_CANCEL.test(text)) {
    return plan
      ? cancelPlan(plan)
      : { text: "Não encontrei nenhum plano ativo na sua agenda para desmarcar. Seus compromissos manuais você gerencia no painel **Agenda**." };
  }

  // "Crie um evento…", "Apague a tarefa X", "Edite o horário do evento Y".
  if (DIRECT_VERB.test(text) && SINGLE_ITEM.test(text) && !PLAN_WORD.test(text)) return refusal;

  if (plan && hasBudget) return adaptPlan(plan, budget);

  const days = parseHorizonDays(text) ?? pendingDays ?? DEFAULT_DAYS;

  if (PLANNING.test(text)) {
    const goal = parseGoal(original) ?? pendingGoal;
    const hours = budget.total ?? pendingHours;
    if (!goal) {
      pendingHours = hours;
      pendingDays = days;
      return { text: "Bora! Qual é a meta ou o projeto que você quer destravar? Pode ser um TCC, uma prova, um projeto do trabalho…" };
    }
    if (!hours) {
      pendingGoal = goal;
      pendingDays = days;
      return { text: `Fechado, vamos destravar **${goal}**. Quantas horas livres você tem para isso?` };
    }
    return createPlan(goal, hours, days);
  }

  // Answer to "which goal?" after the hours: "DUAT", "meu portfólio"... a short name is enough.
  if (pendingHours !== null && budget.total === undefined) {
    const shortAnswer = original.trim().replace(/[.!?]+$/, "");
    const goal =
      parseGoal(original) ??
      (shortAnswer.split(/\s+/).length <= 4 && !DIRECT_VERB.test(text)
        ? capitalize(shortAnswer.replace(/^(?:o|a|no|na|meu|minha|para o|para a)\s+/i, ""))
        : null);
    if (goal) return createPlan(goal, pendingHours, days);
  }

  // Answer to "how many hours do you have?": a bare number is enough.
  if (pendingGoal && budget.total === undefined) {
    const bare = text.match(/^\D*(\d{1,2})\s*(?:horas?|h)?\D*$/);
    if (bare) return createPlan(pendingGoal, Number(bare[1]), days);
  }

  if (budget.total !== undefined) {
    if (pendingGoal) return createPlan(pendingGoal, budget.total, days);
    pendingHours = budget.total;
    pendingDays = days;
    return { text: `Boa, **${budget.total} horas** dá para avançar bastante. Em qual meta ou projeto você quer investir esse tempo?` };
  }

  if (DIRECT_VERB.test(text)) return refusal;
  if (VIEW.test(text)) return replyView(text);
  if (CONTRACT.test(text)) return replyContract();
  return replyDefault(modelId);
}

export async function* mockStreamChat(
  { modelId, messages }: InferenceRequest,
  signal?: AbortSignal,
): AsyncGenerator<InferenceChunk> {
  const pacing = MODEL_PACING[modelId];
  const lastUserMessage = [...messages].reverse().find((message) => message.role === "user");

  await delay(pacing.thinkMs, signal);
  const reply = await buildReply(lastUserMessage?.content ?? "", modelId);

  for (const word of reply.text.match(/\S+\s*/g) ?? []) {
    await delay(pacing.wordMs, signal);
    yield { type: "token", value: word };
  }
  for (const action of reply.actions ?? []) yield { type: "calendar_action", action };
  if (reply.suggestsManualPanel) yield { type: "suggest_manual_panel" };
}
