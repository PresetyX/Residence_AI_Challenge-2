"""Servidor de IA compartilhado: config por ambiente, Ollama remoto e story points.

Nenhum teste usa rede de verdade nem carrega o BGE-M3: o Ollama é simulado no
httpx e o modelo de story points é trocado por um falso.
"""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import backend.main as main
import backend.servidor_story_points as servidor
import backend.story_points as story_points
from backend.story_points import ErroStoryPoints, StoryPointsRemoto, criar_estimador
from destrava.core import config, llm_client

RAIZ = Path(__file__).resolve().parents[1]
VARIAVEIS = (
    "MODELO",
    "MODELO_EMBEDDING",
    "OLLAMA_URL",
    "TIMEOUT_LLM",
    "NUM_CTX",
    "STORY_POINTS_URL",
    "TIMEOUT_STORY_POINTS",
    "CHAVE_API_IA",
)


def tarefa(etapa: int, titulo: str = "Planejamento") -> dict:
    return {
        "etapa": etapa,
        "titulo": titulo,
        "objetivo": "Definir o escopo do projeto.",
        "entregaveis": "Documento de escopo.",
        "demonstracao": "Resumo das funcionalidades.",
        "dependencia": etapa - 1,
        "story_points": 3,
    }


@pytest.fixture
def ambiente(monkeypatch):
    """Recarrega o config com as variáveis de ambiente dadas; restaura no fim."""

    def aplicar(**valores):
        for nome in VARIAVEIS:
            monkeypatch.delenv(nome, raising=False)
        for nome, valor in valores.items():
            monkeypatch.setenv(nome, valor)
        importlib.reload(config)
        return config

    yield aplicar
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    importlib.reload(config)


# ------------------------------------------------------------ config.py


def test_config_sem_variaveis_usa_os_padroes(ambiente):
    cfg = ambiente()
    assert cfg.OLLAMA_URL == "http://localhost:11434"
    assert cfg.MODELO == "gemma2:2b"
    assert cfg.STORY_POINTS_URL == ""
    assert cfg.CHAVE_API_IA == ""
    assert cfg.NUM_CTX == 8192
    assert cfg.TIMEOUT_LLM >= 300


def test_config_le_as_variaveis_de_ambiente(ambiente):
    cfg = ambiente(
        OLLAMA_URL="http://servidor-ia:11434",
        MODELO="gemma4:12b-it-q4_K_M",
        STORY_POINTS_URL="http://servidor-ia:8001",
        TIMEOUT_LLM="900",
        NUM_CTX="16384",
        CHAVE_API_IA="segredo",
    )
    assert cfg.OLLAMA_URL == "http://servidor-ia:11434"
    assert cfg.MODELO == "gemma4:12b-it-q4_K_M"
    assert cfg.STORY_POINTS_URL == "http://servidor-ia:8001"
    assert cfg.TIMEOUT_LLM == 900
    assert cfg.NUM_CTX == 16384
    assert cfg.CHAVE_API_IA == "segredo"


def test_variavel_vazia_vale_como_ausente(ambiente):
    assert ambiente(OLLAMA_URL="   ").OLLAMA_URL == "http://localhost:11434"


@pytest.mark.parametrize("valor", ["muito", "0", "-5"])
def test_timeout_invalido_falha_com_mensagem_clara(ambiente, valor):
    with pytest.raises(ValueError, match="TIMEOUT_LLM"):
        ambiente(TIMEOUT_LLM=valor)


# --------------------------------------------- Ollama remoto (llm_client)


@pytest.fixture
def ollama_falso(monkeypatch):
    """Responde como o Ollama e guarda cada requisição que chegaria a ele."""
    pedidos: list[httpx.Request] = []

    def enviar(self, request, *args, **kwargs):
        pedidos.append(request)
        if request.url.path == "/api/embed":
            corpo = json.loads(request.content)
            vetores = [[0.1, 0.2, 0.3] for _ in corpo["input"]]
            return httpx.Response(200, json={"model": corpo["model"], "embeddings": vetores}, request=request)
        linha = {
            "model": "falso",
            "created_at": "2026-11-11T00:00:00Z",
            "message": {"role": "assistant", "content": '{"ok": true}'},
            "done": True,
            "done_reason": "stop",
        }
        return httpx.Response(
            200,
            content=(json.dumps(linha) + "\n").encode(),
            headers={"Content-Type": "application/x-ndjson"},
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "send", enviar)
    return pedidos


