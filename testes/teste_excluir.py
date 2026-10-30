"""Teste real: cria um evento descartável e manda o ID para o agente.

Execute na raiz do projeto: python -m testes.teste_excluir_por_id
"""
from datetime import datetime, timedelta, time

from destrava.agents.excluir import excluir_evento_agenda
from destrava.core import config
from destrava.core.google_client import get_service


def main() -> None:
    amanha = datetime.now(config.FUSO).date() + timedelta(days=1)
    inicio = datetime.combine(amanha, time(15, 0), tzinfo=config.FUSO)
    fim = inicio + timedelta(hours=1)

    servico = get_service([config.ESCOPO_CALENDARIO])
    evento = servico.events().insert(
        calendarId="primary",
        body={
            "summary": "TESTE EXCLUSAO SUPERVISOR",
            "start": {"dateTime": inicio.isoformat()},
            "end": {"dateTime": fim.isoformat()},
        },
    ).execute()

    id_evento = evento["id"]  # ID real: não usar nome nem ID inventado
    print("Evento de teste criado:", evento.get("summary"))
    print("ID do evento:", id_evento)

    resultado = excluir_evento_agenda(id_evento)
    print("Resposta do agente:", resultado)
    if not resultado["sucesso"]:
        print("ATENÇÃO: o evento de teste pode ter permanecido na agenda.")


if __name__ == "__main__":
    main()
