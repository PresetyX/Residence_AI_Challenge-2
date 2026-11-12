"""Planeja os intervalos de foco e pausa das tarefas do Destrava.

O tempo estimado da tarefa representa trabalho efetivo. As pausas
sao acrescentadas ao periodo reservado no Google Calendar.
"""

from datetime import datetime, timedelta

FOCO_MINUTOS = 25
PAUSA_CURTA_MINUTOS = 5
PAUSA_LONGA_MINUTOS = 15
CICLOS_PARA_PAUSA_LONGA = 4
TRABALHO_PADRAO_TAREFA_MINUTOS = 60  # Ate chegar a estimativa da rede neural.


def gerar_sessoes_pomodoro(inicio: datetime, minutos_trabalho: int) -> list[dict]:
    """Gera blocos ordenados de foco e pausa, sem pausa apos terminar a tarefa.

    O contador e reiniciado para cada tarefa; nao ha limitacao de horas por dia.
    """
    if not isinstance(minutos_trabalho, int) or isinstance(minutos_trabalho, bool) or minutos_trabalho <= 0:
        raise ValueError("O tempo de trabalho deve ser um inteiro positivo em minutos.")

    sessoes = []
    atual = inicio
    restante = minutos_trabalho
    ciclos = 0

    while restante > 0:
        minutos = min(FOCO_MINUTOS, restante)
        fim = atual + timedelta(minutes=minutos)
        sessoes.append({
            "tipo": "foco",
            "inicio": atual.isoformat(),
            "fim": fim.isoformat(),
            "duracao_minutos": minutos,
        })
        atual = fim
        restante -= minutos
        ciclos += 1

        # Pausa so entre blocos de trabalho. Apos cada 4 ciclos, pausa longa.
        if restante > 0:
            pausa = (PAUSA_LONGA_MINUTOS if ciclos % CICLOS_PARA_PAUSA_LONGA == 0
                     else PAUSA_CURTA_MINUTOS)
            fim = atual + timedelta(minutes=pausa)
            sessoes.append({
                "tipo": "pausa_longa" if pausa == PAUSA_LONGA_MINUTOS else "pausa_curta",
                "inicio": atual.isoformat(),
                "fim": fim.isoformat(),
                "duracao_minutos": pausa,
            })
            atual = fim

    return sessoes
