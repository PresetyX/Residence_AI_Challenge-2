from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from destrava.agents.visualizar import VisualizationAgent
from destrava.core.llm import explain_visualization
from destrava.core.models import Visualization

load_dotenv()

app = FastAPI(title="Destrava - Agente de Visualização")
agent = VisualizationAgent()


class VisualizationRequest(BaseModel):
    start: datetime
    end: datetime
    user_message: str = "Mostre minha rotina neste período."


@app.post("/visualize")
def visualize(request: VisualizationRequest):
    try:
        visualization = Visualization(**agent.run(request.start, request.end))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar visualização: {error}",
        )

    explanation = explain_visualization(
        user_message=request.user_message,
        visualization=visualization,
    )

    return {
        "visualization": visualization.model_dump(mode="json"),
        "explanation": explanation,
    }
