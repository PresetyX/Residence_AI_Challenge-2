/**
 * Chat flow for the backend project planner.
 *
 * A message that describes a project ("quero criar um app de...") with a deadline goes
 * to POST /projetos. Without a deadline, the assistant asks for one and keeps the
 * description until the next message brings a date. Everything else (weekly plans by
 * free hours, refusals, free-slot queries) stays with the Supervisor stream.
 */
import { formatLongDate, formatShortDate, formatTimeRange } from "@/lib/format";
import type { ProjectPlan } from "@/lib/types";
import type { InferenceChunk } from "./inference-service";
import {
  mockHasPendingPlan,
  mockSetPendingGoal,
  parseGoal,
  resetMockSupervisor,
} from "./mocks/mock-supervisor";
import { ApiError, USE_CHAT_API } from "./http";
import { toCalendarEvent } from "./contracts";
import { NOT_UNDERSTOOD, projectService, scheduleService } from "./project-service";

/** Project described in an earlier turn, waiting for its deadline. */
let pendingProject: string | null = null;

/** Project the planner did not understand: the next message adds details, same deadline. */
let awaitingDetails: { description: string; deadline: Date } | null = null;

/** Plan shown in the thread, waiting for "sim" to be placed on the calendar. */
let pendingSchedule: { plan: ProjectPlan; goal: string } | null = null;

/** Preview of the calendar slots shown; waiting for the final "sim" to create them. */
let awaitingConfirm = false;

/** The assistant answered "não entendi" and asked what the project is: the next message is one. */
let awaitingProject = false;

/** Called when the backend asks for a project description (NDJSON "pedir_projeto"). */
export function expectProjectDescription(): void {
  awaitingProject = true;
}

/** Calendar questions keep going to the Supervisor even right after a "não entendi". */
const CALENDAR = /\b(agenda|horarios?|livres?|ocupad\w*|amanha|hoje)\b/;

export function resetProjectPlanner(): void {
  pendingProject = null;
  awaitingDetails = null;
  pendingSchedule = null;
  if (awaitingConfirm) void scheduleService.confirm(false).catch(() => undefined);
  awaitingConfirm = false;
  awaitingProject = false;
}

const normalize = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

const YES = /^(sim|s|pode|ok|okay|bora|claro|quero|confirmo|confirma|confirmar|isso|manda|vai|agend\w*|encaix\w*)\b/;
const NO = /^(nao|n|cancela\w*|deixa|agora nao|melhor nao)\b/;

const PROJECT =
  /\b(projeto|app|aplicativo|sistema|site|plataforma|api|software|produto|startup|mvp|jogo|game|dashboard|chatbot|bot|plano|planej\w*|planeje|tcc|monografia)\b|\b(quero|preciso|vou|gostaria de|pretendo)\s+(criar|desenvolver|construir|fazer|montar|lancar|entregar|programar|implementar)\b/;
/** Weekly plans by free hours belong to the Supervisor ("tenho 10 horas livres"). */
const HOURS = /\b\d{1,2}\s*horas?\b/;
/** Single appointments are refused by the Supervisor, never planned here. */
const SINGLE_ITEM = /\b(evento|compromisso|reuniao|lembrete|consulta)\b/;

