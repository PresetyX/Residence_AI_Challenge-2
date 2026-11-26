import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from backend.calendario import router as calendario_router
from backend.chat import modelo_ollama, router as chat_router
from backend import perfil
from backend.story_points import ErroStoryPoints, EstimadorStoryPoints, criar_estimador
from destrava.agents.planejador import AgentePlanejador, ErroPlanejador, PedidoNaoEntendido
from destrava.agents.supervisor import AgenteSupervisor
from destrava.tools.visualizar import AgenteVisualizar
from destrava.core import config
from destrava.core.pomodoro import minutos_de_trabalho
from destrava.core.prazo import interpretar_prazo
from destrava.rag import obter_rag
from backend.database import (
    buscar_storypoints_evento,
    inicializar_banco_eventos,
    salvar_storypoints_eventos,
)


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CAMINHO_HISTORICO = RAIZ_PROJETO / "data" / "historico.json"
_LOCK_HISTORICO = Lock()
_LOCK_AGENDAMENTO = Lock()
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


async def lifespan(app: FastAPI):
    _carregar_historico()
    inicializar_banco_eventos()
    # Sono e calibração da última conta que entrou (data/perfis.json).
    perfil.ativar_conta_salva()
    # Com STORY_POINTS_URL definido, o estimador é só um cliente HTTP do
    # servidor de IA: nada de torch nem de BGE-M3 nesta máquina. Sem ele, o
    # modelo é carregado aqui (modo local, requirements-ia.txt).
    app.state.story_points_predictor = criar_estimador()
    modo = f"remoto ({config.STORY_POINTS_URL})" if config.STORY_POINTS_URL else "local"
    print(f"Story points: modo {modo}. LLM: {config.MODELO} em {config.OLLAMA_URL}.")
    app.state.planejador = AgentePlanejador(rag=obter_rag("planejador"))
    app.state.visualizador = AgenteVisualizar()
    app.state.supervisor = AgenteSupervisor(
        visualizador=app.state.visualizador,
        criador=None,
        planejador=app.state.planejador,
    )
    yield


app = FastAPI(title="Residence AI Challenge", lifespan=lifespan)

media_minutos_por_story_point = _MEDIA_INICIAL
_quantidade_observacoes_media = _QUANTIDADE_INICIAL

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
    # Qualquer porta em localhost (o Next.js sobe na 3001 se a 3000 estiver ocupada).
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", r"http://(localhost|127\.0\.0\.1)(:\d+)?"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)
app.include_router(calendario_router)
app.include_router(perfil.router)


@app.get("/")
def raiz() -> dict[str, object]:
    return {}


class ProjetoRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    texto: str
    # Opcional: sem ele, o prazo é lido do próprio texto ("até amanhã",
    # "tenho uma semana", "20/12"...). Sem prazo nenhum, o plano sai assim mesmo
    # e a resposta traz precisa_prazo=True.
    prazo: str | None = None
    # Id do seletor de modelo do chat. Sem ele, o Planejador usa config.MODELO.
    modelo: str | None = None

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, texto: str) -> str:
        texto = texto.strip()
        if not texto:
            raise ValueError("O texto do projeto não pode ser vazio.")
        return texto

    @field_validator("prazo")
    @classmethod
    def validar_prazo(cls, prazo: str | None) -> str | None:
        if prazo is None:
            return None
        prazo = prazo.strip()
        if not prazo:
            raise ValueError("O prazo não pode ser vazio.")
        return prazo


class InterpretarPrazoRequest(BaseModel):
    texto: str


def _prazo_do_texto(texto: str) -> str | None:
    """Prazo escrito no texto, em AAAA-MM-DD. 422 se a data não existir ou já passou."""
    try:
        prazo = interpretar_prazo(texto)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    if prazo is None:
        return None
    if prazo < datetime.now(config.FUSO).date():
        raise HTTPException(
            status_code=422,
            detail=f"Esse prazo ({prazo:%d/%m/%Y}) já passou. Qual é a nova data de entrega?",
        )
    return prazo.isoformat()


@app.post("/prazos/interpretar")
def interpretar_prazo_do_texto(corpo: InterpretarPrazoRequest) -> dict[str, str | None]:
    """Lê o prazo de uma resposta como "até amanhã" ou "tenho uma semana"."""
    return {"prazo": _prazo_do_texto(corpo.texto)}


class HistoricoTarefaRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    id_evento: str
    tempo_real_minutos: int

    @field_validator("id_evento")
    @classmethod
    def validar_id_evento(cls, id_evento: str) -> str:
        id_evento = id_evento.strip()
        if not id_evento:
            raise ValueError("O id do evento não pode ser vazio.")
        return id_evento

    @field_validator("tempo_real_minutos")
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


class AgendarProjetoRequest(BaseModel):
    prazo: str
    tarefas: list[dict] = Field(min_length=1)


class ConfirmarAgendamentoRequest(BaseModel):
    confirmado: bool


