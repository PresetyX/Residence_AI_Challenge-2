import type {
  CalendarAction,
  CalendarActionType,
  MessageRole,
  ModelId,
  ProjectPlan,
} from "@/lib/types";
import { type EventDto, toCalendarEvent } from "./contracts";
import { API_BASE_URL, ApiError } from "./http";
import { onboardingStream, routeToOnboarding } from "./onboarding";
import {
  answerProjectPlanner,
  awaitingProjectAnswer,
  expectProjectDescription,
  projectPlannerStream,
  routeToProjectPlanner,
} from "./project-planner";

export interface InferenceMessage {
  role: MessageRole;
  content: string;
}

export interface InferenceRequest {
  modelId: ModelId;
  /** Calendar rules the model must follow (see lib/assistant-rules.ts). */
  systemPrompt: string;
  messages: InferenceMessage[];
}

export type InferenceChunk =
  | { type: "token"; value: string }
  /** One calendar mutation; a plan emits one chunk per slot it touched. */
  | { type: "calendar_action"; action: CalendarAction }
  /** The AI declined a direct command; the UI offers the manual panel instead. */
  | { type: "suggest_manual_panel" }
  /** Progress note for slow backend work, shown until the first token arrives. */
  | { type: "status"; value: string }
  /** Project plan from POST /projetos. */
  | { type: "project_plan"; plan: ProjectPlan }
  /** The reply asks a yes/no question: show the Sim and Não buttons. */
  | { type: "confirmation_request" }
  /** The request was settled (scheduled, cancelled, impossible): the chat starts over next time. */
  | { type: "conversation_end" };

export interface InferenceService {
  /** Streams the assistant reply. Calendar mutations arrive as `calendar_action` chunks. */
  streamChat(request: InferenceRequest, signal?: AbortSignal): AsyncGenerator<InferenceChunk>;
  /** A click on Sim or Não for the pending question. */
  confirm(confirmed: boolean, signal?: AbortSignal): AsyncGenerator<InferenceChunk>;
}

/** One NDJSON line emitted by the backend's POST /chat/stream. */
type StreamLineDto =
  | { tipo: "token"; valor: string }
  | { tipo: "status"; valor: string }
  | { tipo: "acao_agenda"; acao: CalendarActionType; evento: EventDto }
  | { tipo: "sugerir_painel_manual" }
  | { tipo: "pedir_projeto" }
  | { tipo: "pedir_confirmacao" }
  | { tipo: "fim_conversa" };

function toChunk(line: Exclude<StreamLineDto, { tipo: "pedir_projeto" }>): InferenceChunk {
  if (line.tipo === "fim_conversa") return { type: "conversation_end" };
  if (line.tipo === "pedir_confirmacao") return { type: "confirmation_request" };
  if (line.tipo === "token") return { type: "token", value: line.valor };
  if (line.tipo === "status") return { type: "status", value: line.valor };
  if (line.tipo === "sugerir_painel_manual") return { type: "suggest_manual_panel" };
  const snapshot = toCalendarEvent(line.evento);
  return {
    type: "calendar_action",
    action: { type: line.acao, eventId: snapshot.id, snapshot },
  };
}

/** "pedir_projeto" is routing state, not a chunk: the next message goes to the planner. */
function* handleLine(raw: string): Generator<InferenceChunk> {
  const line = JSON.parse(raw) as StreamLineDto;
  if (line.tipo === "pedir_projeto") {
    expectProjectDescription();
    return;
  }
  yield toChunk(line);
}

/** POSTs `body` and yields the newline-delimited JSON answer, one StreamLineDto per line. */
async function* streamLines(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<InferenceChunk> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new ApiError("O modelo não respondeu. Tente novamente.", "HttpError", response.status);
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.trim()) yield* handleLine(line);
    }
  }
  if (buffer.trim()) yield* handleLine(buffer);
}

/**
 * Expected backend contract: POST /chat/stream { modelo, sistema, mensagens } and
 * POST /chat/confirmar { confirmado }, both answering with NDJSON.
 */
const supervisor: InferenceService = {
  streamChat: ({ modelId, systemPrompt, messages }, signal) =>
    streamLines(
      "/chat/stream",
      {
        modelo: modelId,
        sistema: systemPrompt,
        mensagens: messages.map((message) => ({
          papel: message.role === "user" ? "usuario" : "assistente",
          conteudo: message.content,
        })),
      },
      signal,
    ),
  confirm: (confirmed, signal) => streamLines("/chat/confirmar", { confirmado: confirmed }, signal),
};

/** Onboarding answers first, then project requests to the backend planner; everything else to the Supervisor. */
export const inferenceService: InferenceService = {
  async *streamChat(request, signal) {
    const last = [...request.messages].reverse().find((message) => message.role === "user");
    // First-run questions (sleep, story-point calibration) come before any agent.
    if (last && routeToOnboarding(last.content)) {
      yield* onboardingStream(last.content, signal);
      return;
    }
    if (last && routeToProjectPlanner(last.content)) {
      yield* projectPlannerStream(last.content, request.modelId, signal);
      return;
    }
    yield* supervisor.streamChat(request, signal);
  },
  async *confirm(confirmed, signal) {
    // The question may come from the planner (kept here) or from the Supervisor (backend).
    if (awaitingProjectAnswer()) {
      yield* answerProjectPlanner(confirmed, signal);
      return;
    }
    yield* supervisor.confirm(confirmed, signal);
  },
};
