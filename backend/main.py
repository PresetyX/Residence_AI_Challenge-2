import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, field_validator
import uvicorn

from backend.story_points import ErroStoryPoints, EstimadorStoryPoints, criar_estimador
from destrava.agents.planejador import AgentePlanejador, ErroPlanejador
from destrava.core import config
from destrava.rag import obter_rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Com STORY_POINTS_URL definido, o estimador é só um cliente HTTP do
    # servidor de IA: nada de torch nem de BGE-M3 nesta máquina. Sem ele, o
    # modelo é carregado aqui (modo local, requirements-ia.txt).
    app.state.story_points_predictor = criar_estimador()
    modo = f"remoto ({config.STORY_POINTS_URL})" if config.STORY_POINTS_URL else "local"
    print(f"Story points: modo {modo}. LLM: {config.MODELO} em {config.OLLAMA_URL}.")
    app.state.planejador = AgentePlanejador(rag=obter_rag("planejador"))
    yield


app = FastAPI(title="Residence AI Challenge", lifespan=lifespan)

# Origens do frontend (Next.js) liberadas para chamar a API pelo navegador.
# Sobrescreva com CORS_ORIGINS="http://exemplo.com,http://outro.com".
CORS_ORIGINS = [
    origem.strip()
    for origem in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3210",
    ).split(",")
    if origem.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def raiz() -> dict[str, object]:
    return {}


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
    try:
        plano = planejador.executar(projeto.texto, projeto.prazo)
    except ErroPlanejador as erro:
        # A IA respondeu, mas fora do contrato esperado.
        raise HTTPException(status_code=502, detail=str(erro)) from erro
    except ValueError as erro:
        # Entrada inválida (ex.: prazo fora do formato AAAA-MM-DD).
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    except Exception as erro:
        # Ollama fora do ar, modelo não baixado etc.
        raise HTTPException(
            status_code=503,
            detail=f"O planejador não está disponível: {erro}",
        ) from erro

    # plano = json.loads("""{
    # "tarefas": [
    #     {
    #     "etapa": 1,
    #     "titulo": "Planejamento da infraestrutura e tecnologias",
    #     "objetivo": "Definir a infraestrutura, tecnologias e ferramentas necessárias para o projeto de IA.",
    #     "entregaveis": "Plano de infraestrutura, especificação de tecnologias (ex: linguagem de programação, framework de IA), lista de ferramentas (ex: plataformas de aprendizado de máquina, banco de dados)",
    #     "demonstracao": "Desenvolver um plano de infraestrutura detalhado, especificando a plataforma de desenvolvimento, armazenamento de dados, hardware e software.",
    #     "dependencia": 0,
    #     "story_points": 6
    #     },
    #     {
    #     "etapa": 2,
    #     "titulo": "Criação da base de dados de sentimentos",
    #     "objetivo": "Definir como os dados serão coletados e armazenados.",
    #     "entregaveis": "Modelo de dados, blueprint de base de dados, plano de coleta de dados de sentimentos",
    #     "demonstracao": "Definir um modelo de dados para coletar sentimentos de tweets (ex: tags, emoticons, frases), criar um banco de dados para armazenar os dados.",
    #     "dependencia": 1,
    #     "story_points": 4
    #     },
    #     {
    #     "etapa": 3,
    #     "titulo": "Treinamento do modelo de IA",
    #     "objetivo": "Treinar o modelo de IA para análise de sentimentos em redes sociais.",
    #     "entregaveis": "Modelo de IA treinado, código de modelo de IA, documentação de modelo de IA.",
    #     "demonstracao": "Implementar um modelo de aprendizado de máquina (ex: LSTM, BERT) para analisar as redes sociais e determinar a presença de sentimentos (ex: positivo, negativo, neutro).",
    #     "dependencia": 2,
    #     "story_points": 8
    #     },
    #     {
    #     "etapa": 4,
    #     "titulo": "Criação da API",
    #     "objetivo": "Criar a API para interagir com o modelo de IA.",
    #     "entregaveis": "Documentação da API, código da API, exemplos de uso da API",
    #     "demonstracao": "Criar uma API para interagir com o modelo de IA, permitindo que outras aplicações acessem o modelo e utilize a análise de sentimentos.",
    #     "dependencia": 3,
    #     "story_points": 6
    #     },
    #     {
    #     "etapa": 5,
    #     "titulo": "Testes e otimização",
    #     "objetivo": "Testar o modelo de IA e otimizá-lo para melhor precisão.",
    #     "entregaveis": "Prototipo da API, testes de performance, documentação de testes",
    #     "demonstracao": "Implementar testes unitários e de integração para o modelo de IA, otimizar o modelo para melhor precisão e confiabilidade.",
    #     "dependencia": 4,
    #     "story_points": 6
    #     },
    #     {
    #     "etapa": 6,
    #     "titulo": "Implementação da interface",
    #     "objetivo": "Criar uma interface para usuários interagirem com o modelo de IA.",
    #     "entregaveis": "Roteiro de interface, código da interface, documentação da interface",
    #     "demonstracao": "Desenvolver a interface para que os usuários possam interagir com o modelo de IA, utilizando um sistema de busca por sentimentos em redes sociais.",
    #     "dependencia": 5,
    #     "story_points": 8
    #     }
    # ]
    # }""")
                       
    resumo = [
        {
            "etapa": tarefa["etapa"],
            "titulo": tarefa["titulo"],
            "story_points": tarefa["story_points"],
        }
        for tarefa in plano["tarefas"]
    ]
    print(json.dumps(plano, ensure_ascii=False, indent=2))
    print("Estimando duração das tarefas...")
    predictor: EstimadorStoryPoints = request.app.state.story_points_predictor
    try:
        # Um pedido só para o plano inteiro (no modo remoto, uma ida à rede).
        estimativas = predictor.prever_lote(plano["tarefas"])
    except ErroStoryPoints as erro:
        # Servidor de IA fora do ar, chave recusada etc.
        raise HTTPException(status_code=503, detail=str(erro)) from erro
    for tarefa, story_points in zip(plano["tarefas"], estimativas):
        tarefa["story_points"] = story_points
        print(f"Estimativa para a tarefa {tarefa['etapa']}: {tarefa['story_points']} story points")


    return {"prazo": projeto.prazo, "tarefas": plano["tarefas"]}
