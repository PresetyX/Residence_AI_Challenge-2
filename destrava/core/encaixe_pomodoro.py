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


def _descricao_planejamento(
    tarefa: dict,
    minutos_trabalho: int,
    titulos_por_etapa: dict
) -> str:
    """Monta a descrição do evento com os dados do Planejador."""

    titulo = tarefa["titulo"].strip()
    etapa = tarefa.get("etapa")

    if isinstance(etapa, int) and not isinstance(etapa, bool) and etapa >= 0:
        linhas = [f"Etapa {etapa} — {titulo}"]
    else:
        linhas = [f"Tarefa: {titulo}"]

    campos = (
        ("objetivo", "Objetivo"),
        ("entregaveis", "Entregáveis"),
        ("demonstracao", "Demonstração"),
    )

    for chave, rotulo in campos:
        valor = tarefa.get(chave)
        if isinstance(valor, str) and valor.strip():
            linhas.append(f"{rotulo}: {valor.strip()}")

    dependencia = tarefa.get("dependencia")

    if dependencia is None:
        linhas.append("Dependência: Não informada.")

    elif dependencia == 0:
        linhas.append("Dependência: Nenhuma.")

    else:
        titulo_dependencia = titulos_por_etapa.get(dependencia)

        if titulo_dependencia:
            linhas.append(
                f"Dependência: Etapa {dependencia} — {titulo_dependencia}"
            )
        else:
            linhas.append(
                f"Dependência: Etapa {dependencia} (título não encontrado)"
            )

    linhas.append(f"Trabalho estimado: {minutos_trabalho} minutos.")
    return "\n".join(linhas)


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


def _maior_trabalho_que_cabe(
    inicio: datetime,
    limite: datetime,
    trabalho_restante: int,
    usar_pomodoro: bool,
) -> int:
    """Maior quantidade de foco que cabe até `limite`, incluindo as pausas.

    Reutiliza o Pomodoro original, sem alterar os ciclos. A busca binária
    encontra a quantidade máxima de foco, em minutos inteiros.
    """
    minutos_calendario = int((limite - inicio).total_seconds() // 60)
    if minutos_calendario <= 0:
        return 0
    if not usar_pomodoro:
        return min(trabalho_restante, minutos_calendario)

    menor, maior = 1, min(trabalho_restante, minutos_calendario)
    resposta = 0
    while menor <= maior:
        meio = (menor + maior) // 2
        sessoes = gerar_sessoes_pomodoro(inicio, meio)
        fim = datetime.fromisoformat(sessoes[-1]["fim"])
        if fim <= limite:
            resposta = meio
            menor = meio + 1
        else:
            maior = meio - 1
    return resposta


def encaixar_tarefas_pomodoro(
    tarefas: list[dict],
    livres: list[dict],
    *,
    agora: datetime | None = None,
    usar_pomodoro: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Distribui as etapas sequencialmente em uma ou várias janelas livres.

    Cada etapa pode virar vários eventos (até em dias diferentes). O Pomodoro
    é gerado novamente para cada parte. O tempo de pausa integra a duração
    ocupada no calendário, e 2h por dia permanecem disponíveis ao estudante.
    Não há intervalo obrigatório entre etapas.

    Sem efeitos colaterais: se uma etapa não couber até o prazo, lança
    SemEspacoPomodoro e não devolve um cronograma parcial ao Supervisor.
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
    janelas = [janela for janela in janelas if tempo_livre_por_dia[janela[0].date()] > reserva]

    # Uma única referência global impede inverter as etapas entre dias.
    ultimo_fim: datetime | None = None
    eventos: list[dict] = []
    detalhes: list[dict] = []

    titulos_por_etapa = {
    tarefa["etapa"]: tarefa["titulo"]
    for tarefa in tarefas
    if "etapa" in tarefa
}

    for tarefa in tarefas:
        titulo_tarefa = tarefa["titulo"]
        story_points = tarefa.get("story_points")
        if not isinstance(story_points, int):
            story_points = 0
        trabalho_total = minutos_de_trabalho(tarefa)
        trabalho_restante = trabalho_total
        partes: list[dict] = []

        # Cada etapa usa uma janela no máximo uma vez. Não reiniciamos
        # artificialmente o Pomodoro no mesmo intervalo para eliminar pausas.
        for janela in janelas:
            if trabalho_restante == 0:
                break
            dia = janela[0].date()
            inicio = _proximo_minuto(max(janela[0], agora, ultimo_fim or agora))
            saldo_utilizavel = (tempo_livre_por_dia[dia]
                                - tempo_agendado_por_dia[dia] - reserva)
            limite = min(janela[1], inicio + saldo_utilizavel)
            foco = _maior_trabalho_que_cabe(
                inicio, limite, trabalho_restante, usar_pomodoro,
            )
            if foco <= 0:
                continue

            if usar_pomodoro:
                sessoes = gerar_sessoes_pomodoro(inicio, foco)
                fim = datetime.fromisoformat(sessoes[-1]["fim"])
            else:
                sessoes = []
                fim = inicio + timedelta(minutes=foco)

            trabalho_restante -= foco
            partes.append({
                "inicio": inicio, "fim": fim,
                "foco": foco, "restante": trabalho_restante,
                "sessoes": sessoes,
            })
            tempo_agendado_por_dia[dia] += fim - inicio
            janela[0] = fim
            ultimo_fim = fim

        if trabalho_restante > 0:
            modo = "com Pomodoro" if usar_pomodoro else "sem Pomodoro"
            raise SemEspacoPomodoro(
                f"Nao ha horario suficiente para '{titulo_tarefa}' {modo}, "
                f"mantendo {int(reserva.total_seconds() / 60)} minutos "
                "livres por dia. Nenhum evento foi criado."
            )

        # Sabemos a quantidade de partes apenas depois de terminar a etapa.
        qtd_partes = len(partes)
        for numero, parte in enumerate(partes, start=1):
            sufixo_parte = f" - Parte {numero}/{qtd_partes}" if qtd_partes > 1 else ""
            titulo = f"[Destrava] {titulo_tarefa}{sufixo_parte}"
            if usar_pomodoro:
                titulo += " (Pomodoro)"
            descricao = _descricao_planejamento(tarefa, trabalho_total, titulos_por_etapa)
            if qtd_partes > 1:
                descricao += (
                    f"\nParte {numero}/{qtd_partes}: {parte['foco']} minutos de trabalho nesta parte."
                    f"\nRestante da etapa após esta parte: {parte['restante']} minutos."
                )
            if usar_pomodoro:
                descricao += (
                    "\n\nTécnica Pomodoro: ciclos de até 25 minutos de foco com pausas.\n"
                    + _descricao_pomodoro(parte["sessoes"], parte["foco"])
                )
            else:
                descricao += (
                    "\n\nDestrava - Prazo corrido (sem tecnica Pomodoro)\n"
                    "Técnica Pomodoro: não utilizada. Sem pausas Pomodoro programadas."
                )
            eventos.append({
                "titulo": titulo,
                "inicio": parte["inicio"].isoformat(),
                "fim": parte["fim"].isoformat(),
                "descricao": descricao,
                "story_points": story_points,
            })
            if usar_pomodoro:
                detalhes.append({"titulo": titulo, "sessoes": parte["sessoes"]})

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
