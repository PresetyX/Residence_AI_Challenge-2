export type ModelId = "gemma-2b" | "gemma-4-26b-a4b-q4_0" | "gemma-4-12b-sfp8";

export type ModelRuntime = "local" | "cloud";

export interface ModelOption {
  id: ModelId;
  /** Full name shown in the dropdown list. */
  name: string;
  /** Compact name shown on the collapsed trigger. */
  shortName: string;
  description: string;
  runtime: ModelRuntime;
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

/** What the user accepted in the pre-auth modal; sent along with the OAuth request. */
export interface ConsentRecord {
  termsAccepted: boolean;
  calendarAccessAccepted: boolean;
  termsVersion: string;
  acceptedAt: string;
}

export type SyncStatus = "synced" | "pending" | "error";

export interface CalendarEvent {
  id: string;
  title: string;
  description: string;
  /** ISO 8601 with offset. */
  start: string;
  /** ISO 8601 with offset. */
  end: string;
  location: string;
  /** Link to the event on Google Calendar, when the backend provides one. */
  link?: string;
  syncStatus: SyncStatus;
  updatedAt: string;
  /** Goal this slot belongs to when it was scheduled by an AI plan; absent for manual events. */
  planGoal?: string;
}

export type CalendarEventInput = Pick<
  CalendarEvent,
  "title" | "description" | "start" | "end" | "location"
>;

export type CalendarActionType = "created" | "updated" | "deleted";

/** A calendar mutation performed by the AI, rendered as an inline card in the thread. */
export interface CalendarAction {
  type: CalendarActionType;
  eventId: string;
  /** Event state at the time of the action; fallback when the live event is gone. */
  snapshot: CalendarEvent;
}

export type MessageRole = "user" | "assistant";
export type MessageStatus = "streaming" | "done" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  status: MessageStatus;
  modelId?: ModelId;
  /** Calendar mutations performed by the AI in this turn (a plan touches many slots). */
  calendarActions?: CalendarAction[];
  /** True when the AI declined a direct command and points the user to the manual panel. */
  suggestsManualPanel?: boolean;
}
