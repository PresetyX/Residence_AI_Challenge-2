import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import SQLAlchemyError
import uvicorn

from backend.database import get_session_factory
from backend.history_models import HistoricoTarefa
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


@app.post("/historico", status_code=201)
def registrar_historico(
    historico: HistoricoTarefaRequest,
) -> dict[str, object]:
    registro = HistoricoTarefa(**historico.model_dump())
    session = get_session_factory()()
    try:
        session.add(registro)
        session.commit()
        session.refresh(registro)
        print("Histórico registrado com sucesso: ", registro)
    except SQLAlchemyError:
        session.rollback()
        print("Erro ao registrar histórico de tarefa.")
        raise
    finally:
        session.close()

    return {
        "id": registro.id,
        "story_points": registro.story_points,
        "tempo_real_minutos": registro.tempo_real_minutos,
        "criado_em": registro.criado_em,
    }


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

@app.get("/calibracao")
def listar_perguntas_calibracao():
    return {"perguntas": perguntas}

@app.post("/calibracao")
def registrar_respostas_calibracao(respostas: list[int]):
    if len(respostas) != len(story_points_perguntas):
        raise ValueError("O número de respostas não corresponde ao número de perguntas.")
    
    fatores_calibracao = [x / y for x, y in zip(respostas, story_points_perguntas)]
    media_minutos_por_story_point = sum(fatores_calibracao) / len(fatores_calibracao)
    dp = (sum((x - media_minutos_por_story_point) ** 2 for x in fatores_calibracao) / len(fatores_calibracao)) ** 0.5
    
    print(f"Média de minutos por story point: {media_minutos_por_story_point:.2f}")
    print(f"Desvio padrão: {dp:.2f}")
    return {"status": "sucesso", "media_minutos_por_story_point": media_minutos_por_story_point}