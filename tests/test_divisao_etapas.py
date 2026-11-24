"""Divisão real de etapas (Google e Ollama NÃO são chamados nesses testes)."""

from collections import defaultdict
from datetime import datetime, timedelta, time
from unittest.mock import MagicMock

import pytest

from destrava.core import config
from destrava.core.encaixe_pomodoro import SemEspacoPomodoro, encaixar_tarefas_pomodoro

DATA = datetime(2026, 12, 3, 7, 0, tzinfo=config.FUSO)


def janela(dia, comeco=8, termino=13, minuto_comeco=0, minuto_termino=0):
    data = DATA.date() + timedelta(days=dia)
    a = datetime.combine(data, time(comeco, minuto_comeco), tzinfo=config.FUSO)
    b = datetime.combine(data, time(termino, minuto_termino), tzinfo=config.FUSO)
    return {"inicio": a.isoformat(), "fim": b.isoformat()}


def duracao(evento):
    return int((datetime.fromisoformat(evento["fim"]) - datetime.fromisoformat(evento["inicio"])).total_seconds() / 60)


def foco(sessoes):
    return sum(s["duracao_minutos"] for s in sessoes if s["tipo"] == "foco")


def por_dia(eventos):
    resultado = defaultdict(int)
    for evento in eventos:
        resultado[datetime.fromisoformat(evento["inicio"]).date()] += duracao(evento)
    return resultado


def tarefa(nome="Login", pontos=4):
    return {
        "etapa": 1, "titulo": nome, "story_points": pontos,
        "objetivo": "Permitir autenticação", "entregaveis": "Tela e rota",
        "demonstracao": "Fazer login",
    }


def test_etapa_de_4_horas_dividida_entre_dois_dias_com_pomodoro():
    eventos, detalhes = encaixar_tarefas_pomodoro(
        [tarefa()], [janela(1), janela(2)], agora=DATA,
    )
    assert len(eventos) == len(detalhes) == 2
    assert "Parte 1/2" in eventos[0]["titulo"]
    assert "Parte 2/2" in eventos[1]["titulo"]
    assert sum(foco(d["sessoes"]) for d in detalhes) == 240
    assert duracao(eventos[0]) == 180  # 145 min de foco + 35 de pausa
    assert foco(detalhes[0]["sessoes"]) == 145
    assert foco(detalhes[1]["sessoes"]) == 95
    assert datetime.fromisoformat(eventos[1]["inicio"]).date() > datetime.fromisoformat(eventos[0]["inicio"]).date()
    assert all(300 - minutos >= 120 for minutos in por_dia(eventos).values())


def test_descricao_informa_total_e_trabalho_de_cada_parte():
    eventos, detalhes = encaixar_tarefas_pomodoro(
        [tarefa()], [janela(1), janela(2)], agora=DATA,
    )
    for n, (evento, detalhe) in enumerate(zip(eventos, detalhes), 1):
        desc = evento["descricao"]
        assert "Etapa 1 — Login" in desc
        assert "Objetivo: Permitir autenticação" in desc
        assert "Entregáveis: Tela e rota" in desc
        assert "Demonstração: Fazer login" in desc
        assert "Trabalho estimado: 240 minutos." in desc
        assert f"Parte {n}/2:" in desc
        assert "Trabalho efetivo:" in desc
        assert "Ciclos:" in desc
        assert "Foco" in desc
        assert detalhe["titulo"] == evento["titulo"]


def test_com_pomodoro_nenhuma_parte_ultrapassa_a_janela():
    eventos, detalhes = encaixar_tarefas_pomodoro(
        [tarefa("API", 3)], [janela(1, 8, 12), janela(2, 8, 12)], agora=DATA,
    )
    assert sum(foco(x["sessoes"]) for x in detalhes) == 180
    assert all(duracao(e) <= 120 for e in eventos)  # 4h livres menos 2h de reserva


