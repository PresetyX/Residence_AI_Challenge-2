"""Encaixe deterministico de tarefas Pomodoro nos horarios livres.

Regras:
- Preservar pelo menos MINIMO_LIVRE_DIA de tempo livre APOS agendar cada tarefa.
- Sem limite de horas fixo de projeto, desde que a reserva diaria seja preservada.
- Nao cria nada no Google; apenas devolve a previa.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from destrava.core import config
from destrava.core.pomodoro import gerar_sessoes_pomodoro, minutos_de_trabalho


class SemEspacoPomodoro(ValueError):
    """Nao foi possivel encaixar todas as tarefas antes do prazo."""


def _no_fuso(valor: datetime) -> datetime:
    return (valor.replace(tzinfo=config.FUSO) if valor.tzinfo is None
            else valor.astimezone(config.FUSO))


def _proximo_minuto(valor: datetime) -> datetime:
    if valor.second or valor.microsecond:
        return valor.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return valor


def periodo_acordado(dia) -> tuple[datetime, datetime]:
    """Do acordar do `dia` até a hora de dormir (no dia seguinte, se for após a meia-noite)."""
    acordar = datetime.combine(dia, config.HORARIO_ACORDAR, tzinfo=config.FUSO)
    dormir = datetime.combine(dia, config.HORARIO_DORMIR, tzinfo=config.FUSO)
    if dormir <= acordar:
        dormir += timedelta(days=1)
    return acordar, dormir


def _janelas_acordadas(livres: list[dict], agora: datetime) -> list[list[datetime]]:
    """Clipa blocos a partir de agora e separa por dia, entre acordar e dormir."""
    janelas = []
    for bloco in livres:
        inicio = _no_fuso(datetime.fromisoformat(bloco["inicio"]))
        fim = _no_fuso(datetime.fromisoformat(bloco["fim"]))
        if fim <= inicio:
            raise ValueError("Horario livre com fim anterior ao inicio.")
        inicio = max(inicio, agora)
        # Começa um dia antes: quem dorme depois da meia-noite (ex.: 01h) ainda
        # está no "dia" anterior até essa hora.
        dia = inicio.date() - timedelta(days=1)
        while dia <= fim.date():
            acordar, dormir = periodo_acordado(dia)
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
    usar_pomodoro: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Encaixa TODAS as tarefas ou dispara SemEspacoPomodoro.

    O trabalho de cada tarefa e story_points x MINUTOS_POR_STORY_POINT
    (60 min, pomodoro.py); sem story points, 60 min. Com Pomodoro, a tarefa
    ocupa esse trabalho + as pausas. Sem Pomodoro, apenas o trabalho.
    Ambos os modos preservam MINIMO_LIVRE_DIA, respeitam os compromissos
    e permitem tarefas consecutivas, sem gap obrigatorio.

    Nenhum evento e criado aqui: esta funcao apenas prepara uma previa.
    """
    if not tarefas:
        raise ValueError("Nenhuma tarefa recebida.")
    if not isinstance(usar_pomodoro, bool):
        raise TypeError("usar_pomodoro deve ser True ou False.")

    agora = _no_fuso(agora or datetime.now(config.FUSO))
    janelas = _janelas_acordadas(livres, agora)

    tempo_livre_por_dia = defaultdict(timedelta)
    for a, b in janelas:
        tempo_livre_por_dia[a.date()] += b - a

    tempo_agendado_por_dia = defaultdict(timedelta)
    reserva = config.MINIMO_LIVRE_DIA
    janelas = [janela for janela in janelas
               if tempo_livre_por_dia[janela[0].date()] > reserva]
    # Impede que uma etapa posterior seja agendada antes da anterior, mesmo em outro dia.
    ultimo_fim: datetime | None = None
    eventos, detalhes = [], []

    for tarefa in tarefas:
        titulo_tarefa = tarefa["titulo"]
        # Story points da rede neural x MINUTOS_POR_STORY_POINT (pomodoro.py).
        trabalho = minutos_de_trabalho(tarefa)
        for janela in janelas:
            dia = janela[0].date()
            inicio = max(janela[0], agora)
            if ultimo_fim is not None:
                inicio = max(inicio, ultimo_fim)
            inicio = _proximo_minuto(inicio)

            if usar_pomodoro:
                sessoes = gerar_sessoes_pomodoro(inicio, trabalho)
                fim = datetime.fromisoformat(sessoes[-1]["fim"])
                titulo = f"[Destrava] {titulo_tarefa} (Pomodoro)"
                descricao = _descricao_pomodoro(sessoes, trabalho)
            else:
                sessoes = []
                fim = inicio + timedelta(minutes=trabalho)
                titulo = f"[Destrava] {titulo_tarefa}"
                descricao = ("Destrava - Prazo corrido (sem tecnica Pomodoro)\\n"
                             f"Trabalho estimado: {trabalho} minutos. "
                             "Sem pausas Pomodoro programadas.")

            duracao_total = fim - inicio
            saldo_apos = (tempo_livre_por_dia[dia] -
                          tempo_agendado_por_dia[dia] - duracao_total)
            if fim <= janela[1] and saldo_apos >= reserva:
                eventos.append({
                    "titulo": titulo,
                    "inicio": inicio.isoformat(),
                    "fim": fim.isoformat(),
                    "descricao": descricao,
                })
                if usar_pomodoro:
                    detalhes.append({"titulo": titulo, "sessoes": sessoes})
                ultimo_fim = fim
                tempo_agendado_por_dia[dia] += duracao_total
                janela[0] = fim
                break
        else:
            modo = "com Pomodoro" if usar_pomodoro else "sem Pomodoro"
            raise SemEspacoPomodoro(
                f"Nao ha horario suficiente para '{titulo_tarefa}' {modo}, "
                f"mantendo {int(reserva.total_seconds() / 60)} minutos "
                "livres por dia. Nenhum evento foi criado."
            )
    return eventos, detalhes


def calcular_deficit_minimo(
    tarefas: list[dict],
    livres: list[dict],
    *,
    agora: datetime | None = None,
) -> int:
    """Retorna o deficit MINIMO, em minutos, sem pausas Pomodoro.

    Considera a soma de tempo utilizavel apos a reserva de cada dia.
    Se retornar zero e o encaixe falhar, o problema e a fragmentacao
    dos intervalos livres (o total por si so nao garante encaixe).
    """
    agora = _no_fuso(agora or datetime.now(config.FUSO))
    por_dia = defaultdict(timedelta)
    for inicio, fim in _janelas_acordadas(livres, agora):
        por_dia[inicio.date()] += fim - inicio

    minutos_disponiveis = sum(
        max(0, int((duracao - config.MINIMO_LIVRE_DIA).total_seconds() // 60))
        for duracao in por_dia.values()
    )
    minutos_necessarios = sum(minutos_de_trabalho(tarefa) for tarefa in tarefas)
    return max(0, minutos_necessarios - minutos_disponiveis)
