/**
 * Project planner: POST /projetos on the backend (backend/main.py).
 *
 * The backend runs the Planejador agent (Ollama + RAG) to split the project into steps,
 * then replaces each step's story points with the estimate from the neural network.
 * Both stages are slow, so callers should show progress and allow cancelling.
 */
import type { ProjectPlan, ProjectTask } from "@/lib/types";
import { ApiError, USE_PLANNER_API, delay, isAbortError, request, API_BASE_URL } from "./http";

export interface ProjectRequestDto {
  texto: string;
  /** YYYY-MM-DD */
  prazo: string;
}

export interface ProjectTaskDto {
  etapa: number;
  titulo: string;
  objetivo: string;
  entregaveis: string;
  demonstracao: string;
  dependencia: number;
  story_points: number;
}

export interface ProjectPlanDto {
  prazo: string;
  tarefas: ProjectTaskDto[];
}

export function toProjectTask(dto: ProjectTaskDto): ProjectTask {
  return {
    step: dto.etapa,
    title: dto.titulo,
    goal: dto.objetivo,
    deliverables: dto.entregaveis,
    demo: dto.demonstracao,
    dependsOn: dto.dependencia,
    storyPoints: dto.story_points,
  };
}

export interface ProjectService {
  planProject(description: string, deadline: string, signal?: AbortSignal): Promise<ProjectPlan>;
}

const httpProjectService: ProjectService = {
  async planProject(description, deadline, signal) {
    let dto: ProjectPlanDto;
    try {
      dto = await request<ProjectPlanDto>("/projetos", {
        method: "POST",
        body: JSON.stringify({ texto: description, prazo: deadline } satisfies ProjectRequestDto),
        signal,
      });
    } catch (error) {
      if (isAbortError(error) || error instanceof ApiError) throw error;
      // fetch() rejects with a TypeError when the server is down or CORS blocks the call.
      throw new ApiError(
        `Não consegui falar com o planejador em ${API_BASE_URL}. Verifique se o backend está rodando (uvicorn backend.main:app).`,
        "NetworkError",
      );
    }

    if (!Array.isArray(dto?.tarefas) || dto.tarefas.length === 0) {
      throw new ApiError("O planejador não devolveu nenhuma etapa. Tente descrever o projeto com mais detalhes.", "EmptyPlan");
    }
    return {
      description,
      deadline: dto.prazo ?? deadline,
      tasks: dto.tarefas.map(toProjectTask).sort((a, b) => a.step - b.step),
    };
  },
};

/** Offline stand-in with the same shape as the backend response. */
const mockProjectService: ProjectService = {
  async planProject(description, deadline, signal) {
    await delay(1800, signal);
    const steps: Array<[string, string, string, string, number]> = [
      ["Planejamento", "Definir escopo, requisitos e funcionalidades do projeto.", "Documento de escopo e cronograma.", "Resumo do projeto com as funcionalidades principais.", 5],
      ["Modelagem", "Definir a estrutura de dados e a arquitetura.", "Modelo de dados e diagrama da arquitetura.", "Esboço do modelo de dados e dos componentes.", 4],
      ["Implementação", "Construir as funcionalidades principais.", "Código-fonte das funcionalidades e documentação.", "Fluxo principal funcionando de ponta a ponta.", 8],
      ["Testes", "Testar o projeto em diferentes cenários.", "Relatório de testes e correções.", "Execução dos testes com os resultados.", 5],
      ["Entrega", "Publicar e apresentar o projeto.", "Versão final publicada e apresentação.", "Demonstração do projeto completo.", 3],
    ];
    return {
      description,
      deadline,
      tasks: steps.map(([title, goal, deliverables, demo, storyPoints], index) => ({
        step: index + 1,
        title,
        goal,
        deliverables,
        demo,
        dependsOn: index,
        storyPoints,
      })),
    };
  },
};

export const projectService: ProjectService = USE_PLANNER_API ? httpProjectService : mockProjectService;
