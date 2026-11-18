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
# Cada story point (estimado pela rede neural) vale este tempo de trabalho efetivo.
MINUTOS_POR_STORY_POINT = TRABALHO_PADRAO_TAREFA_MINUTOS


def minutos_de_trabalho(tarefa: dict) -> int:
    """Trabalho efetivo da tarefa: story_points x MINUTOS_POR_STORY_POINT.

    Sem story points validos (tarefa antiga ou sem estimativa), vale
    TRABALHO_PADRAO_TAREFA_MINUTOS.
    """
    pontos = tarefa.get("story_points") if isinstance(tarefa, dict) else None
    if isinstance(pontos, int) and not isinstance(pontos, bool) and pontos > 0:
        return pontos * MINUTOS_POR_STORY_POINT
    return TRABALHO_PADRAO_TAREFA_MINUTOS


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
