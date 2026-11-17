"""Encaixe deterministico de tarefas Pomodoro nos horarios livres.

Regras:
- Preservar pelo menos MINIMO_LIVRE_DIA de tempo livre APOS agendar cada tarefa.
- Sem limite de horas fixo de projeto, desde que a reserva diaria seja preservada.
- Nao cria nada no Google; apenas devolve a previa.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from destrava.core import config
from destrava.core.pomodoro import gerar_sessoes_pomodoro, TRABALHO_PADRAO_TAREFA_MINUTOS


class SemEspacoPomodoro(ValueError):
    """Nao foi possivel encaixar todas as tarefas antes do prazo."""


def _no_fuso(valor: datetime) -> datetime:
    return (valor.replace(tzinfo=config.FUSO) if valor.tzinfo is None
            else valor.astimezone(config.FUSO))


def _proximo_minuto(valor: datetime) -> datetime:
    if valor.second or valor.microsecond:
        return valor.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return valor


def _janelas_acordadas(livres: list[dict], agora: datetime) -> list[list[datetime]]:
    """Clipa blocos a partir de agora e separa por dia, entre acordar e dormir."""
    janelas = []
    for bloco in livres:
        inicio = _no_fuso(datetime.fromisoformat(bloco["inicio"]))
        fim = _no_fuso(datetime.fromisoformat(bloco["fim"]))
        if fim <= inicio:
            raise ValueError("Horario livre com fim anterior ao inicio.")
        inicio = max(inicio, agora)
        dia = inicio.date()
        while dia <= fim.date():
            acordar = datetime.combine(dia, config.HORARIO_ACORDAR, tzinfo=config.FUSO)
            dormir = datetime.combine(dia, config.HORARIO_DORMIR, tzinfo=config.FUSO)
            a, b = max(inicio, acordar), min(fim, dormir)
            if b > a:
                janelas.append([a, b])
            dia += timedelta(days=1)
    # Unir intervalos eventualmente sobrepostos (evita contar a mesma hora duas vezes).
    unidas = []
    for a, b in sorted(janelas, key=lambda item: item[0]):
        if unidas and a <= unidas[-1][1]:
            unidas[-1][1] = max(unidas[-1][1], b)
        else:
            unidas.append([a, b])
    return unidas


def _descricao_pomodoro(sessoes: list[dict], minutos_trabalho: int) -> str:
    pausa = sum(s["duracao_minutos"] for s in sessoes if s["tipo"] != "foco")
    linhas = [
        "Destrava - Tecnica Pomodoro",
        f"Trabalho efetivo: {minutos_trabalho} minutos | Pausas: {pausa} minutos",
        "Ciclos:",
    ]
    nomes = {"foco": "Foco", "pausa_curta": "Pausa curta", "pausa_longa": "Pausa longa"}
    for sessao in sessoes:
        a = datetime.fromisoformat(sessao["inicio"])
        b = datetime.fromisoformat(sessao["fim"])
        linhas.append(f"{a:%H:%M}-{b:%H:%M} | {nomes[sessao['tipo']]}")
    return "\n".join(linhas)


def encaixar_tarefas_pomodoro(
    tarefas: list[dict],
    livres: list[dict],
    *,
    agora: datetime | None = None,
) -> tuple[list[dict], list[dict]]:
    """Retorna (eventos, detalhes_pomodoro) ou dispara SemEspacoPomodoro.

    O minimo de 2h deve SOBRAR apos cada agendamento. O saldo diario soma
    as janelas livres do mesmo dia, descontando tarefas e suas pausas.
    Os gaps de 30min sao livres e nao contam como trabalho do projeto.
    """
    if not tarefas:
        raise ValueError("Nenhuma tarefa recebida.")
    agora = _no_fuso(agora or datetime.now(config.FUSO))
    janelas = _janelas_acordadas(livres, agora)

    # Cada minuto livre do dia e contado apenas uma vez, inclusive entre blocos.
    tempo_livre_por_dia = defaultdict(timedelta)
    for a, b in janelas:
        tempo_livre_por_dia[a.date()] += b - a

    # Tempo total efetivamente reservado para tarefas, incluindo pausas Pomodoro.
    tempo_agendado_por_dia = defaultdict(timedelta)
    reserva = config.MINIMO_LIVRE_DIA
    # Se ha menos de 2h antes de agendar, naturalmente nao cabe tarefa alguma.
    janelas = [janela for janela in janelas
               if tempo_livre_por_dia[janela[0].date()] > reserva]
    fim_ultimo_evento_por_dia: dict = {}
    eventos, detalhes = [], []

    for tarefa in tarefas:
        titulo_tarefa = tarefa["titulo"]
        # A estimativa da rede ainda nao chegou: 60min de trabalho efetivo.
        trabalho = TRABALHO_PADRAO_TAREFA_MINUTOS
        # Futuramente o Planejador enviara a duracao em minutos.
        for janela in janelas:
            dia = janela[0].date()
            inicio = max(janela[0], agora)
            anterior = fim_ultimo_evento_por_dia.get(dia)
            if anterior is not None:
                inicio = max(inicio, anterior)
            inicio = _proximo_minuto(inicio)
            sessoes = gerar_sessoes_pomodoro(inicio, trabalho)
            fim = datetime.fromisoformat(sessoes[-1]["fim"])
            duracao_total = fim - inicio  # Inclui todas as pausas Pomodoro.
            saldo_apos = (tempo_livre_por_dia[dia] -
                          tempo_agendado_por_dia[dia] - duracao_total)
            if fim <= janela[1] and saldo_apos >= reserva:
                titulo = f"[Destrava] {titulo_tarefa} (Pomodoro)"
                eventos.append({
                    "titulo": titulo,
                    "inicio": inicio.isoformat(),
                    "fim": fim.isoformat(),
                    "descricao": _descricao_pomodoro(sessoes, trabalho),
                })
                detalhes.append({"titulo": titulo, "sessoes": sessoes})
                fim_ultimo_evento_por_dia[dia] = fim
                tempo_agendado_por_dia[dia] += duracao_total
                janela[0] = fim  # Tarefa e pausas agora ocupam este bloco.
                break
        else:
            raise SemEspacoPomodoro(
                f"Nao ha horario suficiente para '{titulo_tarefa}' respeitando "
                f"a reserva de {int(reserva.total_seconds() / 60)} minutos livres "
                "APOS o agendamento e as pausas Pomodoro. "
                "Nenhum evento foi criado."
            )
    return eventos, detalhes