def test_sem_pomodoro_divide_180_minutos_e_depois_60():
    eventos, detalhes = encaixar_tarefas_pomodoro(
        [tarefa()], [janela(1), janela(2)], agora=DATA, usar_pomodoro=False,
    )
    assert detalhes == []
    assert [duracao(e) for e in eventos] == [180, 60]
    assert "Parte 1/2" in eventos[0]["titulo"]
    assert "Técnica Pomodoro: não utilizada" in eventos[1]["descricao"]


def test_proxima_etapa_so_comeca_depois_da_anterior():
    etapas = [tarefa("Primeira", 4), tarefa("Segunda", 3)]
    etapas[1]["etapa"] = 2
    eventos, detalhes = encaixar_tarefas_pomodoro(
        etapas, [janela(1), janela(2), janela(3), janela(4)], agora=DATA,
    )
    primeira = [e for e in eventos if "Primeira" in e["titulo"]]
    segunda = [e for e in eventos if "Segunda" in e["titulo"]]
    assert len(primeira) > 1
    assert len(segunda) >= 1
    assert sum(foco(d["sessoes"]) for d in detalhes if "Primeira" in d["titulo"]) == 240
    assert sum(foco(d["sessoes"]) for d in detalhes if "Segunda" in d["titulo"]) == 180
    assert datetime.fromisoformat(segunda[0]["inicio"]) >= datetime.fromisoformat(primeira[-1]["fim"])
    assert all(datetime.fromisoformat(a["fim"]) <= datetime.fromisoformat(b["inicio"])
               for a, b in zip(eventos, eventos[1:]))


def test_etapas_pequenas_podem_ser_consecutivas():
    eventos, _ = encaixar_tarefas_pomodoro(
        [tarefa("A", 1), tarefa("B", 1)], [janela(1, 8, 14)], agora=DATA,
    )
    assert len(eventos) == 2
    assert datetime.fromisoformat(eventos[1]["inicio"]) - datetime.fromisoformat(eventos[0]["fim"]) == timedelta(0)


def test_partes_da_mesma_etapa_nao_recebem_gap_extra():
    janelas = [
        janela(1, 8, 9),
        janela(1, 9, 12, minuto_comeco=10, minuto_termino=10),
        janela(2, 8, 13),
    ]
    eventos, _ = encaixar_tarefas_pomodoro([tarefa()], janelas, agora=DATA)
    assert len(eventos) >= 3
    # A segunda janela começa às 9h10; não se deve adicionar 30 minutos
    # entre partes da mesma tarefa.
    assert datetime.fromisoformat(eventos[1]["inicio"]).hour == 9
    assert datetime.fromisoformat(eventos[1]["inicio"]).minute == 10


def test_janelas_fora_de_ordem_nao_invertem_etapas():
    janelas = [janela(3), janela(1), janela(2)]
    eventos, _ = encaixar_tarefas_pomodoro([tarefa("A", 4), tarefa("B", 1)], janelas, agora=DATA)
    assert all(datetime.fromisoformat(a["fim"]) <= datetime.fromisoformat(b["inicio"])
               for a, b in zip(eventos, eventos[1:]))
    assert all("[Destrava] A" in evento["titulo"] for evento in eventos if "[Destrava] B" not in evento["titulo"])
    assert "[Destrava] B" in eventos[-1]["titulo"]


def test_mantem_2_horas_de_reserva_somando_janelas_do_dia():
    eventos, _ = encaixar_tarefas_pomodoro(
        [tarefa("Grande", 4)],
        [janela(1, 8, 10), janela(1, 14, 17), janela(2, 8, 13)],
        agora=DATA,
    )
    assert por_dia(eventos)[(DATA + timedelta(days=1)).date()] == 180


