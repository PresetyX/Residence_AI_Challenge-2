import json
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, StrictInt, field_validator
import uvicorn

from backend.story_points import StoryPointsPredictor
from destrava.agents.planejador import AgentePlanejador
from destrava.agents.visualizar import AgenteVisualizar
from destrava.rag import obter_rag


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_HISTORICO = RAIZ_PROJETO / "data" / "historico.json"
_LOCK_HISTORICO = Lock()
_MEDIA_INICIAL = 30.0
_QUANTIDADE_INICIAL = 5


def _salvar_historico() -> None:
    CAMINHO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO_HISTORICO.write_text(
        json.dumps(
            {
                "media_minutos_por_story_point": media_minutos_por_story_point,
                "_quantidade_observacoes_media": _quantidade_observacoes_media,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _carregar_historico() -> None:
    global media_minutos_por_story_point, _quantidade_observacoes_media

    CAMINHO_HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    if CAMINHO_HISTORICO.exists():
        dados = json.loads(CAMINHO_HISTORICO.read_text(encoding="utf-8"))
    else:
        dados = {}

    valores_alterados = False
    if "media_minutos_por_story_point" not in dados:
        dados["media_minutos_por_story_point"] = _MEDIA_INICIAL
        valores_alterados = True
    if "_quantidade_observacoes_media" not in dados:
        dados["_quantidade_observacoes_media"] = _QUANTIDADE_INICIAL
        valores_alterados = True

    media_minutos_por_story_point = float(dados["media_minutos_por_story_point"])
    _quantidade_observacoes_media = int(dados["_quantidade_observacoes_media"])
    if valores_alterados:
        _salvar_historico()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _carregar_historico()
    app.state.story_points_predictor = StoryPointsPredictor()
    app.state.planejador = AgentePlanejador(rag=obter_rag("planejador"))
    app.state.visualizador = AgenteVisualizar()
    yield


app = FastAPI(title="Residence AI Challenge", lifespan=lifespan)

media_minutos_por_story_point = _MEDIA_INICIAL
_quantidade_observacoes_media = _QUANTIDADE_INICIAL


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


class HistoricoTarefaRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    story_points: int
    tempo_real_minutos: int

    @field_validator("story_points", "tempo_real_minutos")
    @classmethod
    def validar_valor_nao_negativo(cls, valor: int) -> int:
        if valor < 0:
            raise ValueError("Os valores não podem ser negativos.")
        return valor


class ProjetoResponse(BaseModel):
    prazo: str
    tarefas: list[dict[str, Any]]


class StatusResponse(BaseModel):
    status: str


class TarefasResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    periodo: dict[str, Any] | None = None
    tarefas: list[dict[str, Any]] | None = None


class PerguntasCalibracaoResponse(BaseModel):
    perguntas: list[dict[str, str]]


@app.post("/projetos", response_model=ProjetoResponse)
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
        story_points = predictor.prever(tarefa)
        tarefa.pop("story_points", None)
        tarefa["tempo_estimado_minutos"] = (
            story_points * media_minutos_por_story_point
        )
        print(f"Estimativa para a tarefa {tarefa['etapa']}: {story_points} story points")
    
    return {"prazo": projeto.prazo, "tarefas": plano["tarefas"]}


@app.post("/historico", response_model=StatusResponse, status_code=201)
def registrar_historico(
    historico: HistoricoTarefaRequest,
) -> dict[str, str]:
    if historico.story_points <= 0:
        raise HTTPException(
            status_code=422,
            detail="Os story points devem ser maiores que zero para compor a média.",
        )

    global media_minutos_por_story_point, _quantidade_observacoes_media
    with _LOCK_HISTORICO:
        fator_tarefa = historico.tempo_real_minutos / historico.story_points
        total_observacoes = _quantidade_observacoes_media + 1
        media_minutos_por_story_point = (
            media_minutos_por_story_point * _quantidade_observacoes_media
            + fator_tarefa
        ) / total_observacoes
        _quantidade_observacoes_media = total_observacoes
        _salvar_historico()

    return {"status": "sucesso"}


@app.get("/tarefas", response_model=TarefasResponse)
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


perguntas = json.loads("""{
    "perguntas": [
        {
            "titulo": "Exportação de relatório de vendas em CSV",
            "objetivo": "Permitir que o gerente baixe o relatório mensal de vendas em CSV.",
            "entregaveis": "Endpoint de exportação, botão na interface, teste de integração",
            "demonstracao": "Selecionar um mês na tela de relatórios, clicar em 'Exportar CSV' e abrir o arquivo gerado com os dados corretos."
        },
        {
            "titulo": "Dashboard de monitoramento de infraestrutura",
            "objetivo": "Visualizar em tempo real o uso de CPU, memória e latência dos servidores.",
            "entregaveis": "Coleta de métricas, painéis no Grafana, alertas configurados, documentação de operação",
            "demonstracao": "Simular picos de carga em um servidor de testes e mostrar o painel refletindo a mudança e o alerta sendo disparado."
        },
        {
            "titulo": "Validação de CPF no formulário de cadastro",
            "objetivo": "Impedir o cadastro de CPFs inválidos.",
            "entregaveis": "Função de validação, mensagens de erro, testes unitários",
            "demonstracao": "Preencher o formulário com um CPF inválido e ver a mensagem de erro; em seguida, com um CPF válido e concluir o cadastro."
        },
        {
            "titulo": "Implementação da interface",
            "objetivo": "Criar uma interface para usuários interagirem com o modelo de IA.",
            "entregaveis": "Roteiro de interface, código da interface, documentação da interface",
            "demonstracao": "Desenvolver a interface para que os usuários possam interagir com o modelo de IA, utilizando um sistema de busca por sentimentos em redes sociais."
        },
        {
            "titulo": "Notificações por e-mail para pedidos enviados",
            "objetivo": "Avisar o cliente por e-mail quando o pedido for despachado.",
            "entregaveis": "Template de e-mail, serviço de envio com fila, configuração de provedor SMTP, testes",
            "demonstracao": "Marcar um pedido como 'enviado' no painel administrativo e mostrar o e-mail chegando com o código de rastreio."
        },
        {
            "titulo": "Integração com gateway de pagamento (Pix e cartão)",
            "objetivo": "Permitir que clientes paguem pedidos via Pix e cartão de crédito.",
            "entregaveis": "Integração com o gateway, tratamento de webhooks, tela de checkout, conciliação de status, testes em sandbox, documentação",
            "demonstracao": "Realizar uma compra de ponta a ponta no ambiente sandbox com Pix e com cartão, mostrando a atualização automática do status do pedido."
        },
        {
            "titulo": "Criação da API",
            "objetivo": "Criar a API para interagir com o modelo de IA.",
            "entregaveis": "Documentação da API, código da API, exemplos de uso da API",
            "demonstracao": "Criar uma API para interagir com o modelo de IA, permitindo que outras aplicações acessem o modelo e utilize a análise de sentimentos."
        },
        {
            "titulo": "Correção do alinhamento do botão de login",
            "objetivo": "Corrigir o desalinhamento do botão de login em telas pequenas.",
            "entregaveis": "Ajuste de CSS, captura de tela antes e depois",
            "demonstracao": "Abrir a tela de login em resoluções mobile (320px a 480px) e mostrar o botão corretamente centralizado e clicável."
        },
        {
            "titulo": "Criação da base de dados de sentimentos",
            "objetivo": "Definir como os dados serão coletados e armazenados.",
            "entregaveis": "Modelo de dados, blueprint de base de dados, plano de coleta de dados de sentimentos",
            "demonstracao": "Definir um modelo de dados para coletar sentimentos de tweets (ex: tags, emoticons, frases), criar um banco de dados para armazenar os dados."
        },
        {
            "titulo": "Migração do monolito de autenticação para serviço independente",
            "objetivo": "Extrair o módulo de autenticação para um microsserviço com OAuth2/JWT, sem interromper os usuários atuais.",
            "entregaveis": "Novo serviço de autenticação, plano de migração de usuários e sessões, adaptação dos clientes existentes, testes de carga, plano de rollback, documentação",
            "demonstracao": "Fazer login, renovar o token e acessar recursos protegidos usando o novo serviço, com parte dos usuários migrada gradualmente via feature flag."
        }
    ]
}""")
story_points_perguntas = [3, 7, 2, 8, 5, 10, 6, 1, 4, 13]

@app.get("/calibracao", response_model=PerguntasCalibracaoResponse)
def listar_perguntas_calibracao() -> dict[str, object]:
    return perguntas

@app.post("/calibracao", response_model=StatusResponse)
def registrar_respostas_calibracao(
    respostas: list[StrictInt],
) -> dict[str, str]:
    if len(respostas) != len(story_points_perguntas):
        raise HTTPException(
            status_code=422,
            detail=(
                "O número de respostas deve ser igual ao número de perguntas "
                f"({len(story_points_perguntas)})."
            ),
        )
    if any(resposta <= 0 for resposta in respostas):
        raise HTTPException(
            status_code=422,
            detail="As respostas devem ser tempos reais em minutos maiores que zero.",
        )

    fatores_calibracao = [x / y for x, y in zip(respostas, story_points_perguntas)]
    media_calibrada = sum(fatores_calibracao) / len(fatores_calibracao)
    dp = (
        sum(
            (x - media_calibrada) ** 2
            for x in fatores_calibracao
        )
        / len(fatores_calibracao)
    ) ** 0.5

    global media_minutos_por_story_point, _quantidade_observacoes_media
    with _LOCK_HISTORICO:
        media_minutos_por_story_point = media_calibrada
        _quantidade_observacoes_media = len(fatores_calibracao)
        _salvar_historico()
    
    print(f"Média de minutos por story point: {media_minutos_por_story_point:.2f}")
    print(f"Desvio padrão: {dp:.2f}")
    return {"status": "sucesso"}
