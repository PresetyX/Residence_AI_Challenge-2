"""Interpreta o prazo de um projeto escrito em linguagem natural.

Usado pelo Supervisor (e pelo backend no POST /projetos e POST /prazos/interpretar)
para tirar a data de entrega do próprio pedido, sem LLM:

    "Quero um app de receitas até 20/12"         -> 2026-12-20
    "preciso entregar até amanhã"                 -> amanhã
    "tenho uma semana para fazer o TCC"           -> hoje + 7 dias
    "em 3 meses", "daqui a 10 dias", "2 semanas"  -> hoje + o período
    "até sexta", "semana que vem", "fim do mês"   -> a data correspondente

Devolve None quando o texto não traz prazo. Uma data impossível (31/02) gera
ValueError com a mensagem para o usuário.
"""

from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import date, datetime, timedelta

from destrava.core import config

MESES = (
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)

NUMEROS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "quinze": 15, "vinte": 20, "trinta": 30,
}

DIAS_DA_SEMANA = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6,
}

_NUMERO = r"(\d{1,3}|" + "|".join(NUMEROS) + r")"


def _normalizar(texto: str) -> str:
    letras = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in letras if unicodedata.category(c) != "Mn")


def _numero(valor: str) -> int:
    return NUMEROS[valor] if valor in NUMEROS else int(valor)


def _data(ano: int, mes: int, dia: int, original: str) -> date:
    try:
        return date(ano, mes, dia)
    except ValueError:
        raise ValueError(f"A data {original} não existe. Informe uma data válida.") from None


def _proxima(mes: int, dia: int, hoje: date, original: str) -> date:
    """Dia/mês sem ano: a próxima vez que essa data acontece (hoje inclusive)."""
    candidata = _data(hoje.year, mes, dia, original)
    return candidata if candidata >= hoje else _data(hoje.year + 1, mes, dia, original)


def _fim_do_mes(ano: int, mes: int) -> date:
    return date(ano, mes, calendar.monthrange(ano, mes)[1])


def _somar_meses(dia: date, meses: int) -> date:
    total = dia.month - 1 + meses
    ano, mes = dia.year + total // 12, total % 12 + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def _domingo(hoje: date) -> date:
    return hoje + timedelta(days=(6 - hoje.weekday()) % 7)