def test_nao_inventa_campos_para_tarefa_sem_metadados():
    eventos, _ = encaixar_tarefas_pomodoro(
        [{"titulo": "Revisar"}], [janela(1, 8, 13)], agora=DATA,
    )
    assert len(eventos) == 1
    assert duracao(eventos[0]) == 70
    assert "Tarefa: Revisar" in eventos[0]["descricao"]
    assert "Objetivo:" not in eventos[0]["descricao"]
    assert "Parte" not in eventos[0]["titulo"]


def test_sem_espaco_falha_sem_devolver_agendamento_parcial():
    with pytest.raises(SemEspacoPomodoro):
        encaixar_tarefas_pomodoro(
            [tarefa("Grande demais", 8)], [janela(1, 8, 12)], agora=DATA,
        )


def test_classificacao_supervisor_reaproveita_tranquilo_corrido_impossivel():
    from destrava.agents.supervisor import AgenteSupervisor
    de_hoje = datetime.now(config.FUSO)
    d1 = (de_hoje + timedelta(days=2)).date()
    d2 = d1 + timedelta(days=1)

    def livre(dia, h1, h2):
        a = datetime.combine(dia, time(h1), tzinfo=config.FUSO)
        b = datetime.combine(dia, time(h2), tzinfo=config.FUSO)
        return {"inicio": a.isoformat(), "fim": b.isoformat()}

    def classificar(janelas):
        sup = AgenteSupervisor(visualizador=MagicMock(), criador=MagicMock())
        sup.consultar_periodos_projeto = MagicMock(return_value={
            "status": "sucesso", "dados": {
                "tarefas": [tarefa("Login", 3)],
                "livres": janelas,
            },
        })
        resp = sup.preparar_agendamento("Site", d2.isoformat())
        return resp, sup

    tranquilo, sup = classificar([livre(d1, 8, 13), livre(d2, 8, 13)])
    assert tranquilo["classificacao"] == "tranquilo"
    assert len(tranquilo["dados"]["eventos"]) == 2
    assert sup.criador.executar_json.call_count == 0

    corrido, sup = classificar([livre(d1, 8, 13)])
    assert corrido["classificacao"] == "corrido"
    assert len(corrido["dados"]["eventos"]) == 1
    assert sup.criador.executar_json.call_count == 0

    impossivel, sup = classificar([livre(d1, 8, 12)])
    assert impossivel["classificacao"] == "impossivel"
    assert impossivel["dados"]["eventos"] == []
    assert sup.criador.executar_json.call_count == 0


def test_nao_reinicia_pomodoro_na_mesma_janela_para_eliminar_pausas():
    # 150 minutos livres - 120 de reserva = 30 minutos disponíveis.
    # 25 minutos de foco cabem; os 5 restantes não viram outro evento
    # consecutivo da mesma etapa para burlar a pausa.
    eventos, detalhes = encaixar_tarefas_pomodoro(
        [tarefa("Login", 1)],
        [janela(1, 8, 10, minuto_termino=30), janela(2, 8, 13)], agora=DATA,
    )
    assert len(eventos) == 2
    assert foco(detalhes[0]["sessoes"]) == 25
    assert foco(detalhes[1]["sessoes"]) == 35


def test_confirmacao_de_parte_curta_consulta_ocupados():
    from destrava.agents.supervisor import AgenteSupervisor
    sup = AgenteSupervisor(visualizador=MagicMock(), criador=MagicMock())
    evento = janela(1, 8, 8, minuto_termino=15)
    sup.visualizador.executar_json.return_value = {
        "status": "sucesso", "dados": {"livres": [], "ocupados": []},
    }
    assert sup.verificar_disponibilidade(evento)
    sup.visualizador.executar_json.assert_called_with(evento, incluir_ocupados=True)
    sup.visualizador.executar_json.return_value["dados"]["ocupados"] = [
        {"tipo": "evento", **evento},
    ]
    assert not sup.verificar_disponibilidade(evento)
    sup.visualizador.executar_json.return_value = {"status": "erro"}
    assert not sup.verificar_disponibilidade(evento)
