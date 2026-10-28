
"""
Valida dados e realiza a criação de eventos no Google Calendar.

Chamado pelo Supervisor do Destrava.
Utiliza configurações do core e o cliente do Google Calendar.
"""

from datetime import datetime

from destrava.core import config


def validar_dados_evento(dados: dict) -> dict:
    """
    Valida os dados recebidos para criar um evento.

    Args:
        dados (dict): Dicionário contendo título, início e fim.

    Returns:
        dict: Dados validados com datas no fuso do projeto.

    Raises:
        ValueError: Se algum campo estiver ausente,
            inválido ou com horário inconsistente.
    """

    titulo = dados.get("titulo")
    inicio = dados.get("inicio")
    fim = dados.get("fim")

    if not isinstance(titulo, str) or not titulo.strip():
        raise ValueError("O título do evento é obrigatório.")

    if not isinstance(inicio, str) or not isinstance(fim, str):
        raise ValueError("Início e fim são obrigatórios.")

    try:
        data_inicio = datetime.fromisoformat(inicio)
        data_fim = datetime.fromisoformat(fim)
    except ValueError as erro:
        raise ValueError("Data ou horário inválido.") from erro

    if data_inicio.tzinfo is None:
        data_inicio = data_inicio.replace(tzinfo=config.FUSO)
    else:
        data_inicio = data_inicio.astimezone(config.FUSO)

    if data_fim.tzinfo is None:
        data_fim = data_fim.replace(tzinfo=config.FUSO)
    else:
        data_fim = data_fim.astimezone(config.FUSO)

    if data_inicio >= data_fim:
        raise ValueError("O início deve ser anterior ao fim.")

    if data_inicio <= datetime.now(config.FUSO):
        raise ValueError("Não é permitido criar eventos no passado.")

    return {
        "titulo": titulo.strip(),
        "inicio": data_inicio.isoformat(),
        "fim": data_fim.isoformat()
    }
