/**
 * First-run questions in the chat, before any request goes to the agents:
 *
 *   1. Sleep: when the user goes to sleep and wakes up. Saved on the account (PUT /perfil/sono);
 *      the backend never schedules anything in that window.
 *   2. Story-point calibration: how long the user would take for each sample task of
 *      GET /calibracao (known story points). The backend turns the answers into the user's
 *      minutes per story point, used for every estimate from then on.
 *
 * Answers are free text ("11 da noite", "1h30", "pular") read by the backend
 * (POST /perfil/interpretar). "configurar sono" and "calibrar" restart a step later on.
 */
import { ApiError } from "./http";
import type { InferenceChunk } from "./inference-service";
import { type CalibrationQuestionDto, type ProfileDto, profileService } from "./profile-service";

type Step =
  | { kind: "sleep" }
  | { kind: "wake"; sleep: string }
  | { kind: "calibration"; questions: CalibrationQuestionDto[]; answers: (number | null)[] };

let account: { email: string; name: string } | null = null;
let email: string | null = null;
let step: Step | null = null;
/** Calibration still missing after the sleep step. */
let needsCalibration = false;

const normalize = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim();

const SKIP = /^(pular|pula|pulo|proxima|nao sei|sei la|nao faco ideia|passo|skip)\b/;
const STOP = /^(parar|para|chega|depois|mais tarde|cancelar|cancela|sair)\b/;
const SLEEP_COMMAND = /\b(configurar|mudar|alterar|trocar|ajustar|redefinir)\b.*\b(sono|dormir|acordar)\b|\bhorarios? de sono\b/;
const CALIBRATE_COMMAND = /^(calibrar|recalibrar|refazer (a )?calibracao|calibrar story points?)\b/;

const ASK_SLEEP =
  "**Que horas você costuma dormir?** (ex.: 23h, meia-noite, 1 da manhã)";
const ASK_WAKE = "**E que horas você costuma acordar?** (ex.: 7h, 6:30, 8 da manhã)";

function sleepHours(sleep: string, wake: string): string {
  const toMinutes = (hhmm: string) => {
    const [h, m] = hhmm.split(":").map(Number);
    return h * 60 + m;
  };
  const minutes = (toMinutes(wake) - toMinutes(sleep) + 24 * 60) % (24 * 60);
  return (Math.round((minutes / 60) * 10) / 10).toLocaleString("pt-BR");
}

function question(questions: CalibrationQuestionDto[], index: number): string {
  const q = questions[index];
  return [
    `**Pergunta ${index + 1}/${questions.length}: ${q.titulo}**`,
    q.objetivo,
    `- Entregáveis: ${q.entregaveis}`,
    `- Como demonstrar: ${q.demonstracao}`,
    "",
    "Quanto tempo você levaria para fazer isso? (ex.: 2h, 90 min, 1 dia, ou **pular**)",
  ].join("\n");
}

async function startCalibration(signal?: AbortSignal): Promise<string> {
  const questions = await profileService.calibrationQuestions(signal);
  step = { kind: "calibration", questions, answers: [] };
  return [
    `Agora, ${questions.length} perguntas rápidas para eu calibrar quanto tempo **você** leva por story point. ` +
      "Para cada tarefa, diga quanto tempo levaria trabalhando nela sozinho. " +
      "Se não souber, responda **pular**; para continuar depois, **parar**.",
    "",
    question(questions, 0),
  ].join("\n");
}

/** Called when the chat opens: the greeting with the first question, or null when the profile is complete. */
export async function startOnboarding(
  user: { email: string; name: string },
  signal?: AbortSignal,
): Promise<string | null> {
  email = user.email;
  account = user;
  const profile: ProfileDto = await profileService.get(user.email, signal);
  needsCalibration = !profile.calibracao;
  const firstName = user.name.split(" ")[0];

  if (!profile.sono) {
    step = { kind: "sleep" };
    return [
      `Oi, ${firstName}! Antes de começarmos, preciso conhecer sua rotina para nunca marcar nada enquanto você dorme.`,
      "",
      ASK_SLEEP,
    ].join("\n");
  }
  if (needsCalibration) {
    return `Oi, ${firstName}! ${await startCalibration(signal)}`;
  }
  step = null;
  return null;
}

/** The account whose questions are half-answered (the greeting must be shown again), or null. */
export function pendingOnboarding(): { email: string; name: string } | null {
  return step ? account : null;
}

