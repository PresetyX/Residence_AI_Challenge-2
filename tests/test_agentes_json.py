"""Testes do contrato JSON dos agentes de criar e visualizar (sem Google).

O Google Calendar é simulado com mocks, então não precisam de credentials.json
nem de internet. Os agentes não usam LLM. Rodam em qualquer máquina:

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


# ---------------------------------------------------------------- criar


def test_criar_json_cria_evento_e_devolve_envelope_de_sucesso():
    inicio, fim = _amanha(14), _amanha(15)
    servico = _servico_que_cria(_evento_google(inicio, fim))
    entrada = {"titulo": " Reunião ", "inicio": inicio.isoformat(), "fim": fim.isoformat()}

    with patch.object(criar, "get_service", return_value=servico):
        saida = criar.AgenteCriar().executar_json(entrada)

    assert saida["status"] == "sucesso"
    assert saida["acao"] == "evento_criado"
    assert saida["periodo"]["duracao_minutos"] == 60
    assert saida["dados"] == {
        "evento": {
            "id": "abc123",
            "titulo": "Reunião",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "link": "https://calendar.google.com/event?eid=abc123",
        }
    }
    assert [saida["fluxo"][e]["status"] for e in ("inicio", "meio", "fim")] == ["ok"] * 3
    assert saida["fluxo"]["fim"]["detalhe"] == {"periodo_confere": True}
    assert saida["erro"] is None
    json.dumps(saida)  # a saída é serializável

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

    assert saida["status"] == "sucesso"
    assert saida["dados"]["evento"]["titulo"] == "Estudar"
    corpo = servico.events.return_value.insert.call_args.kwargs["body"]
    assert corpo["start"]["dateTime"] == inicio.isoformat()  # sem fuso = config.FUSO


def test_criar_json_avisa_quando_o_google_devolve_outro_periodo():
    inicio, fim = _amanha(14), _amanha(15)
    outro = _evento_google(_amanha(16), _amanha(17))  # o Google devolveu outro horário
    servico = _servico_que_cria(outro)

    with patch.object(criar, "get_service", return_value=servico):
        saida = criar.AgenteCriar().executar_json(
            {"titulo": "X", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
        )

    assert saida["status"] == "sucesso"
    assert saida["fluxo"]["fim"]["detalhe"] == {"periodo_confere": False}


@pytest.mark.parametrize(
    "entrada",
    [
        {"titulo": "  ", "inicio": "2099-01-01T10:00", "fim": "2099-01-01T11:00"},
        {"titulo": "X", "inicio": None, "fim": None},
        {"inicio": "2099-01-01T10:00", "fim": "2099-01-01T11:00"},
        {"titulo": "X", "inicio": "2099-01-01T11:00", "fim": "2099-01-01T10:00"},
        {"titulo": "X", "inicio": "2020-01-01T10:00", "fim": "2020-01-01T11:00"},
        {"titulo": "X", "inicio": "não é data", "fim": "2099-01-01T11:00"},
        "isso não é json",
    ],
)
def test_criar_json_invalido_devolve_erro_e_nao_chama_google(entrada):
    get_service = MagicMock()

    with patch.object(criar, "get_service", get_service):
        saida = criar.AgenteCriar().executar_json(entrada)

    assert saida["status"] == "erro"
    assert saida["acao"] == "evento_nao_criado"
    assert saida["periodo"] is None
    assert saida["dados"] is None
    assert saida["fluxo"]["inicio"]["status"] == "erro"
    assert saida["fluxo"]["meio"]["status"] == "pendente"
    assert saida["fluxo"]["fim"]["status"] == "pendente"
    assert saida["erro"]["tipo"] == "ValidationError"
    json.dumps(saida)  # o erro também é serializável
    get_service.assert_not_called()


def test_criar_json_erro_do_google_vira_json():
    inicio, fim = _amanha(14), _amanha(15)
    servico = _servico_que_cria({})  # a API não devolveu o id

    with patch.object(criar, "get_service", return_value=servico):
        saida = criar.AgenteCriar().executar_json(
            {"titulo": "X", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
        )

    assert saida["status"] == "erro"
    assert saida["acao"] == "evento_nao_criado"
    assert saida["periodo"] is not None  # o pedido era válido
    assert saida["dados"] is None
    assert saida["fluxo"]["inicio"]["status"] == "ok"
    assert saida["fluxo"]["meio"]["status"] == "erro"
    assert saida["fluxo"]["fim"]["status"] == "pendente"
    assert saida["erro"]["tipo"] == "RuntimeError"


def test_criar_json_falha_ao_conectar_no_google_vira_json():
    inicio, fim = _amanha(14), _amanha(15)

    with patch.object(criar, "get_service", side_effect=RuntimeError("sem credencial")):
        saida = criar.AgenteCriar().executar_json(
            {"titulo": "X", "inicio": inicio.isoformat(), "fim": fim.isoformat()}
        )

    assert saida["status"] == "erro"
    assert saida["fluxo"]["meio"]["status"] == "erro"
    assert saida["erro"]["mensagem"] == "sem credencial"


def test_validar_dados_evento_mantem_mensagens_em_valueerror():
    with pytest.raises(ValueError, match="título do evento é obrigatório"):
        criar.validar_dados_evento(
            {"titulo": "", "inicio": "2099-01-01T10:00", "fim": "2099-01-01T11:00"}
        )
    with pytest.raises(ValueError, match="passado"):
        criar.validar_dados_evento(
            {"titulo": "X", "inicio": "2020-01-01T10:00", "fim": "2020-01-01T11:00"}
        )


# ---------------------------------------------------------- visualizar


def test_agentes_nao_usam_llm():
    assert not hasattr(criar, "perguntar")
    assert not hasattr(visualizar, "perguntar")


def test_visualizar_json_devolve_envelope_de_sucesso():
    inicio, fim = _amanha(0), _amanha(0) + timedelta(days=1)
    eventos = [_evento_google(_amanha(10), _amanha(11))]

    with patch.object(visualizar, "get_service"), \
         patch.object(visualizar, "listar_eventos", return_value=eventos):
        saida = visualizar.AgenteVisualizar().executar_json(
            {"inicio": inicio.isoformat(), "fim": fim.isoformat()}
        )

    assert saida["status"] == "sucesso"
    assert saida["acao"] == "agenda_visualizada"
    assert saida["periodo"]["duracao_minutos"] == 1440
    assert set(saida["dados"]) == {"livres", "total_minutos_livres"}
    assert saida["dados"]["livres"]
    assert [saida["fluxo"][e]["status"] for e in ("inicio", "meio", "fim")] == ["ok"] * 3
    assert saida["erro"] is None
    json.dumps(saida)  # a saída é serializável


def test_visualizar_json_inicio_igual_ao_fim_vira_dia_inteiro():
    dia = _amanha(0).date().isoformat()

    with patch.object(visualizar, "get_service"), \
         patch.object(visualizar, "listar_eventos", return_value=[]):
        saida = visualizar.AgenteVisualizar().executar_json({"inicio": dia, "fim": dia})

    assert saida["status"] == "sucesso"
    assert saida["periodo"]["duracao_minutos"] == 1440


@pytest.mark.parametrize(
    "entrada",
    [
        {"inicio": "xxx"},
        {"inicio": "2026-11-05", "fim": "2026-11-04"},                  # fim antes do início
        {"inicio": "2026-11-05T00:00:00-03:00", "fim": "2026-11-06"},   # fuso só de um lado
        "isso não é json",
    ],
)
def test_visualizar_json_invalido_devolve_erro_na_validacao(entrada):
    get_service = MagicMock()

    with patch.object(visualizar, "get_service", get_service):
        saida = visualizar.AgenteVisualizar().executar_json(entrada)

    assert saida["status"] == "erro"
    assert saida["acao"] == "agenda_nao_visualizada"
    assert saida["periodo"] is None
    assert saida["dados"] is None
    assert saida["fluxo"]["inicio"]["status"] == "erro"
    assert saida["fluxo"]["meio"]["status"] == "pendente"
    json.dumps(saida)
    get_service.assert_not_called()


def test_visualizar_json_erro_do_google_vira_json():
    with patch.object(visualizar, "get_service", side_effect=RuntimeError("sem credencial")):
        saida = visualizar.AgenteVisualizar().executar_json(
            {"inicio": "2026-11-05", "fim": "2026-11-05"}
        )

    assert saida["status"] == "erro"
    assert saida["periodo"] is not None
    assert saida["fluxo"]["meio"]["status"] == "erro"
    assert saida["fluxo"]["fim"]["status"] == "pendente"
    assert saida["erro"]["tipo"] == "RuntimeError"
    