def test_chat_vai_para_o_ollama_remoto_com_num_ctx(ambiente, ollama_falso):
    ambiente(OLLAMA_URL="http://servidor-ia:11434", MODELO="gemma4:12b-it-q4_K_M")

    resposta = llm_client.perguntar("Planeje o projeto.")

    assert resposta == '{"ok": true}'
    pedido = ollama_falso[-1]
    assert pedido.url.host == "servidor-ia"
    assert pedido.url.port == 11434
    corpo = json.loads(pedido.content)
    assert corpo["model"] == "gemma4:12b-it-q4_K_M"
    assert corpo["options"]["num_ctx"] == 8192
    assert "authorization" not in pedido.headers


def test_num_ctx_vem_da_variavel_de_ambiente(ambiente, ollama_falso):
    ambiente(NUM_CTX="12288")
    llm_client.perguntar("oi")
    assert json.loads(ollama_falso[-1].content)["options"]["num_ctx"] == 12288


def test_chave_de_api_segue_no_cabecalho_para_o_ollama(ambiente, ollama_falso):
    ambiente(CHAVE_API_IA="segredo")
    llm_client.perguntar("oi")
    llm_client.criar_embeddings().embed_query("oi")
    assert [p.headers["authorization"] for p in ollama_falso] == ["Bearer segredo"] * 2


def test_embeddings_do_rag_usam_o_mesmo_servidor(ambiente, ollama_falso):
    ambiente(OLLAMA_URL="http://servidor-ia:11434")
    vetores = llm_client.criar_embeddings().embed_documents(["trecho um", "trecho dois"])
    assert len(vetores) == 2
    assert ollama_falso[-1].url.host == "servidor-ia"
    assert ollama_falso[-1].url.path == "/api/embed"


def test_ollama_fora_do_ar_vira_erro_llm_com_dica(ambiente, monkeypatch):
    ambiente(OLLAMA_URL="http://servidor-ia:11434")

    def sem_rede(*args, **kwargs):
        raise httpx.ConnectError("sem rota")

    monkeypatch.setattr(httpx.Client, "send", sem_rede)
    with pytest.raises(llm_client.ErroLLM, match="servidor-ia.*Tailscale"):
        llm_client.perguntar("oi")


# ----------------------------------------- story points: cliente remoto


def remoto(manipulador, chave: str = "") -> StoryPointsRemoto:
    return StoryPointsRemoto(
        "http://servidor-ia:8001/", chave=chave, transport=httpx.MockTransport(manipulador)
    )


def test_cliente_remoto_envia_as_tarefas_e_le_os_story_points():
    recebido = {}

    def manipulador(request: httpx.Request) -> httpx.Response:
        recebido["url"] = str(request.url)
        recebido["corpo"] = json.loads(request.content)
        recebido["chave"] = request.headers.get("x-api-key")
        return httpx.Response(200, json={"story_points": [5, 8]})

    valores = remoto(manipulador, chave="segredo").prever_lote([tarefa(1), tarefa(2, "Testes")])

    assert valores == [5, 8]
    assert recebido["url"] == "http://servidor-ia:8001/story-points"
    assert recebido["chave"] == "segredo"
    # Só os quatro campos de texto vão pela rede.
    assert recebido["corpo"]["tarefas"][1] == {
        "titulo": "Testes",
        "objetivo": "Definir o escopo do projeto.",
        "entregaveis": "Documento de escopo.",
        "demonstracao": "Resumo das funcionalidades.",
    }


def test_cliente_remoto_sem_chave_nao_envia_cabecalho():
    def manipulador(request):
        assert "x-api-key" not in request.headers
        return httpx.Response(200, json={"story_points": [3]})

    assert remoto(manipulador).prever(tarefa(1)) == 3


