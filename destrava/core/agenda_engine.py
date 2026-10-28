"""
Motor de cálculo da agenda: ocupados, livres e conflitos.

Fica no core (e não em um agente) porque pode ser reaproveitado por mais de
um agente (ex.: o de criar pode checar conflitos antes de marcar um evento).

Usa os valores de config.py:
    FUSO, HORARIO_ACORDAR, HORARIO_DORMIR, DURACAO_MINIMA_LIVRE,
    DIA_INTEIRO_BLOQUEIA

Não chama APIs nem LLM: só recebe eventos e devolve cálculos.
"""

from datetime import date, datetime, time, timedelta

from destrava.core import config
from destrava.core.models import Bloco, Conflito, HorarioLivre, Visualizacao


def normalizar_fuso(momento: datetime) -> datetime:
    """Coloca a data no fuso do projeto (config.FUSO).

    Datas sem fuso são consideradas já no horário de config.FUSO.
    Datas com fuso (ex.: UTC, vindas do Google) são convertidas para ele.
    """
    if momento.tzinfo is None:
        return momento.replace(tzinfo=config.FUSO)
    return momento.astimezone(config.FUSO)


def _no_dia(dia: date, horario: time) -> datetime:
    """Junta um dia e um horário em um datetime no fuso do projeto."""
    return datetime.combine(dia, horario, tzinfo=config.FUSO)


def _recortar(bloco: Bloco, inicio: datetime, fim: datetime) -> Bloco | None:
    """Corta o bloco para caber no período. Devolve None se ficar fora dele."""
    novo_inicio = max(bloco.inicio, inicio)
    novo_fim = min(bloco.fim, fim)

    if novo_inicio >= novo_fim:
        return None

    return bloco.model_copy(update={"inicio": novo_inicio, "fim": novo_fim})


def unir_blocos(blocos: list[Bloco]) -> list[Bloco]:
    """Junta blocos que se sobrepõem ou se encostam em um bloco só.

    Usado para calcular livres e o total ocupado sem contar tempo duas vezes.
    """
    ordenados = sorted(blocos, key=lambda bloco: bloco.inicio)
    unidos: list[Bloco] = []

    for bloco in ordenados:
        if unidos and bloco.inicio <= unidos[-1].fim:
            unidos[-1].fim = max(unidos[-1].fim, bloco.fim)
        else:
            unidos.append(bloco.model_copy())

    return unidos


def gerar_blocos_sono(inicio: datetime, fim: datetime) -> list[Bloco]:
    """Cria os blocos de sono que caem dentro do período.

    Começa um dia antes do início para incluir a madrugada do primeiro dia
    (ex.: dormir 22h e acordar 6h gera o bloco da noite anterior até as 6h).
    Os blocos são cortados para não passar do período pedido.
    """
    inicio = normalizar_fuso(inicio)
    fim = normalizar_fuso(fim)
    sono_cruza_meia_noite = config.HORARIO_DORMIR > config.HORARIO_ACORDAR

    blocos: list[Bloco] = []
    dia = inicio.date() - timedelta(days=1)

    while dia <= fim.date():
        inicio_sono = _no_dia(dia, config.HORARIO_DORMIR)

        if sono_cruza_meia_noite:
            fim_sono = _no_dia(dia + timedelta(days=1), config.HORARIO_ACORDAR)
        else:
            fim_sono = _no_dia(dia, config.HORARIO_ACORDAR)

        bloco = _recortar(
            Bloco(
                id=f"sono-{dia.isoformat()}",
                titulo="Sono",
                inicio=inicio_sono,
                fim=fim_sono,
                tipo="sono",
            ),
            inicio,
            fim,
        )

        if bloco is not None:
            blocos.append(bloco)

        dia += timedelta(days=1)

    return blocos


