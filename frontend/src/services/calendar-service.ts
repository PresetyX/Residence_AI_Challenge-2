import type { CalendarEvent, CalendarEventInput } from "@/lib/types";
import {
  type AgentResponseDto,
  type DeleteEventPayload,
  type DeleteOrigin,
  type EventDto,
  toCalendarEvent,
  toEventWriteDto,
  unwrapAgentResponse,
} from "./contracts";
import { ApiError, request } from "./http";

export interface CalendarService {
  listEvents(): Promise<CalendarEvent[]>;
  getEvent(id: string): Promise<CalendarEvent>;
  /** `planGoal` is set only by the AI planner; manual events leave it out. */
  createEvent(input: CalendarEventInput, planGoal?: string): Promise<CalendarEvent>;
  updateEvent(id: string, input: CalendarEventInput): Promise<CalendarEvent>;
  deleteEvent(payload: DeleteEventPayload): Promise<void>;
}

/** Builds the exact payload the delete confirmation modal shows and then sends. */
export function buildDeletePayload(
  event: CalendarEvent,
  origin: DeleteOrigin = "painel_manual",
): DeleteEventPayload {
  return {
    acao: "excluir_evento",
    evento_id: event.id,
    titulo: event.title,
    origem: origin,
    confirmado: true,
    solicitado_em: new Date().toISOString(),
  };
}

export function validateEventInput(input: CalendarEventInput): void {
  if (!input.title.trim()) {
    throw new ApiError("O título do evento é obrigatório.", "ValidationError");
  }
  if (Date.parse(input.start) >= Date.parse(input.end)) {
    throw new ApiError("O início deve ser anterior ao término.", "ValidationError");
  }
}

// ---------------------------------------------------------------------------
// HTTP implementation. Responses follow the agents' `RespostaAgente` envelope.
//   GET    /calendar/events          -> { eventos: EventDto[] }
//   GET    /calendar/events/:id      -> { evento: EventDto }
//   POST   /calendar/events          -> { evento: EventDto }   (acao: evento_criado)
//   PUT    /calendar/events/:id      -> { evento: EventDto }   (acao: evento_editado)
//   DELETE /calendar/events/:id      -> { evento_id: string }  (acao: evento_excluido)
// ---------------------------------------------------------------------------

type EventResponse = AgentResponseDto<{ evento: EventDto }>;

const httpCalendarService: CalendarService = {
  async listEvents() {
    const response = await request<AgentResponseDto<{ eventos: EventDto[] }>>("/calendar/events");
    return unwrapAgentResponse(response).eventos.map(toCalendarEvent);
  },
  async getEvent(id) {
    const response = await request<EventResponse>(`/calendar/events/${encodeURIComponent(id)}`);
    return toCalendarEvent(unwrapAgentResponse(response).evento);
  },
  async createEvent(input, planGoal) {
    validateEventInput(input);
    const response = await request<EventResponse>("/calendar/events", {
      method: "POST",
      body: JSON.stringify({ ...toEventWriteDto(input), meta: planGoal }),
    });
    return toCalendarEvent(unwrapAgentResponse(response).evento);
  },
  async updateEvent(id, input) {
    validateEventInput(input);
    const response = await request<EventResponse>(`/calendar/events/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(toEventWriteDto(input)),
    });
    return toCalendarEvent(unwrapAgentResponse(response).evento);
  },
  async deleteEvent(payload) {
    const response = await request<AgentResponseDto<{ evento_id: string }>>(
      `/calendar/events/${encodeURIComponent(payload.evento_id)}`,
      { method: "DELETE", body: JSON.stringify(payload) },
    );
    unwrapAgentResponse(response);
  },
};

export const calendarService: CalendarService = httpCalendarService;