def test_lista_vazia_nao_chama_o_servidor():
    def manipulador(request):
        raise AssertionError("não deveria chamar o servidor")

    assert remoto(manipulador).prever_lote([]) == []


@pytest.mark.parametrize(
    ("resposta", "trecho"),
    [
        (httpx.Response(401, json={"detail": "x"}), "CHAVE_API_IA"),
        (httpx.Response(500, text="erro interno"), "HTTP 500"),
        (httpx.Response(200, json={"outra_coisa": []}), "resposta inválida"),
        (httpx.Response(200, json={"story_points": [1]}), "cada tarefa"),
        (httpx.Response(200, json={"story_points": ["5", "8"]}), "cada tarefa"),
        (httpx.Response(200, text="não é json"), "resposta inválida"),
    ],
)
def test_cliente_remoto_rejeita_respostas_ruins(resposta, trecho):
    with pytest.raises(ErroStoryPoints, match=trecho):
        remoto(lambda request: resposta).prever_lote([tarefa(1), tarefa(2)])


@pytest.mark.parametrize(
    ("erro", "trecho"),
    [
        (httpx.ConnectError("recusado"), "Não foi possível conectar"),
        (httpx.ReadTimeout("devagar"), "demorou demais"),
    ],
)
def test_cliente_remoto_fora_do_ar_vira_erro_story_points(erro, trecho):
    def manipulador(request):
        raise erro

    with pytest.raises(ErroStoryPoints, match=trecho):
        remoto(manipulador).prever(tarefa(1))


# ------------------------------------------- story points: modo local x remoto


class PredictorFalso:
    """Faz o papel do StoryPointsPredictor sem carregar o BGE-M3."""

    instancias = 0

    def __init__(self):
        type(self).instancias += 1
        self.dispositivo = "cuda:0"
        self.chamadas = 0

    def prever(self, tarefa):
        return self.prever_lote([tarefa])[0]

    def prever_lote(self, tarefas):
        self.chamadas += 1
        return [len(t["titulo"]) for t in tarefas]


@pytest.fixture
def predictor_falso(monkeypatch):
    PredictorFalso.instancias = 0
    monkeypatch.setattr(story_points, "StoryPointsPredictor", PredictorFalso)
    monkeypatch.setattr(servidor, "criar_predictor", PredictorFalso)
    return PredictorFalso


def test_sem_url_o_estimador_e_local(ambiente, predictor_falso):
    ambiente()
    assert isinstance(criar_estimador(), PredictorFalso)


def test_com_url_o_estimador_e_remoto_e_nao_carrega_o_modelo(ambiente, predictor_falso):
    ambiente(STORY_POINTS_URL="http://servidor-ia:8001", CHAVE_API_IA="segredo")
    estimador = criar_estimador()
    assert isinstance(estimador, StoryPointsRemoto)
    assert estimador.url == "http://servidor-ia:8001"
    assert predictor_falso.instancias == 0


