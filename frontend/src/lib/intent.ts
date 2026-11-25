/**
 * Deterministic reading of short user messages: yes/no answers, project requests and
 * calendar requests. Mirrors destrava/core/intencao.py (keep both in step).
 * No imports on purpose, so it can be exercised directly with Node.
 */

export const normalizeText = (text: string): string =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");

const words = (text: string): string[] => normalizeText(text).match(/[a-z0-9]+/g) ?? [];
const set = (list: string) => new Set(list.split(" "));

const YES_STRONG = set(
  "sim s ok okay pode confirmo confirma confirmado confirmar claro bora manda vai quero isso criar cria crie agendar agende encaixar encaixa encaixe beleza fechado",
);
const YES_ALLOWED = set(
  "sim s ok okay pode podes confirmo confirma confirmado confirmar claro bora manda vai quero isso criar cria crie agendar agende agenda encaixar encaixa encaixe beleza fechado ser mesmo por favor ai la com certeza otimo perfeito o os evento eventos esse esses tudo",
);
const NO_WORDS = set("nao n cancela cancelar cancele cancelado deixa negativo");
const NO_ALLOWED = set(
  "nao n cancela cancelar cancele cancelado deixa negativo pra para la melhor agora nada quero pode podes ok obrigado obrigada por favor isso tudo esse esses o os evento eventos criar cria crie agendar agende agenda encaixar encaixa encaixe vou mesmo entao",
);
const EXPLICIT_YES = set("sim confirmo confirma confirmado");

/**
 * true = clear yes, false = clear no/cancel, null = unclear (ask again, never create).
 * A yes is only accepted when every word of the answer is part of a yes.
 */
export function classifyConfirmation(text: string): boolean | null {
  const list = words(text);
  if (list.length === 0 || text.includes("?")) return null;
  const hasNo = list.some((word) => NO_WORDS.has(word));
  if (hasNo) {
    if (list.every((word) => NO_ALLOWED.has(word))) return false;
    const startsWithNo = /^(nao|cancel)/.test(list[0]);
    return startsWithNo && !list.some((word) => EXPLICIT_YES.has(word)) ? false : null;
  }
  const allYes = list.every((word) => YES_ALLOWED.has(word));
  return allYes && list.some((word) => YES_STRONG.has(word)) ? true : null;
}

/** A short message that tries to answer a yes/no question, even if unclearly. */
export function looksLikeReply(text: string): boolean {
  const list = words(text);
  return list.length <= 6 && list.some((word) => YES_STRONG.has(word) || NO_WORDS.has(word));
}

const TIME_RANGE = /\b(?:das|de)\s+\d{1,2}(?:h|:)?\d{0,2}\s*(?:as|a|ate)\s+\d{1,2}/;
const PROJECT_REQUEST =
  /^\W*(?:(?:oi|ola|bom dia|boa tarde|boa noite)\W+)?(?:(?:eu\s+)?(?:quero|queria|preciso|vou|gostaria|pretendo|planejo|me ajude|me ajuda|ajude-me)\s+(?:(?:de|a)\s+)?)?(?:(?:criar|crie|cria|desenvolver|desenvolva|construir|fazer|montar|programar|implementar|lancar|entregar|planejar|planeje|dividir|organizar|agendar)\s+)?(?:(?:um|uma|o|a|meu|minha|novo|nova|este|esse|pequeno|simples)\s+){0,3}(?:projeto|app|aplicativo|sistema|site|plataforma|api|software|jogo|game|dashboard|chatbot|bot|mvp|tcc|monografia|programa(?!\s+(?:um|uma|o|a)\b)|startup)\b/;

/** "Quero criar um app de agenda para barbearia": a project, even if it mentions the calendar. */
export function isProjectRequest(text: string): boolean {
  const t = normalizeText(text);
  // "O projeto atrasou, quais meus horários livres?" is a calendar question.
  const calendarQuestion = t.trimEnd().endsWith("?") && CALENDAR_QUERY.test(t);
  return PROJECT_REQUEST.test(t) && !TIME_RANGE.test(t) && !calendarQuestion;
}

const CREATE_FIRST =
  /^\W*(?:(?:por favor|pf)\W+)?(?:crie|criar|cria|agende|agendar|marque|marcar|marca|coloque|adicione)\b/;
const CALENDAR_QUERY =
  /\b(?:horarios? livres?|tempo livre|tenho tempo|tenho (?:algum )?horario|quais .{0,30}horarios?|(?:ver|veja|mostre|mostrar|mostra|consultar|consulte) .{0,30}(?:agenda|horarios?|livres?)|estou livre|tenho livre|de livre|minha agenda|disponibilidade)\b/;

/** A message clearly meant for the calendar: a free-time question or a single event. */
export function isCalendarRequest(text: string): boolean {
  const t = normalizeText(text);
  return CALENDAR_QUERY.test(t) || (CREATE_FIRST.test(t) && TIME_RANGE.test(t));
}
