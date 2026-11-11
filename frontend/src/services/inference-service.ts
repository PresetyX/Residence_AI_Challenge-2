import type { CalendarAction, CalendarActionType, MessageRole, ModelId } from "@/lib/types";
import { type EventDto, toCalendarEvent } from "./contracts";
import { API_BASE_URL, ApiError, USE_MOCKS } from "./http";
import { mockStreamChat } from "./mocks/mock-supervisor";

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
  | { type: "suggest_manual_panel" };

export interface InferenceService {
  /** Streams the assistant reply. Calendar mutations arrive as `calendar_action` chunks. */
  streamChat(request: InferenceRequest, signal?: AbortSignal): AsyncGenerator<InferenceChunk>;
}

/** One NDJSON line emitted by the backend's POST /chat/stream. */
type StreamLineDto =
  | { tipo: "token"; valor: string }
  | { tipo: "acao_agenda"; acao: CalendarActionType; evento: EventDto }
  | { tipo: "sugerir_painel_manual" };

function toChunk(line: StreamLineDto): InferenceChunk {
  if (line.tipo === "token") return { type: "token", value: line.valor };
  if (line.tipo === "sugerir_painel_manual") return { type: "suggest_manual_panel" };
  const snapshot = toCalendarEvent(line.evento);
  return {
    type: "calendar_action",
    action: { type: line.acao, eventId: snapshot.id, snapshot },
  };
}

/**
 * Expected backend contract: POST /chat/stream { modelo, sistema, mensagens } answering with
 * newline-delimited JSON, one StreamLineDto per line.
 */
const httpInferenceService: InferenceService = {
  async *streamChat({ modelId, systemPrompt, messages }, signal) {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        modelo: modelId,
        sistema: systemPrompt,
        mensagens: messages.map((message) => ({
          papel: message.role === "user" ? "usuario" : "assistente",
          conteudo: message.content,
        })),
      }),
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
        if (line.trim()) yield toChunk(JSON.parse(line) as StreamLineDto);
      }
    }
    if (buffer.trim()) yield toChunk(JSON.parse(buffer) as StreamLineDto);
  },
};

export const inferenceService: InferenceService = USE_MOCKS
  ? { streamChat: mockStreamChat }
  : httpInferenceService;
