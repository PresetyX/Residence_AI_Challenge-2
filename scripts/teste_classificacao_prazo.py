"""Cenarios de prazo sem Google/Ollama. Executar: python -m scripts.teste_classificacao_prazo"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from destrava.agents.supervisor import AgenteSupervisor
from destrava.core import config


def montar_supervisor(minutos_livres: int):
    inicio = datetime.now(config.FUSO).replace(
        hour=6, minute=0, second=0, microsecond=0,
    ) + timedelta(days=1)
    fim = inicio + timedelta(minutes=minutos_livres)
    criador = MagicMock()
    supervisor = AgenteSupervisor(
        planejador=MagicMock(), visualizador=MagicMock(), criador=criador,
    )
    supervisor.consultar_periodos_projeto = MagicMock(return_value={
        "status": "sucesso",
        "dados": {
            "tarefas": [
                {"etapa": i, "titulo": titulo}
                for i, titulo in enumerate(("Criar HTML", "Estilizar CSS", "Testar site"))
            ],
            "livres": [{"inicio": inicio.isoformat(), "fim": fim.isoformat()}],
        },
    })
    return supervisor, criador


def main():
    cenarios = [
        (360, "tranquilo", 70),
        (300, "corrido", 60),
        (270, "impossivel", None),
    ]
    for minutos, esperado, duracao_esperada in cenarios:
        supervisor, criador = montar_supervisor(minutos)
        resposta = supervisor.preparar_agendamento("2099-12-31")
        assert resposta["classificacao"] == esperado, resposta
        if esperado == "impossivel":
            assert resposta["status"] == "erro"
            assert resposta["dados"]["minutos_faltantes_minimos"] == 30
            assert supervisor.cronograma_pendente is None
        else:
            assert resposta["status"] == "confirmacao"
            eventos = resposta["dados"]["eventos"]
            assert len(eventos) == 3
            for evento in eventos:
                inicio = datetime.fromisoformat(evento["inicio"])
                fim = datetime.fromisoformat(evento["fim"])
                assert (fim - inicio).total_seconds() / 60 == duracao_esperada
                assert ("(Pomodoro)" in evento["titulo"]) == (esperado == "tranquilo")
            assert len(resposta["dados"]["pomodoros"]) == (3 if esperado == "tranquilo" else 0)
            assert supervisor.confirmar_agendamento(False)["status"] == "cancelado"
        criador.executar_json.assert_not_called()
        print(f"[OK] {esperado.upper()} ({minutos} minutos livres brutos)")
    print("3 cenarios aprovados; nenhum evento real foi criado.")


if __name__ == "__main__":
    main()