export function resetOnboarding(): void {
  step = null;
  email = null;
  account = null;
  needsCalibration = false;
}

/** True when this message answers an onboarding question (or asks to redo one). */
export function routeToOnboarding(text: string): boolean {
  if (!email) return false;
  const t = normalize(text);
  return step !== null || SLEEP_COMMAND.test(t) || CALIBRATE_COMMAND.test(t);
}

function* say(text: string): Generator<InferenceChunk> {
  yield { type: "token", value: text };
}

async function* answerSleep(text: string, signal?: AbortSignal): AsyncGenerator<InferenceChunk> {
  const sleep = await profileService.interpret(text, "dormir", signal);
  if (typeof sleep !== "string") {
    yield* say(`Não consegui entender esse horário. ${ASK_SLEEP}`);
    return;
  }
  step = { kind: "wake", sleep };
  yield* say(`Anotado: você dorme às **${sleep}**. ${ASK_WAKE}`);
}

async function* answerWake(sleep: string, text: string, signal?: AbortSignal): AsyncGenerator<InferenceChunk> {
  const wake = await profileService.interpret(text, "acordar", signal);
  if (typeof wake !== "string") {
    yield* say(`Não consegui entender esse horário. ${ASK_WAKE}`);
    return;
  }
  try {
    await profileService.saveSleep(email!, { dormir: sleep, acordar: wake }, signal);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 422) throw error;
    step = { kind: "sleep" };
    yield* say(`${error.message}\n\n${ASK_SLEEP}`);
    return;
  }
  const saved =
    `Pronto, salvei na sua conta: você dorme das **${sleep}** às **${wake}** (${sleepHours(sleep, wake)} h). ` +
    "Não vou marcar nada nesse período.";
  if (!needsCalibration) {
    step = null;
    yield* say(`${saved} Para mudar depois, é só escrever **configurar sono**.`);
    return;
  }
  yield* say(`${saved}\n\n${await startCalibration(signal)}`);
}

async function* answerCalibration(
  current: Extract<Step, { kind: "calibration" }>,
  text: string,
  signal?: AbortSignal,
): AsyncGenerator<InferenceChunk> {
  const t = normalize(text);
  if (STOP.test(t)) {
    step = null;
    yield* say(
      "Tudo bem! Até você calibrar, cada story point vale **60 min**. Quando quiser, escreva **calibrar**. " +
        "Já pode me pedir um projeto ou perguntar pela sua agenda.",
    );
    return;
  }

  let minutes: number | null = null;
  if (!SKIP.test(t)) {
    const value = await profileService.interpret(text, "duracao", signal);
    if (typeof value !== "number") {
      yield* say(
        "Não entendi esse tempo. Responda algo como **2h**, **45 min**, **1 dia** ou **pular**.\n\n" +
          question(current.questions, current.answers.length),
      );
      return;
    }
    minutes = value;
  }
  current.answers.push(minutes);

  if (current.answers.length < current.questions.length) {
    yield* say(question(current.questions, current.answers.length));
    return;
  }

  step = null;
  try {
    await profileService.saveCalibration(current.answers, signal);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 422) throw error;
    yield* say(`${error.message} Escreva **calibrar** para tentar de novo; até lá, cada story point vale 60 min.`);
    return;
  }
  needsCalibration = false;
  const profile = await profileService.get(email!, signal);
  yield* say(
    `Calibrado! Para você, cada story point vale cerca de **${profile.minutos_por_story_point} min** de trabalho. ` +
      "Vou usar isso para estimar e encaixar suas tarefas na agenda. Já pode me pedir seu primeiro projeto!",
  );
}

export async function* onboardingStream(text: string, signal?: AbortSignal): AsyncGenerator<InferenceChunk> {
  const t = normalize(text);
  if (SLEEP_COMMAND.test(t)) {
    step = { kind: "sleep" };
    yield* say(ASK_SLEEP);
    return;
  }
  if (CALIBRATE_COMMAND.test(t)) {
    yield* say(await startCalibration(signal));
    return;
  }
  if (!step) return;
  if (step.kind === "sleep") yield* answerSleep(text, signal);
  else if (step.kind === "wake") yield* answerWake(step.sleep, text, signal);
  else yield* answerCalibration(step, text, signal);
}
