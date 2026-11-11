import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict, field_validator
import uvicorn

from backend.story_points import StoryPointsPredictor
from destrava.agents.planejador import AgentePlanejador
from destrava.agents.visualizar import AgenteVisualizar
from destrava.rag import obter_rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.story_points_predictor = StoryPointsPredictor()
    app.state.planejador = AgentePlanejador(rag=obter_rag("planejador"))
    app.state.visualizador = AgenteVisualizar()
    yield


app = FastAPI(title="Residence AI Challenge", lifespan=lifespan)


class ProjetoRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    texto: str
    prazo: str

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, texto: str) -> str:
        texto = texto.strip()
        if not texto:
            raise ValueError("O texto do projeto não pode ser vazio.")
        return texto

    @field_validator("prazo")
    @classmethod
    def validar_prazo(cls, prazo: str) -> str:
        prazo = prazo.strip()
        if not prazo:
            raise ValueError("O prazo não pode ser vazio.")
        return prazo


@app.post("/projetos")
def criar_projeto(
    projeto: ProjetoRequest,
    request: Request,
) -> dict[str, object]:
    
    print("Planejando projeto: ", projeto.texto, "com prazo", projeto.prazo, "...")
    planejador: AgentePlanejador = request.app.state.planejador
    plano = planejador.executar(projeto.texto, projeto.prazo)
    resumo = [
        {
            "etapa": tarefa["etapa"],
            "titulo": tarefa["titulo"],
            "story_points": tarefa["story_points"],
        }
        for tarefa in plano["tarefas"]
    ]
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    
    print("Estimando duração das tarefas...")
    predictor: StoryPointsPredictor = request.app.state.story_points_predictor
    for tarefa in plano["tarefas"]:
        tarefa["story_points"] = predictor.prever(tarefa)
        print(f"Estimativa para a tarefa {tarefa['etapa']}: {tarefa['story_points']} story points")
    
    return {"prazo": projeto.prazo, "tarefas": plano["tarefas"]}


@app.get("/tarefas")
def listar_tarefas(
    inicio: str,
    fim: str,
    request: Request,
) -> dict[str, object]:
    """Lista os compromissos da agenda dentro de uma janela de tempo."""
    visualizador: AgenteVisualizar = request.app.state.visualizador
    resposta = visualizador.executar_json(
        {"inicio": inicio, "fim": fim},
        incluir_ocupados=True,
    )

    if resposta["status"] == "erro":
        return resposta

    dados = resposta["dados"]
    if dados is None or "ocupados" not in dados:
        raise RuntimeError("O visualizador não retornou as tarefas ocupadas.")

    return {
        "status": resposta["status"],
        "periodo": resposta["periodo"],
        "tarefas": dados["ocupados"],
    }