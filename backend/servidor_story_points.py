"""Serviço de story points do servidor de IA (o PC com a GPU).

Expõe o ``StoryPointsPredictor`` (BGE-M3 + modelos/rede_neural.pt) por HTTP para
que os notebooks do time não precisem de torch nem de sentence-transformers.
O modelo é carregado uma vez, na inicialização, e reaproveitado em todas as
chamadas.

Rodar no servidor (na raiz do projeto, com requirements-ia.txt instalado):

    uvicorn backend.servidor_story_points:app --host 0.0.0.0 --port 8001

Rotas:
    GET  /saude         -> {"status": "ok", "dispositivo": "cuda:0"}
    POST /story-points  {"tarefas": [{titulo, objetivo, entregaveis, demonstracao}, ...]}
                        -> {"story_points": [5, 8, ...]}  (mesma ordem das tarefas)

Segurança: o serviço não tem usuários. O acesso deve ficar restrito à rede da
Tailscale (sem port forward no roteador; ver README). Com a variável de
ambiente CHAVE_API_IA definida, toda rota exceto /saude exige o cabeçalho
X-API-Key com o mesmo valor.
"""

import hmac
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.story_points import CABECALHO_CHAVE, StoryPointsPredictor
from destrava.core import config

# Limite de tarefas por pedido: o Planejador gera poucas etapas; um lote enorme
# seria erro de quem chama e ocuparia a GPU à toa.
MAX_TAREFAS = 50
# Rotas liberadas sem chave (para conferir se o serviço está no ar).
ROTAS_ABERTAS = {"/saude"}

# Quem cria o estimador. Os testes trocam por um falso, sem carregar o modelo.
criar_predictor: Callable[[], StoryPointsPredictor] = StoryPointsPredictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Carrega o BGE-M3 e a rede neural uma vez só (leva alguns segundos e ocupa
    # memória da GPU). As requisições reaproveitam este objeto.
    app.state.predictor = criar_predictor()
    yield


app = FastAPI(title="Destrava · Story points", lifespan=lifespan)


@app.middleware("http")
async def exigir_chave(request: Request, call_next):
    chave = config.CHAVE_API_IA
    if chave and request.url.path not in ROTAS_ABERTAS:
        enviada = request.headers.get(CABECALHO_CHAVE, "")
        # compare_digest: comparação em tempo constante (não vaza a chave por tempo).
        if not hmac.compare_digest(enviada.encode(), chave.encode()):
            return JSONResponse(status_code=401, content={"detail": "Chave de API inválida ou ausente."})
    return await call_next(request)


class TarefaRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    titulo: str
    objetivo: str
    entregaveis: str
    demonstracao: str


class StoryPointsRequest(BaseModel):
    tarefas: list[TarefaRequest] = Field(min_length=1, max_length=MAX_TAREFAS)

    @field_validator("tarefas")
    @classmethod
    def validar_textos(cls, tarefas: list[TarefaRequest]) -> list[TarefaRequest]:
        for indice, tarefa in enumerate(tarefas, start=1):
            if not any(valor.strip() for valor in tarefa.model_dump().values()):
                raise ValueError(f"A tarefa {indice} está sem texto.")
        return tarefas


@app.get("/saude")
def saude(request: Request) -> dict[str, str]:
    predictor = request.app.state.predictor
    return {"status": "ok", "dispositivo": getattr(predictor, "dispositivo", "desconhecido")}


# Rota síncrona (def, não async def): o FastAPI a roda numa thread, e a
# inferência não trava o laço de eventos enquanto a GPU trabalha.
@app.post("/story-points")
def story_points(pedido: StoryPointsRequest, request: Request) -> dict[str, list[int]]:
    predictor = request.app.state.predictor
    tarefas = [tarefa.model_dump() for tarefa in pedido.tarefas]
    return {"story_points": predictor.prever_lote(tarefas)}
