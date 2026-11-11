/**
 * Chat flow for the backend project planner.
 *
 * A message that describes a project ("quero criar um app de...") with a deadline goes
 * to POST /projetos. Without a deadline, the assistant asks for one and keeps the
 * description until the next message brings a date. Everything else (weekly plans by
 * free hours, refusals, free-slot queries) stays with the Supervisor stream.
 */
import { formatLongDate } from "@/lib/format";
import type { ProjectPlan } from "@/lib/types";
import type { InferenceChunk } from "./inference-service";
import { projectService } from "./project-service";

/** Project described in an earlier turn, waiting for its deadline. */
let pendingProject: string | null = null;

export function resetProjectPlanner(): void {
  pendingProject = null;
}

const normalize = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

const PROJECT =
  /\b(projeto|app|aplicativo|sistema|site|plataforma|api|software|produto|startup|mvp|jogo|game|dashboard|chatbot|bot)\b|\b(quero|preciso|vou|gostaria de|pretendo)\s+(criar|desenvolver|construir|fazer|montar|lancar|entregar|programar|implementar)\b/;
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
  return null;
}

const pad = (value: number) => String(value).padStart(2, "0");
const toIsoDate = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

const isPast = (date: Date, now: Date) =>
  date < new Date(now.getFullYear(), now.getMonth(), now.getDate());

/** Whether this message belongs to the project-planner flow. */
export function isProjectMessage(text: string): boolean {
  const t = normalize(text);
  if (pendingProject && parseDeadline(text)) return true;
  if (SINGLE_ITEM.test(t) || HOURS.test(t)) return false;
  return PROJECT.test(t);
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
  const now = new Date();
  const deadline = parseDeadline(text, now);
  const description = pendingProject && !PROJECT.test(normalize(text)) ? pendingProject : text;

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
  const plan = await projectService.planProject(description, toIsoDate(deadline), signal);
  yield { type: "token", value: summarize(plan) };
  yield { type: "project_plan", plan };
}
