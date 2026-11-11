import { create } from "zustand";
import type { CalendarAction, CalendarEvent, CalendarEventInput } from "@/lib/types";
import { calendarService } from "@/services/calendar-service";
import type { DeleteEventPayload } from "@/services/contracts";
import { ApiError } from "@/services/http";

interface CalendarState {
  /** Client cache of events touched in this session, keyed by id. */
  events: Record<string, CalendarEvent>;
  deletedIds: Record<string, true>;
  /** Applies a mutation performed by the AI during a chat turn. */
  applyAction: (action: CalendarAction) => void;
  /** Manual creation from the Agenda panel. Resolves with the new event's id. */
  createEvent: (input: CalendarEventInput) => Promise<string>;
  updateEvent: (id: string, input: CalendarEventInput) => Promise<void>;
  /** Sends the payload the user confirmed in the delete modal, unchanged. */
  deleteEvent: (payload: DeleteEventPayload) => Promise<void>;
  reset: () => void;
}

const toMessage = (error: unknown, fallback: string) =>
  error instanceof ApiError ? error.message : fallback;

export const useCalendarStore = create<CalendarState>()((set, get) => ({
  events: {},
  deletedIds: {},

  applyAction(action) {
    if (action.type === "deleted") {
      set((state) => ({ deletedIds: { ...state.deletedIds, [action.eventId]: true } }));
      return;
    }
    set((state) => ({ events: { ...state.events, [action.eventId]: action.snapshot } }));
  },

  async createEvent(input) {
    try {
      const created = await calendarService.createEvent(input);
      set((state) => ({ events: { ...state.events, [created.id]: created } }));
      return created.id;
    } catch (error) {
      throw new Error(toMessage(error, "Não foi possível criar o agendamento."));
    }
  },

  async updateEvent(id, input) {
    const previous = get().events[id];
    if (!previous) throw new Error("Agendamento não encontrado.");

    // Optimistic update: show the new values right away, flagged as pending sync.
    set((state) => ({
      events: { ...state.events, [id]: { ...previous, ...input, syncStatus: "pending" } },
    }));

    try {
      const saved = await calendarService.updateEvent(id, input);
      set((state) => ({ events: { ...state.events, [id]: saved } }));
    } catch (error) {
      set((state) => ({ events: { ...state.events, [id]: { ...previous, syncStatus: "error" } } }));
      throw new Error(toMessage(error, "Não foi possível salvar as alterações."));
    }
  },

  async deleteEvent(payload) {
    try {
      await calendarService.deleteEvent(payload);
      set((state) => ({ deletedIds: { ...state.deletedIds, [payload.evento_id]: true } }));
    } catch (error) {
      throw new Error(toMessage(error, "Não foi possível excluir o agendamento."));
    }
  },

  reset: () => set({ events: {}, deletedIds: {} }),
}));