def calcular_horarios_livres(
    ocupados: list[Bloco],
    inicio: datetime,
    fim: datetime,
    duracao_minima: timedelta = config.DURACAO_MINIMA_LIVRE,
) -> list[HorarioLivre]:
    """Devolve as lacunas entre os ocupados, dentro do período.

    Só entram lacunas com pelo menos ``duracao_minima``.
    """
    inicio = normalizar_fuso(inicio)
    fim = normalizar_fuso(fim)

    livres: list[HorarioLivre] = []
    cursor = inicio

    for bloco in unir_blocos(ocupados):
        if bloco.inicio > cursor and bloco.inicio - cursor >= duracao_minima:
            livres.append(
                HorarioLivre(
                    inicio=cursor,
                    fim=bloco.inicio,
                    duracao_minutos=(bloco.inicio - cursor).total_seconds() / 60,
                )
            )

        cursor = max(cursor, bloco.fim)

    if fim > cursor and fim - cursor >= duracao_minima:
        livres.append(
            HorarioLivre(
                inicio=cursor,
                fim=fim,
                duracao_minutos=(fim - cursor).total_seconds() / 60,
            )
        )

    return livres


def encontrar_conflitos(eventos: list[Bloco]) -> list[Conflito]:
    """Devolve os pares de eventos que se sobrepõem.

    Dois eventos A e B conflitam quando inicio_A < fim_B e inicio_B < fim_A.
    O sono não entra aqui: um evento durante o sono não é conflito.
    """
    conflitos: list[Conflito] = []

    for indice, primeiro in enumerate(eventos):
        for segundo in eventos[indice + 1:]:
            if primeiro.inicio < segundo.fim and segundo.inicio < primeiro.fim:
                conflitos.append(
                    Conflito(
                        ids_eventos=[primeiro.id, segundo.id],
                        inicio_sobreposicao=max(primeiro.inicio, segundo.inicio),
                        fim_sobreposicao=min(primeiro.fim, segundo.fim),
                    )
                )

    return conflitos


def montar_visualizacao(
    eventos: list[dict],
    inicio: datetime,
    fim: datetime,
) -> Visualizacao:
    """Calcula ocupados, livres e conflitos de um período.

    Args:
        eventos: lista de dicionários com as chaves de ``Bloco``
            (id, titulo, inicio, fim e, opcionalmente, tipo).
        inicio: começo do período.
        fim: fim do período.

    Returns:
        Visualizacao com:
            - ocupados: cada evento e cada bloco de sono, separados e em ordem
              (eventos sobrepostos continuam aparecendo cada um com seu título);
              eventos de dia inteiro sempre aparecem aqui, com tipo "dia_inteiro";
            - livres: lacunas com pelo menos DURACAO_MINIMA_LIVRE;
            - conflitos: pares de eventos sobrepostos;
            - totais em minutos (sem contar tempo sobreposto duas vezes).

        Eventos de dia inteiro só tiram horários livres, geram conflitos e
        entram no total ocupado se config.DIA_INTEIRO_BLOQUEIA for True.

    Raises:
        ValueError: se ``fim`` não for posterior a ``inicio``.
    """
    inicio = normalizar_fuso(inicio)
    fim = normalizar_fuso(fim)

    if fim <= inicio:
        raise ValueError("O fim do período deve ser posterior ao início.")

    blocos_eventos: list[Bloco] = []

    for evento in eventos:
        bloco = Bloco(**evento)
        bloco = bloco.model_copy(
            update={
                "inicio": normalizar_fuso(bloco.inicio),
                "fim": normalizar_fuso(bloco.fim),
            }
        )
        bloco = _recortar(bloco, inicio, fim)

        if bloco is not None:
            blocos_eventos.append(bloco)

    blocos_sono = gerar_blocos_sono(inicio, fim)
    ocupados = sorted(blocos_eventos + blocos_sono, key=lambda bloco: bloco.inicio)

    # Eventos que realmente ocupam horário (o de dia inteiro depende do config).
    eventos_que_bloqueiam = [
        bloco
        for bloco in blocos_eventos
        if bloco.tipo != "dia_inteiro" or config.DIA_INTEIRO_BLOQUEIA
    ]

    livres = calcular_horarios_livres(
        eventos_que_bloqueiam + blocos_sono, inicio, fim
    )
    conflitos = encontrar_conflitos(eventos_que_bloqueiam)

    total_livres = sum(livre.duracao_minutos for livre in livres)
    total_ocupados = sum(
        (bloco.fim - bloco.inicio).total_seconds() / 60
        for bloco in unir_blocos(eventos_que_bloqueiam + blocos_sono)
    )

    return Visualizacao(
        ocupados=ocupados,
        livres=livres,
        conflitos=conflitos,
        total_minutos_livres=total_livres,
        total_minutos_ocupados=total_ocupados,
    )
