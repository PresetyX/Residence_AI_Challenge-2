"""Testes do contrato JSON padrão dos agentes (sem Google e sem Ollama).

O Google Calendar e o LLM são simulados com mocks, então os testes rodam
em qualquer máquina:  python -m pytest tests/
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from destrava.agents import criar, visualizar
from destrava.core import config
from destrava.core.llm_client import extrair_json
from destrava.core.resposta import MENSAGEM_GENERICA


CHAVES_PADRAO = {
    "agente", "status", "acao", "mensagem", "periodo", "dados", "fluxo", "erro",
}


def _amanha(hora: int) -> datetime:
    dia = datetime.now(config.FUSO).date() + timedelta(days=1)
    return datetime(dia.year, dia.month, dia.day, hora, tzinfo=config.FUSO)


def _servico_que_cria(evento: dict) -> MagicMock:
    servico = MagicMock()
    servico.events.return_value.insert.return_value.execute.return_value = evento
    return servico


def _llm(*respostas):
    """Simula o perguntar(): devolve as respostas em ordem."""
    return MagicMock(side_effect=list(respostas))


# ---------------------------------------------------------------- criar


def _evento_google(inicio: datetime, fim: datetime) -> dict:
    return {
        "id": "abc123",
        "summary": "Reunião",
        "htmlLink": "https://calendar.google.com/event?eid=abc123",
        "start": {"dateTime": inicio.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": fim.isoformat(), "timeZone": "America/Sao_Paulo"},
    }


def test_criar_devolve_json_padrao_com_periodo():
    inicio, fim = _amanha(14), _amanha(15)
    extracao = json.dumps(
        {"titulo": "Reunião", "inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
         "fim": fim.strftime("%Y-%m-%dT%H:%M")}
    )
    llm = _llm(f"```json\n{extracao}\n```")
    servico = _servico_que_cria(_evento_google(inicio, fim))

    with patch.object(criar, "perguntar", llm), \
         patch.object(criar, "get_service", return_value=servico):
        resposta = criar.AgenteCriar().executar_por_texto("reunião amanhã 14h às 15h")

    dados = json.loads(resposta.para_json())
    assert set(dados) == CHAVES_PADRAO
    assert dados["agente"] == "criar"
    assert dados["status"] == "sucesso"
    assert dados["acao"] == "evento_criado"
    # A mensagem é montada pelo código e o LLM só foi chamado na extração.
    assert dados["mensagem"] == (
        f"Pronto! Criei \"Reunião\" em {inicio:%d/%m/%Y}, "
        f"das {inicio:%H:%M} às {fim:%H:%M}."
    )
    assert llm.call_count == 1

    assert datetime.fromisoformat(dados["periodo"]["inicio"]) == inicio
    assert datetime.fromisoformat(dados["periodo"]["fim"]) == fim
    assert dados["periodo"]["duracao_minutos"] == 60

    assert dados["dados"]["periodo_confere"] is True
    assert dados["dados"]["evento"]["id"] == "abc123"
    assert [dados["fluxo"][e]["status"] for e in ("inicio", "meio", "fim")] == [
        "ok", "ok", "ok",
    ]
    assert dados["erro"] is None


def test_criar_detecta_periodo_diferente_do_pedido():
    inicio, fim = _amanha(14), _amanha(15)
    extracao = json.dumps(
        {"titulo": "Reunião", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
    )
    # O Google devolve uma hora a mais no fim.
    servico = _servico_que_cria(_evento_google(inicio, fim + timedelta(hours=1)))

    with patch.object(criar, "perguntar", _llm(extracao)), \
         patch.object(criar, "get_service", return_value=servico):
        resposta = criar.AgenteCriar().executar_por_texto("reunião")

    assert resposta.status == "sucesso"
    assert resposta.dados["periodo_confere"] is False
    assert "Atenção" in resposta.mensagem
    assert resposta.fluxo.meio.detalhe["periodo_confere"] is False


def test_criar_dados_incompletos_vira_erro_no_inicio():
    extracao = '{"titulo": "Consulta médica", "inicio": null, "fim": null}'
    get_service = MagicMock()

    with patch.object(criar, "perguntar", _llm(extracao)), \
         patch.object(criar, "get_service", get_service):
        resposta = criar.AgenteCriar().executar_por_texto("marque uma consulta")

    assert resposta.status == "erro"
    assert resposta.acao == "evento_nao_criado"
    assert resposta.fluxo.inicio.status == "erro"
    assert resposta.fluxo.meio.status == "pendente"
    assert resposta.erro.tipo == "ValueError"
    get_service.assert_not_called()


def test_criar_cancelado_nao_chama_google():
    inicio, fim = _amanha(9), _amanha(10)
    extracao = json.dumps(
        {"titulo": "Estudar", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
    )
    get_service = MagicMock()

    with patch.object(criar, "perguntar", _llm(extracao)), \
         patch.object(criar, "get_service", get_service):
        resposta = criar.AgenteCriar().executar_por_texto(
            "estudar amanhã", confirmar=lambda dados: False
        )

    assert resposta.status == "cancelado"
    assert resposta.periodo.inicio == inicio
    get_service.assert_not_called()


def test_criar_nao_chama_llm_para_montar_a_resposta():
    inicio, fim = _amanha(14), _amanha(16)
    extracao = json.dumps(
        {"titulo": "Reunião", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
    )
    llm = _llm(extracao)
    servico = _servico_que_cria(_evento_google(inicio, fim))

    with patch.object(criar, "perguntar", llm), \
         patch.object(criar, "get_service", return_value=servico):
        resposta = criar.AgenteCriar().executar_por_texto("reunião")

    assert llm.call_count == 1  # só a extração; a resposta não usa LLM
    assert resposta.status == "sucesso"
    assert resposta.fluxo.fim.status == "ok"
    assert resposta.erro is None
    assert "Reunião" in resposta.mensagem
    assert f"{inicio:%H:%M}" in resposta.mensagem


def test_erro_ao_montar_mensagem_mantem_sucesso(monkeypatch):
    inicio, fim = _amanha(14), _amanha(16)
    extracao = json.dumps(
        {"titulo": "Reunião", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
    )
    servico = _servico_que_cria(_evento_google(inicio, fim))
    monkeypatch.setattr(
        criar, "montar_mensagem", MagicMock(side_effect=KeyError("evento"))
    )

    with patch.object(criar, "perguntar", _llm(extracao)), \
         patch.object(criar, "get_service", return_value=servico):
        resposta = criar.AgenteCriar().executar_por_texto("reunião")

    # A ação já foi feita: continua sucesso, com mensagem genérica.
    assert resposta.status == "sucesso"
    assert resposta.fluxo.fim.status == "erro"
    assert resposta.erro.tipo == "KeyError"
    assert resposta.mensagem == MENSAGEM_GENERICA


# ---------------------------------------------------------- visualizar


def test_visualizar_devolve_json_padrao_com_periodo():
    inicio, fim = _amanha(0), _amanha(0) + timedelta(days=1)
    extracao = json.dumps(
        {"inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
         "fim": fim.strftime("%Y-%m-%dT%H:%M")}
    )
    eventos = [_evento_google(_amanha(10), _amanha(11))]

    llm = _llm(extracao)
    with patch.object(visualizar, "perguntar", llm), \
         patch.object(visualizar, "get_service"), \
         patch.object(visualizar, "listar_eventos", return_value=eventos):
        resposta = visualizar.AgenteVisualizar().executar_por_texto("e amanhã?")

    dados = resposta.para_dict()
    assert set(dados) == CHAVES_PADRAO
    assert dados["agente"] == "visualizar"
    assert dados["status"] == "sucesso"
    assert dados["acao"] == "agenda_visualizada"
    assert datetime.fromisoformat(dados["periodo"]["inicio"]) == inicio
    assert datetime.fromisoformat(dados["periodo"]["fim"]) == fim
    assert dados["periodo"]["duracao_minutos"] == 24 * 60
    assert dados["fluxo"]["inicio"]["detalhe"]["periodo_padrao"] is False
    assert dados["fluxo"]["meio"]["detalhe"]["total_eventos"] == 1
    assert {"ocupados", "livres", "conflitos"} <= set(dados["dados"])
    assert llm.call_count == 1  # só a extração; a resposta não usa LLM
    assert dados["fluxo"]["fim"]["status"] == "ok"
    assert "Horários livres:" in dados["mensagem"]
    assert "Reunião: " in dados["mensagem"]


def test_visualizar_json_invalido_usa_periodo_padrao():
    with patch.object(visualizar, "perguntar", _llm("não sei")), \
         patch.object(visualizar, "get_service"), \
         patch.object(visualizar, "listar_eventos", return_value=[]):
        resposta = visualizar.AgenteVisualizar().executar_por_texto("???")

    assert resposta.status == "sucesso"
    assert resposta.fluxo.inicio.detalhe["periodo_padrao"] is True
    assert resposta.periodo.duracao_minutos == 7 * 24 * 60


def test_visualizar_sem_credenciais_vira_erro_no_meio():
    extracao = '{"inicio": "2030-01-01T00:00", "fim": "2030-01-01T23:59"}'

    with patch.object(visualizar, "perguntar", _llm(extracao)), \
         patch.object(
             visualizar, "get_service",
             side_effect=FileNotFoundError("credentials.json não encontrado"),
         ):
        resposta = visualizar.AgenteVisualizar().executar_por_texto("dia 1")

    assert resposta.status == "erro"
    assert resposta.fluxo.inicio.status == "ok"
    assert resposta.fluxo.meio.status == "erro"
    assert resposta.erro.tipo == "FileNotFoundError"
    assert resposta.periodo is not None  # o período pedido continua no JSON


def _resultado_visualizacao(eventos: list[dict], inicio, fim):
    from destrava.core.resposta import Periodo, ResultadoExecucao

    with patch.object(visualizar, "get_service"), \
         patch.object(visualizar, "listar_eventos", return_value=eventos):
        dados = visualizar.AgenteVisualizar().executar(inicio, fim)
    return ResultadoExecucao(dados=dados, periodo=Periodo.de(inicio, fim))


def test_visualizar_mensagem_lista_conflitos_pelo_titulo():
    inicio, fim = _amanha(0), _amanha(0) + timedelta(days=1)
    eventos = [
        {**_evento_google(_amanha(10), _amanha(12)), "id": "a", "summary": "Aula"},
        {**_evento_google(_amanha(11), _amanha(13)), "id": "b", "summary": "Dentista"},
    ]

    mensagem = visualizar.montar_mensagem(
        _resultado_visualizacao(eventos, inicio, fim)
    )

    assert mensagem.startswith("Avaliei o período de")
    assert "Horários ocupados:" in mensagem
    assert f"- Aula: {_amanha(10):%d/%m %H:%M} até {_amanha(12):%d/%m %H:%M}" in mensagem
    assert "Você possui compromissos conflitantes:" in mensagem
    assert f"- Aula x Dentista: {_amanha(11):%d/%m %H:%M} até {_amanha(12):%d/%m %H:%M}" in mensagem
    assert "Evento de dia inteiro:" not in mensagem


def test_visualizar_mensagem_dia_inteiro_e_sem_conflitos():
    inicio, fim = _amanha(0), _amanha(0) + timedelta(days=1)
    dia = inicio.date()
    feriado = {
        "id": "f",
        "summary": "Feriado",
        "start": {"date": dia.isoformat()},
        "end": {"date": (dia + timedelta(days=1)).isoformat()},
    }

    mensagem = visualizar.montar_mensagem(
        _resultado_visualizacao([feriado], inicio, fim)
    )

    assert "Evento de dia inteiro:" in mensagem
    assert f"- Feriado ({dia:%d/%m})" in mensagem
    assert "conflitantes" not in mensagem


@pytest.mark.parametrize(
    "minutos, esperado",
    [(0, "cheia"), (60, "cheia"), (61, "média"), (240, "média"), (241, "livre")],
)
def test_classificar_agenda(minutos, esperado):
    assert visualizar.classificar_agenda(minutos) == esperado


# ----------------------------------------------------------- extrair_json


@pytest.mark.parametrize(
    "texto",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '```\n{"a": 1}\n```',
        'Claro! Aqui está: {"a": 1} Espero ter ajudado.',
    ],
)
def test_extrair_json_aceita_respostas_do_modelo(texto):
    assert extrair_json(texto) == {"a": 1}


def test_extrair_json_rejeita_texto_sem_json():
    with pytest.raises(ValueError):
        extrair_json("não entendi")
