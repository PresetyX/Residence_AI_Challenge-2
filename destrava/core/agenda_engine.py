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

    Args:
        momento: data a normalizar. Sem fuso, é considerada já no horário de
            config.FUSO (ex.: 09:00 vira 09:00 -03:00). Com fuso (ex.: UTC,
            vinda do Google), é convertida (12:00 UTC vira 09:00 -03:00).

    Returns:
        A mesma data, com o fuso de config.FUSO.

    Raises:
        Nenhuma exceção própria.
    """
    if momento.tzinfo is None:
        # Sem fuso: só "carimba" São Paulo, sem mudar a hora (09:00 -> 09:00 -03:00).
        return momento.replace(tzinfo=config.FUSO)
    # Com fuso: converte a hora (12:00 UTC -> 09:00 -03:00).
    return momento.astimezone(config.FUSO)


def _no_dia(dia: date, horario: time) -> datetime:
    """Junta um dia e um horário em um datetime no fuso do projeto.

    Args:
        dia: a data (ex.: 29/10/2026).
        horario: a hora do dia (ex.: 22:00).

    Returns:
        Data e hora juntas, no fuso de config.FUSO (ex.: 29/10/2026 22:00 -03:00).

    Raises:
        Nenhuma exceção própria.
    """
    return datetime.combine(dia, horario, tzinfo=config.FUSO)


def _recortar(bloco: Bloco, inicio: datetime, fim: datetime) -> Bloco | None:
    """Corta o bloco para caber dentro do período.

    Args:
        bloco: o intervalo a recortar (evento ou sono).
        inicio: começo do período.
        fim: fim do período.

    Returns:
        Uma cópia do bloco só com a parte que fica dentro do período, ou
        None se o bloco estiver todo fora dele.

    Raises:
        Nenhuma exceção própria.
    """
    # O início mais tarde e o fim mais cedo = a parte que fica dentro do período.
    novo_inicio = max(bloco.inicio, inicio)
    novo_fim = min(bloco.fim, fim)

    # Não sobrou nada: o bloco está todo fora do período.
    if novo_inicio >= novo_fim:
        return None

    return bloco.model_copy(update={"inicio": novo_inicio, "fim": novo_fim})


def unir_blocos(blocos: list[Bloco]) -> list[Bloco]:
    """Junta blocos que se sobrepõem ou se encostam em um bloco só.

    Usado para calcular livres e o total ocupado sem contar tempo duas vezes.
    Ex.: Reunião 09:00–10:00 e Dentista 09:30–10:30 viram um bloco 09:00–10:30.

    Args:
        blocos: blocos em qualquer ordem. A lista original não é alterada.

    Returns:
        Nova lista de blocos, em ordem de início, sem sobreposições.

    Raises:
        Nenhuma exceção própria.
    """
    ordenados = sorted(blocos, key=lambda bloco: bloco.inicio)
    unidos: list[Bloco] = []

    for bloco in ordenados:
        if unidos and bloco.inicio <= unidos[-1].fim:
            # Encosta ou sobrepõe o último bloco: estica o último até o fim deste.
            unidos[-1].fim = max(unidos[-1].fim, bloco.fim)
        else:
            # Não encosta: começa um bloco novo (cópia, para não alterar o original).
            unidos.append(bloco.model_copy())

    return unidos


def gerar_blocos_sono(inicio: datetime, fim: datetime) -> list[Bloco]:
    """Cria os blocos de sono que caem dentro do período.

    Usa config.HORARIO_DORMIR e config.HORARIO_ACORDAR. Começa um dia antes
    do início para incluir a madrugada do primeiro dia (ex.: dormir 22h e
    acordar 6h gera o bloco da noite anterior até as 6h). Os blocos são
    cortados para não passar do período pedido.

    Args:
        inicio: começo do período.
        fim: fim do período.

    Returns:
        Lista de blocos com tipo "sono", um por noite, em ordem.

    Raises:
        Nenhuma exceção própria.
    """
    inicio = normalizar_fuso(inicio)
    fim = normalizar_fuso(fim)
    # Ex.: dormir 22h e acordar 6h -> o sono termina no dia seguinte.
    sono_cruza_meia_noite = config.HORARIO_DORMIR > config.HORARIO_ACORDAR

    blocos: list[Bloco] = []
    # Começa um dia ANTES: o sono da madrugada do 1º dia começou na noite anterior.
    dia = inicio.date() - timedelta(days=1)

    # Um bloco de sono por noite, até o último dia do período.
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

        # Só guarda a noite se alguma parte dela cair dentro do período.
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
    """Devolve as lacunas entre os blocos ocupados, dentro do período.

    Percorre o período com um "cursor" e registra cada espaço vazio entre
    um bloco e o próximo. Só entram lacunas com pelo menos ``duracao_minima``.

    Args:
        ocupados: blocos que ocupam horário (eventos e sono), em qualquer ordem.
        inicio: começo do período.
        fim: fim do período.
        duracao_minima: menor lacuna que conta como livre. Padrão:
            config.DURACAO_MINIMA_LIVRE (30 minutos).

    Returns:
        Lista de HorarioLivre (início, fim e duração em minutos), em ordem.

    Raises:
        Nenhuma exceção própria.
    """
    inicio = normalizar_fuso(inicio)
    fim = normalizar_fuso(fim)

    livres: list[HorarioLivre] = []
    # O cursor marca até onde o período já foi verificado. Começa no início.
    cursor = inicio

    # Percorre os blocos ocupados (já unidos e em ordem).
    for bloco in unir_blocos(ocupados):
        # Há espaço entre o cursor e o próximo bloco? Se tiver o mínimo, é livre.
        if bloco.inicio > cursor and bloco.inicio - cursor >= duracao_minima:
            livres.append(
                HorarioLivre(
                    inicio=cursor,
                    fim=bloco.inicio,
                    duracao_minutos=(bloco.inicio - cursor).total_seconds() / 60,
                )
            )

        # Pula o cursor para o fim do bloco (o max impede que ele volte).
        cursor = max(cursor, bloco.fim)

    # Sobrou tempo livre entre o último bloco e o fim do período?
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

    Args:
        eventos: blocos de eventos que ocupam horário (sem o sono).

    Returns:
        Lista de Conflito, cada um com os ids dos dois eventos e o trecho em
        que se sobrepõem (do início mais tarde ao fim mais cedo).

    Raises:
        Nenhuma exceção própria.
    """
    conflitos: list[Conflito] = []

    # Compara cada par de eventos uma única vez (A x B, sem repetir B x A).
    for indice, primeiro in enumerate(eventos):
        for segundo in eventos[indice + 1:]:
            # Regra da sobreposição: um começa antes de o outro terminar, e vice-versa.
            if primeiro.inicio < segundo.fim and segundo.inicio < primeiro.fim:
                # O trecho em conflito vai do início mais tarde ao fim mais cedo.
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
        pydantic.ValidationError: se algum evento vier sem um campo
            obrigatório do Bloco (ex.: sem ``inicio``).
    """
    # 1. Coloca o período no fuso do projeto e valida.
    inicio = normalizar_fuso(inicio)
    fim = normalizar_fuso(fim)

    if fim <= inicio:
        raise ValueError("O fim do período deve ser posterior ao início.")

    # 2. Converte cada evento em Bloco, no fuso do projeto e recortado no período.
    blocos_eventos: list[Bloco] = []

    for evento in eventos:
        bloco = Bloco(**evento) # cada chave do evento vira um parâmetro para o Bloco
        bloco = bloco.model_copy(
            update={
                "inicio": normalizar_fuso(bloco.inicio),
                "fim": normalizar_fuso(bloco.fim),
            }
        )
        bloco = _recortar(bloco, inicio, fim)

        if bloco is not None:
            blocos_eventos.append(bloco)

    # 3. Cria o sono de cada noite do período.
    blocos_sono = gerar_blocos_sono(inicio, fim)

    # 4. Lista para MOSTRAR: todos os eventos e o sono, em ordem de início.
    ocupados = sorted(blocos_eventos + blocos_sono, key=lambda bloco: bloco.inicio)

    # 5. Lista para CALCULAR: eventos que realmente ocupam horário
    #    (o de dia inteiro só entra se config.DIA_INTEIRO_BLOQUEIA for True).
    eventos_que_bloqueiam = [
        bloco
        for bloco in blocos_eventos
        if bloco.tipo != "dia_inteiro" or config.DIA_INTEIRO_BLOQUEIA
    ]

    # 6. Horários livres e conflitos (o sono e os dias inteiros não geram conflito).
    livres = calcular_horarios_livres(
        eventos_que_bloqueiam + blocos_sono, inicio, fim
    )
    conflitos = encontrar_conflitos(eventos_que_bloqueiam)

    # 7. Totais em minutos. O ocupado usa os blocos unidos, para não contar
    #    duas vezes o tempo em que dois eventos se sobrepõem.
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