def test_modo_remoto_nao_importa_torch():
    """O notebook do time não tem torch: o backend precisa subir sem ele."""
    codigo = (
        "import sys, backend.main; "
        "print(sorted(m for m in ('torch', 'sentence_transformers', 'transformers') if m in sys.modules))"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env={**__import__("os").environ, "STORY_POINTS_URL": "http://servidor-ia:8001"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "[]"


# ------------------------------------------------------ backend/main.py


class PlanejadorFalso:
    def executar(self, projeto, prazo):
        return {"tarefas": [tarefa(1), tarefa(2, "Implementação")]}


@pytest.fixture
def lifespan_sem_rag(monkeypatch):
    monkeypatch.setattr(main, "obter_rag", lambda nome: None)
    monkeypatch.setattr(main, "AgentePlanejador", lambda rag: PlanejadorFalso())


def test_lifespan_local_carrega_o_predictor(ambiente, predictor_falso, lifespan_sem_rag):
    ambiente()
    with TestClient(main.app):
        assert isinstance(main.app.state.story_points_predictor, PredictorFalso)


def test_lifespan_remoto_nao_carrega_o_predictor(ambiente, predictor_falso, lifespan_sem_rag):
    ambiente(STORY_POINTS_URL="http://servidor-ia:8001")
    with TestClient(main.app):
        assert isinstance(main.app.state.story_points_predictor, StoryPointsRemoto)
    assert predictor_falso.instancias == 0


def projeto(estimador) -> httpx.Response:
    main.app.state.planejador = PlanejadorFalso()
    main.app.state.story_points_predictor = estimador
    # Sem `with`: não roda o lifespan (o estado já foi montado acima).
    return TestClient(main.app).post("/projetos", json={"texto": "Um app de receitas", "prazo": "2026-12-31"})


def test_projeto_usa_os_story_points_do_servidor_remoto():
    resposta = projeto(remoto(lambda request: httpx.Response(200, json={"story_points": [13, 21]})))
    assert resposta.status_code == 200
    assert [t["story_points"] for t in resposta.json()["tarefas"]] == [13, 21]


def test_projeto_com_servidor_de_story_points_fora_do_ar_da_503():
    def manipulador(request):
        raise httpx.ConnectError("recusado")

    resposta = projeto(remoto(manipulador))
    assert resposta.status_code == 503
    assert "servidor-ia:8001" in resposta.json()["detail"]


def test_projeto_no_modo_local_faz_um_lote_so():
    estimador = PredictorFalso()
    resposta = projeto(estimador)
    assert resposta.status_code == 200
    assert [t["story_points"] for t in resposta.json()["tarefas"]] == [12, 13]
    assert estimador.chamadas == 1


# ------------------------------------- backend/servidor_story_points.py


@pytest.fixture
def cliente_servidor(ambiente, predictor_falso):
    def abrir(**variaveis):
        ambiente(**variaveis)
        return TestClient(servidor.app)

    return abrir


def corpo(*titulos):
    return {"tarefas": [{k: v for k, v in tarefa(i, t).items() if k in story_points.CAMPOS_TAREFA} for i, t in enumerate(titulos, 1)]}


def test_servidor_carrega_o_modelo_uma_vez_so(cliente_servidor, predictor_falso):
    with cliente_servidor() as cliente:
        primeira = cliente.post("/story-points", json=corpo("Planejamento", "Testes"))
        segunda = cliente.post("/story-points", json=corpo("Deploy"))
    assert primeira.json() == {"story_points": [12, 6]}
    assert segunda.json() == {"story_points": [6]}
    assert predictor_falso.instancias == 1


def test_servidor_saude(cliente_servidor):
    with cliente_servidor() as cliente:
        assert cliente.get("/saude").json() == {"status": "ok", "dispositivo": "cuda:0"}


@pytest.mark.parametrize(
    "pedido",
    [
        {"tarefas": []},
        {"tarefas": [{"titulo": "x"}]},
        {"tarefas": [{"titulo": " ", "objetivo": "", "entregaveis": "", "demonstracao": ""}]},
        {"tarefas": [{"titulo": "x", "objetivo": "y", "entregaveis": "z", "demonstracao": "w"}] * 51},
    ],
)
def test_servidor_valida_o_pedido(cliente_servidor, pedido):
    with cliente_servidor() as cliente:
        assert cliente.post("/story-points", json=pedido).status_code == 422


def test_servidor_com_chave_exige_o_cabecalho(cliente_servidor):
    with cliente_servidor(CHAVE_API_IA="segredo") as cliente:
        sem_chave = cliente.post("/story-points", json=corpo("Deploy"))
        errada = cliente.post("/story-points", json=corpo("Deploy"), headers={"X-API-Key": "chute"})
        certa = cliente.post("/story-points", json=corpo("Deploy"), headers={"X-API-Key": "segredo"})
        saude = cliente.get("/saude")
    assert sem_chave.status_code == errada.status_code == 401
    assert certa.json() == {"story_points": [6]}
    assert saude.status_code == 200


def test_servidor_sem_chave_configurada_fica_aberto(cliente_servidor):
    with cliente_servidor() as cliente:
        assert cliente.post("/story-points", json=corpo("Deploy")).status_code == 200
