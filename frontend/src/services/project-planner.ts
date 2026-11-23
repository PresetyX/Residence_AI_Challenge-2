/**
 * Chat flow for the project planner (backend: POST /projetos and the scheduling routes).
 *
 * A message that describes a project goes to the Planejador. The deadline is read by the
 * backend Supervisor from the message itself ("até amanhã", "tenho uma semana", "20/12",
 * "em 3 meses"...). Without one, the plan is made anyway and the assistant asks only for
 * the deadline; the answer is read by the backend too. Then the assistant offers to place
 * the steps on the calendar (deadline class + preview) and creates them after a "sim".
 * Everything else (free slots, single events) stays with the Supervisor chat stream.
 */
import { formatLongDate, formatShortDate, formatTimeRange } from "@/lib/format";
import type { ProjectPlan } from "@/lib/types";
import { toCalendarEvent } from "./contracts";
import { ApiError } from "./http";
import type { InferenceChunk } from "./inference-service";
import { NOT_UNDERSTOOD, projectService, scheduleService } from "./project-service";

/** Project planned without a deadline: the next message should bring it. */
let pendingProject: { description: string; draft: ProjectPlan } | null = null;

/** Project the planner did not understand (or the Supervisor asked for one): the next message adds details. */
let awaitingDetails: { description: string; deadline: string | null } | null = null;

/** Plan shown in the thread, waiting for "sim" to be placed on the calendar. */
let pendingSchedule: { plan: ProjectPlan; goal: string } | null = null;

/** Preview of the calendar slots shown; waiting for the final "sim" to create them. */
let awaitingConfirm = false;

export function resetProjectPlanner(): void {
  pendingProject = null;
  awaitingDetails = null;
  pendingSchedule = null;
  if (awaitingConfirm) void scheduleService.confirm(false).catch(() => undefined);
  awaitingConfirm = false;
}