def interpretar_prazo(texto: str, agora: datetime | None = None) -> date | None:
    """Data de entrega escrita no texto, ou None se não houver.

    Raises:
        ValueError: se o texto trouxer uma data que não existe (ex.: 31/02).
    """
    if not isinstance(texto, str) or not texto.strip():
        return None
    hoje = (agora or datetime.now(config.FUSO)).date()
    t = _normalizar(texto)

    # 1. Datas escritas: ISO, dd/mm/aaaa, dd/mm/aa, dd/mm (também com - ou .).
    achado = re.search(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)", t)
    if achado:
        ano, mes, dia = (int(p) for p in achado.groups())
        return _data(ano, mes, dia, achado.group())

    achado = re.search(r"(?<![\d:])(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{4}|\d{2}))?(?![\d:])", t)
    if achado:
        dia, mes = int(achado.group(1)), int(achado.group(2))
        if achado.group(3):
            ano = int(achado.group(3))
            return _data(ano + 2000 if ano < 100 else ano, mes, dia, achado.group())
        return _proxima(mes, dia, hoje, achado.group())

    # 2. "20 de dezembro", "20 de dezembro de 2026", "dezembro de 2026", "ate dezembro".
    meses = "|".join(MESES)
    achado = re.search(rf"\b(\d{{1,2}})\s+de\s+({meses})(?:\s+(?:de\s+)?(\d{{4}}))?\b", t)
    if achado:
        dia, mes = int(achado.group(1)), MESES.index(achado.group(2)) + 1
        if achado.group(3):
            return _data(int(achado.group(3)), mes, dia, achado.group())
        return _proxima(mes, dia, hoje, achado.group())
    achado = re.search(rf"\b(?:ate|em|para|no fim de|no final de|final de|fim de)\s+({meses})(?:\s+(?:de\s+)?(\d{{4}}))?\b", t)
    if achado:
        mes = MESES.index(achado.group(1)) + 1
        ano = int(achado.group(2)) if achado.group(2) else (hoje.year if mes >= hoje.month else hoje.year + 1)
        return _fim_do_mes(ano, mes)

    # 3. Dias relativos.
    if re.search(r"\bdepois de amanha\b", t):
        return hoje + timedelta(days=2)
    if re.search(r"\bamanha\b", t):
        return hoje + timedelta(days=1)
    if re.search(r"\b(ate|para|entregar|prazo)\s+hoje\b|\bhoje mesmo\b", t):
        return hoje

    # 4. Períodos: "em 3 semanas", "daqui a 10 dias", "tenho uma semana", "2 meses", "uma quinzena".
    achado = re.search(rf"\b{_NUMERO}\s+(dias?|semanas?|mes|meses|anos?)\b", t)
    if achado:
        quantidade, unidade = _numero(achado.group(1)), achado.group(2)
        if unidade.startswith("dia"):
            return hoje + timedelta(days=quantidade)
        if unidade.startswith("semana"):
            return hoje + timedelta(weeks=quantidade)
        if unidade.startswith("mes"):
            return _somar_meses(hoje, quantidade)
        return _somar_meses(hoje, 12 * quantidade)
    if re.search(r"\b(uma\s+)?quinzena\b", t):
        return hoje + timedelta(days=15)
    if re.search(r"\b(um|uma)?\s*(semana|mes|ano)\b", t) and re.search(r"\b(tenho|em|daqui a|dentro de|prazo de|de prazo|ate)\b", t):
        unidade = re.search(r"\b(semana|mes|ano)\b", t).group(1)
        if unidade == "semana" and not re.search(r"\b(esta|essa|nesta|nessa|proxima|que vem|seguinte|fim da|final da)\b", t):
            return hoje + timedelta(weeks=1)
        if unidade == "mes" and not re.search(r"\b(fim do|final do|que vem|proximo|seguinte|este|esse)\b", t):
            return _somar_meses(hoje, 1)
        if unidade == "ano" and not re.search(r"\b(fim do|final do|que vem|proximo|este|esse)\b", t):
            return _somar_meses(hoje, 12)

    # 5. Semana, mês e ano do calendário.
    if re.search(r"\b(semana que vem|proxima semana|semana seguinte)\b", t):
        return _domingo(hoje) + timedelta(days=7)
    if re.search(r"\b(esta|essa|nesta|nessa) semana\b|\b(fim|final) (da|de) semana\b", t):
        return _domingo(hoje)
    if re.search(r"\b(mes que vem|proximo mes|mes seguinte)\b", t):
        seguinte = _somar_meses(hoje.replace(day=1), 1)
        return _fim_do_mes(seguinte.year, seguinte.month)
    if re.search(r"\b(fim|final) do mes\b|\b(este|esse|neste|nesse) mes\b", t):
        return _fim_do_mes(hoje.year, hoje.month)
    if re.search(r"\b(fim|final) do ano\b|\b(este|esse|neste|nesse) ano\b", t):
        return date(hoje.year, 12, 31)
    if re.search(r"\b(ano que vem|proximo ano)\b", t):
        return date(hoje.year + 1, 12, 31)

    # 6. Dia da semana: "ate sexta", "sexta que vem", "proxima segunda".
    achado = re.search(r"\b(segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:-feira)?\b", t)
    if achado and re.search(r"\b(ate|para|na|no|proxim[oa]|que vem|entregar|prazo)\b", t):
        # A próxima ocorrência; no próprio dia, a da semana seguinte.
        dias = (DIAS_DA_SEMANA[achado.group(1)] - hoje.weekday()) % 7 or 7
        return hoje + timedelta(days=dias)

    return None
