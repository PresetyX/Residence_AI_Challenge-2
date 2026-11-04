"""Testes do contrato JSON dos agentes (sem Google e sem Ollama).

O Google Calendar é simulado com mocks e o LLM é bloqueado: os caminhos em
JSON (executar_json) não podem chamar o modelo. Rodam em qualquer máquina:

    python -m pytest tests/
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from destrava.agents import criar, visualizar
from destrava.core import config


def _amanha(hora: int) -> datetime:
    dia = datetime.now(config.FUSO).date() + timedelta(days=1)
    return datetime(dia.year, dia.month, dia.day, hora, tzinfo=config.FUSO)


def _evento_google(inicio: datetime, fim: datetime, titulo: str = "Reunião") -> dict:
    return {
        "id": "abc123",
        "summary": titulo,
        "htmlLink": "https://calendar.google.com/event?eid=abc123",
        "start": {"dateTime": inicio.isoformat()},
        "end": {"dateTime": fim.isoformat()},
    }


def _servico_que_cria(evento: dict) -> MagicMock:
    servico = MagicMock()
    servico.events.return_value.insert.return_value.execute.return_value = evento
    return servico


@pytest.fixture(autouse=True)
def sem_llm():
    """Falha o teste se algum caminho em JSON tentar chamar o LLM."""
    proibido = MagicMock(side_effect=AssertionError("o JSON não deve chamar o LLM"))
    with patch.object(criar, "perguntar", proibido), \
         patch.object(visualizar, "perguntar", proibido):
        yield proibido


# ---------------------------------------------------------------- criar


def test_criar_json_cria_evento_e_devolve_json(sem_llm):
    inicio, fim = _amanha(14), _amanha(15)
    servico = _servico_que_cria(_evento_google(inicio, fim))
    entrada = {"titulo": " Reunião ", "inicio": inicio.isoformat(), "fim": fim.isoformat()}

    with patch.object(criar, "get_service", return_value=servico):
        saida = criar.AgenteCriar().executar_json(entrada)

    assert saida == {
        "evento": {
            "id": "abc123",
            "titulo": "Reunião",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "link": "https://calendar.google.com/event?eid=abc123",
        }
    }
    json.dumps(saida)  # a saída é serializável
    sem_llm.assert_not_called()

    corpo = servico.events.return_value.insert.call_args.kwargs["body"]
    assert corpo["summary"] == "Reunião"  # título sem espaços sobrando
    assert corpo["start"]["dateTime"] == inicio.isoformat()


def test_criar_json_aceita_texto_json_e_data_sem_fuso():
    inicio, fim = _amanha(9), _amanha(10)
    servico = _servico_que_cria(_evento_google(inicio, fim, "Estudar"))
    entrada = json.dumps(
        {"titulo": "Estudar", "inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
         "fim": fim.strftime("%Y-%m-%dT%H:%M")}
    )

    with patch.object(criar, "get_service", return_value=servico):
        saida = criar.AgenteCriar().executar_json(entrada)

    assert saida["evento"]["titulo"] == "Estudar"
    corpo = servico.events.return_value.insert.call_args.kwargs["body"]
    assert corpo["start"]["dateTime"] == inicio.isoformat()  # sem fuso = config.FUSO


@pytest.mark.parametrize(
    "entrada",
    [
        {"titulo": "  ", "inicio": "2099-01-01T10:00", "fim": "2099-01-01T11:00"},
        {"titulo": "X", "inicio": None, "fim": None},
        {"inicio": "2099-01-01T10:00", "fim": "2099-01-01T11:00"},
        {"titulo": "X", "inicio": "2099-01-01T11:00", "fim": "2099-01-01T10:00"},
        {"titulo": "X", "inicio": "2020-01-01T10:00", "fim": "2020-01-01T11:00"},
        {"titulo": "X", "inicio": "não é data", "fim": "2099-01-01T11:00"},
    ],
)
def test_criar_json_invalido_devolve_erro_e_nao_chama_google(entrada):
    get_service = MagicMock()

    with patch.object(criar, "get_service", get_service):
        saida = criar.AgenteCriar().executar_json(entrada)

    assert saida["erro"] == "Pedido inválido"
    assert saida["detalhes"]
    json.dumps(saida)  # o erro também é serializável
    get_service.assert_not_called()


def test_criar_json_texto_que_nao_e_json_devolve_erro():
    with patch.object(criar, "get_service", MagicMock()):
        saida = criar.AgenteCriar().executar_json("isso não é json")

    assert saida["erro"] == "Pedido inválido"


def test_criar_json_erro_do_google_propaga():
    inicio, fim = _amanha(14), _amanha(15)
    servico = _servico_que_cria({})  # a API não devolveu o id

    with patch.object(criar, "get_service", return_value=servico), \
         pytest.raises(RuntimeError):
        criar.AgenteCriar().executar_json(
            {"titulo": "X", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
        )


def test_validar_dados_evento_mantem_mensagens_em_valueerror():
    with pytest.raises(ValueError, match="título do evento é obrigatório"):
        criar.validar_dados_evento(
            {"titulo": "", "inicio": "2099-01-01T10:00", "fim": "2099-01-01T11:00"}
        )
    with pytest.raises(ValueError, match="passado"):
        criar.validar_dados_evento(
            {"titulo": "X", "inicio": "2020-01-01T10:00", "fim": "2020-01-01T11:00"}
        )


# ------------------------------------------------- criar: caminho em texto


def test_criar_por_texto_usa_llm_para_extrair_e_responder():
    inicio, fim = _amanha(14), _amanha(15)
    extracao = json.dumps(
        {"titulo": "Reunião", "inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
         "fim": fim.strftime("%Y-%m-%dT%H:%M")}
    )
    llm = MagicMock(side_effect=[f"```json\n{extracao}\n```", "Evento criado!"])
    servico = _servico_que_cria(_evento_google(inicio, fim))

    with patch.object(criar, "perguntar", llm), \
         patch.object(criar, "get_service", return_value=servico):
        resposta = criar.AgenteCriar().executar_por_texto("reunião amanhã 14h às 15h")

    assert resposta == "Evento criado!"
    assert llm.call_count == 2


def test_criar_por_texto_cancelado_nao_chama_google():
    inicio, fim = _amanha(9), _amanha(10)
    extracao = json.dumps(
        {"titulo": "Estudar", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
    )
    get_service = MagicMock()

    with patch.object(criar, "perguntar", MagicMock(return_value=extracao)), \
         patch.object(criar, "get_service", get_service):
        resposta = criar.AgenteCriar().executar_por_texto(
            "estudar amanhã", confirmar=lambda dados: False
        )

    assert "cancelada" in resposta
    get_service.assert_not_called()


def test_criar_por_texto_dados_incompletos_levanta_valueerror():
    extracao = '{"titulo": "Consulta médica", "inicio": null, "fim": null}'

    with patch.object(criar, "perguntar", MagicMock(return_value=extracao)), \
         patch.object(criar, "get_service", MagicMock()) as get_service, \
         pytest.raises(ValueError):
        criar.AgenteCriar().executar_por_texto("marque uma consulta")

    get_service.assert_not_called()


# ---------------------------------------------------------- visualizar


def test_visualizar_json_devolve_livres_sem_llm(sem_llm):
    inicio, fim = _amanha(0), _amanha(0) + timedelta(days=1)
    eventos = [_evento_google(_amanha(10), _amanha(11))]

    with patch.object(visualizar, "get_service"), \
         patch.object(visualizar, "listar_eventos", return_value=eventos):
        saida = visualizar.AgenteVisualizar().executar_json(
            {"inicio": inicio.isoformat(), "fim": fim.isoformat()}
        )

    assert set(saida) == {"livres", "total_minutos_livres"}
    assert saida["livres"]
    json.dumps(saida)
    sem_llm.assert_not_called()


def test_visualizar_json_invalido_devolve_erro():
    saida = visualizar.AgenteVisualizar().executar_json({"inicio": "xxx"})

    assert saida["erro"] == "Pedido inválido"
