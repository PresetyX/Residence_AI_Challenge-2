/**
 * Project planner on the backend (backend/main.py and backend/chat.py).
 *
 *   POST /projetos            -> Planejador (Ollama + RAG) + story points of the neural network.
 *                                The deadline comes from `prazo` or is read from the text itself
 *                                by the Supervisor ("até amanhã", "tenho uma semana", "20/12").
 *   POST /prazos/interpretar  -> reads a deadline from a short answer ("até sexta").
 *   POST /projetos/agendar    -> deadline class + calendar preview (nothing created yet).
 *   POST /projetos/agendar/confirmar -> creates the previewed events.
 */
import type { ModelId, ProjectPlan, ProjectTask } from "@/lib/types";
import type { EventDto } from "./contracts";
import { ApiError, request } from "./http";

export interface ProjectTaskDto {
  etapa: number;
  titulo: string;
  objetivo: string;
  entregaveis: string;
  demonstracao: string;
  dependencia: number;
  story_points: number;
  /** story_points x the user's minutes per story point (calibration, POST /calibracao). */
  tempo_estimado_minutos?: number;
}

export interface ProjectPlanDto {
  /** YYYY-MM-DD, or null when neither `prazo` nor the text had a deadline. */
  prazo: string | null;
  tarefas: ProjectTaskDto[];
  /** The plan is ready but the user still has to say the deadline. */
  precisa_prazo?: boolean;
  /** The planner could not make sense of the project; `mensagem` asks for details. */
  nao_entendi?: boolean;
  mensagem?: string;
}

/** Kind of the ApiError thrown when the planner asks for more details. */
export const NOT_UNDERSTOOD = "NotUnderstood";

export function toProjectTask(dto: ProjectTaskDto): ProjectTask {
  return {
    step: dto.etapa,
    title: dto.titulo,
    goal: dto.objetivo,
    deliverables: dto.entregaveis,
    demo: dto.demonstracao,
    dependsOn: dto.dependencia,
    storyPoints: dto.story_points,
    estimatedMinutes: dto.tempo_estimado_minutos,
  };
}

export function toTaskDto(task: ProjectTask): ProjectTaskDto {
  return {
    etapa: task.step,
    titulo: task.title,
    objetivo: task.goal,
    entregaveis: task.deliverables,
    demonstracao: task.demo,
    dependencia: task.dependsOn,
    story_points: task.storyPoints,
    ...(task.estimatedMinutes ? { tempo_estimado_minutos: task.estimatedMinutes } : {}),
  };
}

export interface PlannedProject {
  plan: ProjectPlan;
  /** True when the backend found no deadline: `plan.deadline` is empty until the user gives one. */
  needsDeadline: boolean;
}

export const projectService = {
  /** `deadline` (YYYY-MM-DD) is optional: without it the backend reads it from the text. */
  async planProject(
    description: string,
    deadline: string | null,
    modelId: ModelId,
    signal?: AbortSignal,
  ): Promise<PlannedProject> {
    const dto = await request<ProjectPlanDto>("/projetos", {
      method: "POST",
      body: JSON.stringify({
        texto: description,
        modelo: modelId,
        ...(deadline ? { prazo: deadline } : {}),
      }),
      signal,
    });

    if (dto?.nao_entendi) {
      throw new ApiError(dto.mensagem ?? "Não entendi. Pode descrever o projeto com mais detalhes?", NOT_UNDERSTOOD);
    }
    if (!Array.isArray(dto?.tarefas) || dto.tarefas.length === 0) {
      throw new ApiError("O planejador não devolveu nenhuma etapa. Tente descrever o projeto com mais detalhes.", "EmptyPlan");
    }
    return {
      plan: {
        description,
        deadline: dto.prazo ?? deadline ?? "",
        tasks: dto.tarefas.map(toProjectTask).sort((a, b) => a.step - b.step),
      },
      needsDeadline: !dto.prazo && !deadline,
    };
  },

  /** Deadline (YYYY-MM-DD) in a short answer, or null. Rejects with the backend message if it already passed. */
  async interpretDeadline(text: string, signal?: AbortSignal): Promise<string | null> {
    const dto = await request<{ prazo: string | null }>("/prazos/interpretar", {
      method: "POST",
      body: JSON.stringify({ texto: text }),
      signal,
    });
    return dto.prazo;
  },
};

export type DeadlineClass = "tranquilo" | "corrido" | "impossivel";

export interface ScheduleSlotDto {
  titulo: string;
  inicio: string;
  fim: string;
  descricao?: string;
}

export interface SchedulePreviewDto {
  status: "confirmacao" | "erro" | "esclarecimento";
  mensagem: string;
  classificacao?: DeadlineClass;
  dados?: { classificacao?: DeadlineClass; eventos?: ScheduleSlotDto[] };
}

export interface ScheduleResultDto {
  status: "sucesso" | "parcial" | "erro" | "cancelado";
  mensagem: string;
  dados?: { eventos_criados?: EventDto[] };
}

export const scheduleService = {
  preview(plan: ProjectPlan, goal: string, signal?: AbortSignal): Promise<SchedulePreviewDto> {
    return request<SchedulePreviewDto>("/projetos/agendar", {
      method: "POST",
      body: JSON.stringify({
        projeto: plan.description,
        prazo: plan.deadline,
        tarefas: plan.tasks.map(toTaskDto),
        meta: goal,
      }),
      signal,
    });
  },
  confirm(confirmed: boolean, signal?: AbortSignal): Promise<ScheduleResultDto> {
    return request<ScheduleResultDto>("/projetos/agendar/confirmar", {
      method: "POST",
      body: JSON.stringify({ confirmado: confirmed }),
      signal,
    });
  },
};
