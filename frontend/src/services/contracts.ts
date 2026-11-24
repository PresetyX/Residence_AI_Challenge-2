/**
 * Wire types mirroring the backend JSON contract (docs/contrato.md, `RespostaAgente`
 * in destrava/core/models.py). Field names stay in Portuguese because that is what
 * the agents send; the mappers below translate to the frontend domain types.
 *
 * `descricao` and `local` are not in the backend contract yet. They are optional
 * here so the UI works today and picks them up as soon as the agents return them.
 */
import type { CalendarEvent, CalendarEventInput } from "@/lib/types";
import { ApiError } from "./http";

export type AgentStepStatus = "ok" | "erro" | "pendente";

export interface AgentStepDto {
  etapa: string;
  status: AgentStepStatus;
  detalhe: unknown;
}

export interface EventDto {
  id: string;
  titulo: string;
  inicio: string;
  fim: string;
  link?: string | null;
  descricao?: string | null;
  local?: string | null;
  /** Goal of the AI plan this slot belongs to, if any. */
  meta?: string | null;
}

export interface AgentResponseDto<TData> {
  status: "sucesso" | "erro";
  acao: string;
  periodo: { inicio: string; fim: string; duracao_minutos: number } | null;
  dados: TData | null;
  fluxo: { inicio: AgentStepDto; meio: AgentStepDto; fim: AgentStepDto };
  erro: { tipo: string; mensagem: string } | null;
}

export interface EventWriteDto {
  titulo: string;
  inicio: string;
  fim: string;
  descricao?: string;
  local?: string;
}

/** Who asked for the deletion: the user in the panel, or the AI clearing a plan. */
export type DeleteOrigin = "painel_manual" | "plano_ia";

/** Payload sent to delete an event (shown to the user before a manual deletion). */
export interface DeleteEventPayload {
  acao: "excluir_evento";
  evento_id: string;
  titulo: string;
  origem: DeleteOrigin;
  confirmado: true;
  solicitado_em: string;
}

export function toCalendarEvent(dto: EventDto): CalendarEvent {
  return {
    id: dto.id,
    title: dto.titulo,
    description: dto.descricao ?? "",
    start: dto.inicio,
    end: dto.fim,
    location: dto.local ?? "",
    link: dto.link ?? undefined,
    syncStatus: "synced",
    updatedAt: new Date().toISOString(),
    planGoal: dto.meta ?? undefined,
  };
}

export function toEventWriteDto(input: CalendarEventInput): EventWriteDto {
  return {
    titulo: input.title,
    inicio: input.start,
    fim: input.end,
    descricao: input.description,
    local: input.location,
  };
}

/** Agents never raise: failures come back as `status: "erro"`. Convert them to ApiError. */
export function unwrapAgentResponse<TData>(response: AgentResponseDto<TData>): TData {
  if (response.status === "erro" || response.dados === null) {
    throw new ApiError(
      response.erro?.mensagem ?? "O agente não conseguiu concluir a ação.",
      response.erro?.tipo ?? "AgentError",
    );
  }
  return response.dados;
}