const MONTHS = [
  "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];
const NUMBER_WORDS: Record<string, number> = { um: 1, uma: 1, dois: 2, duas: 2, tres: 3, quatro: 4, cinco: 5, seis: 6 };

function validDate(year: number, month: number, day: number): Date | null {
  const date = new Date(year, month - 1, day);
  return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day
    ? date
    : null;
}

/** Day/month without a year: the next time that date comes around. */
function nextOccurrence(month: number, day: number, today: Date): Date | null {
  const thisYear = validDate(today.getFullYear(), month, day);
  if (thisYear && thisYear >= today) return thisYear;
  return validDate(today.getFullYear() + 1, month, day);
}

/** Finds a deadline in free text: 2026-12-31, 31/12/2026, 31/12, "31 de dezembro", "em 3 semanas". */
export function parseDeadline(text: string, now = new Date()): Date | null {
  const t = normalize(text);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const iso = t.match(/\b(\d{4})-(\d{1,2})-(\d{1,2})\b/);
  if (iso) return validDate(Number(iso[1]), Number(iso[2]), Number(iso[3]));

  const br = t.match(/\b(\d{1,2})\/(\d{1,2})(?:\/(\d{4}|\d{2}))?\b/);
  if (br) {
    const [day, month] = [Number(br[1]), Number(br[2])];
    if (!br[3]) return nextOccurrence(month, day, today);
    const year = br[3].length === 2 ? 2000 + Number(br[3]) : Number(br[3]);
    return validDate(year, month, day);
  }

  const written = t.match(
    new RegExp(`\\b(\\d{1,2})\\s+de\\s+(${MONTHS.join("|")})(?:\\s+(?:de\\s+)?(\\d{4}))?`),
  );
  if (written) {
    const [day, month] = [Number(written[1]), MONTHS.indexOf(written[2]) + 1];
    return written[3] ? validDate(Number(written[3]), month, day) : nextOccurrence(month, day, today);
  }

  const relative = t.match(/\b(?:em|daqui a|dentro de)\s+(\d{1,3}|um|uma|dois|duas|tres|quatro|cinco|seis)\s+(dias?|semanas?|mes|meses)\b/);
  if (relative) {
    const amount = NUMBER_WORDS[relative[1]] ?? Number(relative[1]);
    const date = new Date(today);
    if (relative[2].startsWith("dia")) date.setDate(date.getDate() + amount);
    else if (relative[2].startsWith("semana")) date.setDate(date.getDate() + amount * 7);
    else date.setMonth(date.getMonth() + amount);
    return date;
  }

  if (/\b(fim|final) do ano\b/.test(t)) return new Date(today.getFullYear(), 11, 31);

  // "esta semana" -> this Sunday; "semana que vem" / "proxima semana" -> next Sunday.
  const sunday = new Date(today);
  sunday.setDate(today.getDate() + ((7 - today.getDay()) % 7));
  if (/\b(semana que vem|proxima semana|semana seguinte)\b/.test(t)) {
    sunday.setDate(sunday.getDate() + 7);
    return sunday;
  }
  if (/\b(esta|essa|nesta|nessa) semana\b/.test(t)) return sunday;
  return null;
}

const pad = (value: number) => String(value).padStart(2, "0");
const toIsoDate = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

const isPast = (date: Date, now: Date) =>
  date < new Date(now.getFullYear(), now.getMonth(), now.getDate());

/** "Quero desenvolver um app de controle de gastos pessoais" -> "App de controle de gastos pessoais". */
function goalFromDescription(description: string): string {
  const named = parseGoal(description);
  if (named) return named;
  const words = description
    .replace(/^.*?\b(?:criar|desenvolver|construir|fazer|montar|lançar|lancar|entregar|programar|implementar|realizar)\s+/i, "")
    .replace(/^(?:um|uma|o|a|meu|minha)\s+/i, "")
    .replace(/[,.;:!?].*$/, "")
    .split(/\s+/)
    .slice(0, 6)
    .join(" ");
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Projeto";
}

/**
 * Decides who answers this message: the backend planner (project + deadline) or the
 * Supervisor (weekly focus blocks by free hours, refusals, free slots). The two flows
 * share the conversation, so an open question in one of them wins over keywords:
 *
 *   - planner asked for the deadline and the user answers with free hours -> the user
 *     chose weekly blocks: the project description becomes the Supervisor's goal;
 *   - Supervisor asked for the goal (or the hours) -> its answer stays with it, even when
 *     it says "projeto", unless the message brings a deadline.
 */
export function routeToProjectPlanner(text: string): boolean {
  const t = normalize(text);
  const answer = t.trim();
  const hasDeadline = parseDeadline(text) !== null;

  // A plan or a calendar preview is waiting for a yes/no: that answer is ours.
  if (awaitingConfirm) {
    if (YES.test(answer) || NO.test(answer)) return true;
    awaitingConfirm = false;
    void scheduleService.confirm(false).catch(() => undefined);
  }
  if (pendingSchedule) {
    if (YES.test(answer) || NO.test(answer)) return true;
    pendingSchedule = null;
  }
  if (awaitingProject) {
    awaitingProject = false;
    if (!SINGLE_ITEM.test(t) && !CALENDAR.test(t) && !NO.test(answer)) return true;
  }

  if (pendingProject && hasDeadline) return true;
  if (SINGLE_ITEM.test(t)) {
    awaitingDetails = null;
    return false;
  }
  if (awaitingDetails && !HOURS.test(t)) return true;
  awaitingDetails = null;

  // The backend Supervisor has no weekly-hours plan (only the mock does): with the real
  // chat, "um plano para meu TCC, tenho 10 horas esta semana" goes to the planner.
  if (HOURS.test(t) && !(USE_CHAT_API && PROJECT.test(t))) {
    if (pendingProject) {
      if (!parseGoal(text)) mockSetPendingGoal(goalFromDescription(pendingProject));
      pendingProject = null;
    }
    return false;
  }

  if (mockHasPendingPlan() && !hasDeadline) return false;

  if (!PROJECT.test(t)) return false;
  // The planner takes over: forget any half-built weekly plan.
  resetMockSupervisor();
  return true;
}

/** Deadline at noon so the long date never slips a day across time zones. */
const longDate = (isoDate: string) => formatLongDate(`${isoDate}T12:00:00`);

function summarize(plan: ProjectPlan): string {
  const total = plan.tasks.reduce((sum, task) => sum + task.storyPoints, 0);
  const days = Math.round(
    (Date.parse(`${plan.deadline}T12:00:00`) - Date.now()) / (24 * 60 * 60 * 1000),
  );
  const first = plan.tasks[0];
  return [
    `Montei um plano em **${plan.tasks.length} etapas** para entregar até **${longDate(plan.deadline)}**${days > 0 ? ` (${days} dias)` : ""}. Esforço total estimado pela rede neural: **${total} story points**.`,
    "",
    `Comece pela etapa 1, **${first.title}**: o mais difícil é dar o primeiro passo. Abra cada etapa no cartão abaixo para ver o objetivo, os entregáveis e a demonstração.`,
  ].join("\n");
}

export async function* projectPlannerStream(
  text: string,
  signal?: AbortSignal,
): AsyncGenerator<InferenceChunk> {
  const answer = normalize(text).trim();
  if (awaitingConfirm) {
    awaitingConfirm = false;
    yield* confirmSchedule(YES.test(answer), signal);
    return;
  }
  if (pendingSchedule) {
    const pending = pendingSchedule;
    pendingSchedule = null;
    if (NO.test(answer)) {
      yield { type: "token", value: "Tudo bem, não mexi na sua agenda. O plano continua aqui no cartão." };
      return;
    }
    yield* previewSchedule(pending.plan, pending.goal, signal);
    return;
  }

  const now = new Date();
  const details = awaitingDetails;
  awaitingDetails = null;
  const deadline = parseDeadline(text, now) ?? details?.deadline ?? null;
  const description = details
    ? `${details.description}\n${text}`
    : pendingProject && !PROJECT.test(normalize(text))
      ? pendingProject
      : text;

  if (!deadline) {
    pendingProject = description;
    yield {
      type: "token",
      value:
        "Bora destravar esse projeto! Qual é o **prazo de entrega**? Pode ser uma data (*31/12/2026*) ou um tempo (*em 6 semanas*).",
    };
    return;
  }
  if (isPast(deadline, now)) {
    pendingProject = description;
    yield {
      type: "token",
      value: `Esse prazo (**${longDate(toIsoDate(deadline))}**) já passou. Qual é a nova data de entrega?`,
    };
    return;
  }

  pendingProject = null;
  yield {
    type: "status",
    value: "Dividindo o projeto em etapas e estimando os story points. Isso pode levar alguns minutos…",
  };
  let plan: ProjectPlan;
  try {
    plan = await projectService.planProject(description, toIsoDate(deadline), signal);
  } catch (error) {
    if (error instanceof ApiError && error.kind === NOT_UNDERSTOOD) {
      awaitingDetails = { description, deadline };
      yield { type: "token", value: error.message };
      return;
    }
    throw error;
  }
  pendingSchedule = { plan, goal: goalFromDescription(description) };
  yield {
    type: "token",
    value: `${summarize(plan)}\n\nQuer que eu encaixe essas etapas nos seus horários livres do Google Agenda até **${longDate(plan.deadline)}**? Responda **sim** ou **não**.`,
  };
  yield { type: "project_plan", plan };
}

const CLASS_LABEL = { tranquilo: "🟢 Prazo tranquilo", corrido: "🟡 Prazo corrido", impossivel: "🔴 Prazo impossível" };

/** Asks the Supervisor to classify the deadline and lay the steps on free slots (nothing created yet). */
async function* previewSchedule(
  plan: ProjectPlan,
  goal: string,
  signal?: AbortSignal,
): AsyncGenerator<InferenceChunk> {
  yield { type: "status", value: "Classificando o prazo e procurando horários livres na sua agenda…" };
  const preview = await scheduleService.preview(plan, goal, signal);
  const slots = preview.dados?.eventos ?? [];
  const kind = preview.classificacao ?? preview.dados?.classificacao;
  const heading = kind ? `**${CLASS_LABEL[kind]}.** ` : "";

  if (preview.status !== "confirmacao" || slots.length === 0) {
    yield { type: "token", value: `${heading}${preview.mensagem}` };
    return;
  }

  awaitingConfirm = true;
  const lines = slots.map(
    (slot) =>
      `- **${slot.titulo.replace(/^\[Destrava\]\s*/, "")}** · ${formatShortDate(slot.inicio)}, ${formatTimeRange(slot.inicio, slot.fim)}`,
  );
  yield {
    type: "token",
    value: [
      `${heading}${preview.mensagem.replace(/\s*Confira a previa e responda 'sim' ou 'nao'\.?/i, "")}`,
      "",
      ...lines,
      "",
      `Responda **sim** para criar ${slots.length === 1 ? "o evento" : `os ${slots.length} eventos`} ou **não** para cancelar.`,
    ].join("\n"),
  };
}

/** Creates (or drops) the previewed slots; each created event becomes a calendar card. */
async function* confirmSchedule(confirmed: boolean, signal?: AbortSignal): AsyncGenerator<InferenceChunk> {
  if (confirmed) yield { type: "status", value: "Criando os eventos no Google Agenda…" };
  const result = await scheduleService.confirm(confirmed, signal);
  yield { type: "token", value: result.mensagem };
  for (const dto of result.dados?.eventos_criados ?? []) {
    const snapshot = toCalendarEvent(dto);
    yield { type: "calendar_action", action: { type: "created", eventId: snapshot.id, snapshot } };
  }
}