/** Called when the backend answers "não entendi" and asks for a project (NDJSON "pedir_projeto"). */
export function expectProjectDescription(): void {
  awaitingDetails = { description: "", deadline: null };
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
/** Single appointments belong to the Supervisor ("crie uma reunião amanhã das 13h às 14h"). */
const SINGLE_ITEM = /\b(evento|compromisso|reuniao|lembrete|consulta)\b/;
/** Calendar questions keep going to the Supervisor ("quais meus horários livres?"). */
const CALENDAR = /\b(agenda|horarios?|livres?|ocupad\w*)\b/;

/** Decides who answers this message: the planner flow (true) or the Supervisor stream. */
export function routeToProjectPlanner(text: string): boolean {
  const t = normalize(text);
  const answer = t.trim();

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

  if (SINGLE_ITEM.test(t) || CALENDAR.test(t)) {
    pendingProject = null;
    awaitingDetails = null;
    return false;
  }
  if (pendingProject || awaitingDetails) return !NO.test(answer);
  return PROJECT.test(t);
}

/** Deadline at noon so the long date never slips a day across time zones. */
const longDate = (isoDate: string) => formatLongDate(`${isoDate}T12:00:00`);

function summarize(plan: ProjectPlan): string {
  const total = plan.tasks.reduce((sum, task) => sum + task.storyPoints, 0);
  const minutes = plan.tasks.reduce((sum, task) => sum + (task.estimatedMinutes ?? task.storyPoints * 60), 0);
  const perPoint = total > 0 ? Math.round(minutes / total) : 60;
  const hours = Math.round((minutes / 60) * 10) / 10;
  const days = Math.round(
    (Date.parse(`${plan.deadline}T12:00:00`) - Date.now()) / (24 * 60 * 60 * 1000),
  );
  const first = plan.tasks[0];
  return [
    `Montei um plano em **${plan.tasks.length} etapas** para entregar até **${longDate(plan.deadline)}**${days > 0 ? ` (${days} dias)` : ""}. Esforço total estimado pela rede neural: **${total} story points** (≈ **${hours.toLocaleString("pt-BR")} h** de trabalho, 1 story point = ${perPoint} min).`,
    "",
    `Comece pela etapa 1, **${first.title}**: o mais difícil é dar o primeiro passo. Abra cada etapa no cartão abaixo para ver o objetivo, os entregáveis e a demonstração.`,
  ].join("\n");
}

/** "Quero desenvolver um app de controle de gastos" -> "App de controle de gastos". */
function goalFromDescription(description: string): string {
  const named = description.match(/\b(tcc|monografia|disserta[çc][ãa]o|tese)\b/i);
  if (named) return named[1].length <= 3 ? named[1].toUpperCase() : named[1];
  const words = description
    .trim()
    .replace(/^.*?\b(?:criar|desenvolver|construir|fazer|montar|lançar|lancar|entregar|programar|implementar)\s+/i, "")
    .replace(/^(?:um|uma|o|a|meu|minha)\s+/i, "")
    .replace(/[,.;:!?].*$/s, "")
    .split(/\s+/)
    .slice(0, 6)
    .join(" ");
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Projeto";
}

const ASK_DEADLINE =
  "Qual é o **prazo de entrega**? Pode ser uma data (*20/12*, *20 de dezembro*) ou um tempo (*até amanhã*, *tenho uma semana*, *em 3 meses*).";

/** Turns a 422 from the backend (date that does not exist or already passed) into a reply. */
function isDeadlineError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 422;
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
      yield { type: "conversation_end" };
      return;
    }
    yield* previewSchedule(pending.plan, pending.goal, signal);
    return;
  }

  // The answer to "qual é o prazo?": the plan is already made, only the date is missing.
  if (pendingProject && !PROJECT.test(normalize(text))) {
    const pending = pendingProject;
    let deadline: string | null;
    try {
      deadline = await projectService.interpretDeadline(text, signal);
    } catch (error) {
      if (!isDeadlineError(error)) throw error;
      yield { type: "token", value: error.message };
      return;
    }
    if (!deadline) {
      yield { type: "token", value: `Não consegui entender o prazo. ${ASK_DEADLINE}` };
      return;
    }
    pendingProject = null;
    yield* offerPlan({ ...pending.draft, deadline }, pending.description);
    return;
  }

  const details = awaitingDetails;
  awaitingDetails = null;
  pendingProject = null;
  const description = details?.description ? `${details.description}\n${text}` : text;

  yield {
    type: "status",
    value: "Dividindo o projeto em etapas e estimando os story points. Isso pode levar alguns minutos…",
  };
  let planned;
  try {
    planned = await projectService.planProject(description, details?.deadline ?? null, signal);
  } catch (error) {
    if (error instanceof ApiError && error.kind === NOT_UNDERSTOOD) {
      awaitingDetails = { description, deadline: details?.deadline ?? null };
      yield { type: "token", value: error.message };
      return;
    }
    if (isDeadlineError(error)) {
      // Date that does not exist or already passed: ask again, keep the project.
      awaitingDetails = { description, deadline: null };
      yield { type: "token", value: error.message };
      return;
    }
    throw error;
  }

  if (planned.needsDeadline) {
    pendingProject = { description, draft: planned.plan };
    yield {
      type: "token",
      value: `Bora destravar esse projeto! Já dividi em **${planned.plan.tasks.length} etapas**. ${ASK_DEADLINE}`,
    };
    return;
  }
  yield* offerPlan(planned.plan, description);
}

/** Shows the plan card and offers to place the steps on the calendar. */
function* offerPlan(plan: ProjectPlan, description: string): Generator<InferenceChunk> {
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
  const preview = await scheduleService.preview(plan, signal);
  const slots = preview.dados?.eventos ?? [];
  const kind = preview.classificacao ?? preview.dados?.classificacao;
  const heading = kind ? `**${CLASS_LABEL[kind]}.** ` : "";

  if (preview.status !== "confirmacao" || slots.length === 0) {
    // Impossible deadline (or nothing to place): this plan ends here.
    yield { type: "token", value: `${heading}${preview.mensagem}` };
    yield { type: "conversation_end" };
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
  // Scheduled, cancelled or failed: either way this plan is settled.
  yield { type: "conversation_end" };
}