@app.post("/projetos/agendar")
def agendar_projeto(
    corpo: AgendarProjetoRequest,
    request: Request,
) -> dict:
    supervisor: AgenteSupervisor = request.app.state.supervisor
    with _LOCK_AGENDAMENTO:
        supervisor.evento_pendente = None
        return supervisor.preparar_agendamento(corpo.prazo, corpo.tarefas)


@app.post("/projetos/agendar/confirmar")
def confirmar_agendamento(
    corpo: ConfirmarAgendamentoRequest,
    request: Request,
) -> dict:
    supervisor: AgenteSupervisor = request.app.state.supervisor
    with _LOCK_AGENDAMENTO:
        resultado = supervisor.confirmar_agendamento(corpo.confirmado)

        dados = resultado.get("dados")
        eventos_criados = dados.get("eventos_criados", []) if isinstance(dados, dict) else []
        salvar_storypoints_eventos(eventos_criados)
        return resultado


@app.post("/projetos")
def criar_projeto(
    projeto: ProjetoRequest,
    request: Request,
) -> dict[str, object]:
    prazo = projeto.prazo or _prazo_do_texto(projeto.texto)
    # Sem prazo, planeja com um provisório (30 dias): o prazo só dá contexto ao
    # Planejador, e é ele quem diz se o texto é mesmo um projeto.
    prazo_planejamento = prazo or (datetime.now(config.FUSO).date() + timedelta(days=30)).isoformat()
    print("Planejando projeto: ", projeto.texto, "com prazo", prazo or "(não informado)", "...")
    planejador: AgentePlanejador = request.app.state.planejador
    try:
        opcoes = {"modelo": modelo_ollama(projeto.modelo)} if projeto.modelo else {}
        plano = planejador.executar(projeto.texto, prazo_planejamento, **opcoes)
    except PedidoNaoEntendido as erro:
        # A IA não entendeu o projeto: o frontend mostra a pergunta e espera
        # mais detalhes (mesmo prazo).
        return {"prazo": prazo, "tarefas": [], "nao_entendi": True, "mensagem": str(erro)}
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
        # Cada story point vale MINUTOS_POR_STORY_POINT (60 min, pomodoro.py), o
        # mesmo tempo que o Supervisor reserva na agenda ao encaixar a tarefa.
        tarefa["tempo_estimado_minutos"] = minutos_de_trabalho(tarefa)
        print(f"Estimativa para a tarefa {tarefa['etapa']}: {tarefa['story_points']} story points")


    resposta: dict[str, object] = {"prazo": prazo, "tarefas": plano["tarefas"]}
    if prazo is None:
        resposta["precisa_prazo"] = True
    return resposta


@app.post("/historico", response_model=StatusResponse, status_code=201)
def registrar_historico(
    historico: HistoricoTarefaRequest,
) -> dict[str, str]:
    story_points = buscar_storypoints_evento(historico.id_evento)
    if story_points is None:
        raise HTTPException(
            status_code=404,
            detail="Não existe um registro de story points para este evento.",
        )
    if story_points <= 0:
        raise HTTPException(
            status_code=422,
            detail="Os story points devem ser maiores que zero para compor a média.",
        )

    global media_minutos_por_story_point, _quantidade_observacoes_media
    with _LOCK_HISTORICO:
        fator_tarefa = historico.tempo_real_minutos / story_points
        total_observacoes = _quantidade_observacoes_media + 1
        media_minutos_por_story_point = (
            media_minutos_por_story_point * _quantidade_observacoes_media
            + fator_tarefa
        ) / total_observacoes
        _quantidade_observacoes_media = total_observacoes
        _salvar_historico()

    print(f"Nova média de minutos por story point: {media_minutos_por_story_point:.2f}")

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
    respostas: list[StrictInt | None],
) -> dict[str, str]:
    """Respostas das perguntas de calibração: minutos de cada tarefa, ou null (pulou).

    A média de minutos por story point vira o tempo de cada story point da
    conta ativa (pomodoro.MINUTOS_POR_STORY_POINT) e fica salva no perfil.
    """
    if len(respostas) != len(story_points_perguntas):
        raise HTTPException(
            status_code=422,
            detail=(
                "O número de respostas deve ser igual ao número de perguntas "
                f"({len(story_points_perguntas)})."
            ),
        )
    if any(resposta is not None and resposta <= 0 for resposta in respostas):
        raise HTTPException(
            status_code=422,
            detail="As respostas devem ser tempos reais em minutos maiores que zero.",
        )
    try:
        media_calibrada = perfil.calcular_minutos_por_story_point(respostas, story_points_perguntas)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro

    global media_minutos_por_story_point, _quantidade_observacoes_media
    with _LOCK_HISTORICO:
        media_minutos_por_story_point = media_calibrada
        _quantidade_observacoes_media = sum(resposta is not None for resposta in respostas)
        _salvar_historico()
    perfil.salvar_calibracao(media_calibrada, list(respostas))

    print(f"Média de minutos por story point: {media_minutos_por_story_point:.2f}")
    return {"status": "sucesso"}
