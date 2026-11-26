"""Lê horários e durações escritos em português livre.

Usado no onboarding do chat:
    - interpretar_horario("11 da noite", "dormir") -> time(23, 0)
    - interpretar_horario("7h30", "acordar") -> time(7, 30)
    - interpretar_duracao("1h30") -> 90 (minutos)

Não chama APIs nem LLM: só regras. Devolve None quando não entende.
"""

import re
import unicodedata
from datetime import time
from typing import Literal

TipoHorario = Literal["dormir", "acordar"]

_NUMEROS = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18,
    "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
}


# Sinal de menos colado a um número (hífen ou "−") no começo de uma palavra.
_SINAL = re.compile(r"(?<![^\s(\[=:,;])[-−](?=\d)")
# "10h -11h" é um intervalo: antes do traço já há um número ou horário.
_NUMERO_ANTES = re.compile(r"\d\s*(?:h|hrs?|horas?|min|minutos?)?\s*$", re.IGNORECASE)
_UNIDADE_DEPOIS = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?::\d|(?:h|hrs?|horas?|min|minutos?|dias?|semanas?|m[eê]s|meses|anos?)(?![a-zà-ú]))"
    r"|\d+h\d",
    re.IGNORECASE,
)
# Palavras depois das quais um número é um horário ou um prazo.
_PALAVRA_DE_TEMPO = re.compile(r"(?<!\w)(?:das|às|as|até|ate|em|daqui a|tenho)\s*$", re.IGNORECASE)
_COMECA_COM_MENOS = re.compile(r"^\s*menos\s+\d", re.IGNORECASE)


def tem_numero_negativo(texto: str, qualquer: bool = False) -> bool:
    """O texto traz um horário, duração ou prazo negativo ("-1h", "em -3 dias").

    Traços que não são sinal ficam de fora: "13h-14h", "10h - 11h", "20-12",
    "2026-12-20", "sexta-feira" e "turma -2".

    Args:
        qualquer: para respostas que são só um número (sono e calibração):
            todo número negativo conta, mesmo sem unidade ("-3").
    """
    if qualquer and _COMECA_COM_MENOS.search(texto):
        return True
    for sinal in _SINAL.finditer(texto):
        antes, depois = texto[: sinal.start()], texto[sinal.end():]
        if _NUMERO_ANTES.search(antes):
            continue
        if qualquer or _UNIDADE_DEPOIS.match(depois) or _PALAVRA_DE_TEMPO.search(antes):
            return True
    return False


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    sem_acento = sem_acento.replace("-", " ")
    # "vinte e tres" -> "23", "onze" -> "11": troca números por extenso por dígitos.
    sem_acento = re.sub(
        r"\b(vinte|trinta|quarenta|cinquenta) e (um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove)\b",
        lambda m: str(_NUMEROS[m.group(1)] + _NUMEROS[m.group(2)]),
        sem_acento,
    )
    sem_acento = re.sub(
        r"\b(" + "|".join(sorted(_NUMEROS, key=len, reverse=True)) + r")\b",
        lambda m: str(_NUMEROS[m.group(1)]),
        sem_acento,
    )
    return re.sub(r"\s+", " ", sem_acento).strip()


def interpretar_horario(texto: str, tipo: TipoHorario) -> time | None:
    """Horário de dormir ou acordar escrito livremente.

    Sem "da manhã"/"da noite", a hora ambígua é lida pelo tipo: para dormir,
    "11" é 23h e "1" é 1h da madrugada; para acordar, "7" é 7h.
    """
    if tem_numero_negativo(texto, qualquer=True):
        return None
    t = _normalizar(texto)
    if re.search(r"\bmeia noite\b", t):
        hora, minuto = 0, 30 if re.search(r"meia noite e meia", t) else 0
        return time(hora, minuto)
    if re.search(r"\bmeio dia\b", t):
        return time(12, 30 if re.search(r"meio dia e meia", t) else 0)
    # "23h e meia" -> "23:30"; "10 horas e 15" -> "10:15".
    t = re.sub(r"(\d)\s*(?:h|horas?)\s+e\s+meia\b", r"\1:30", t)
    t = re.sub(r"(\d)\s*(?:h|horas?)\s+e\s+(\d{1,2})\b", r"\1:\2", t)

    achado = re.search(
        r"(?<!\d)(\d{1,2})\s*(?:(?::|h|horas?)\s*(\d{1,2})?|e\s+(meia|\d{1,2})\b)?",
        t,
    )
    if not achado:
        return None
    hora = int(achado.group(1))
    if achado.group(3) == "meia":
        minuto = 30
    else:
        minuto = int(achado.group(2) or achado.group(3) or 0)
    if hora > 24 or minuto > 59:
        return None
    if hora == 24:
        hora = 0

    noite = re.search(r"\b(da noite|a noite|de noite|da tarde|a tarde|de tarde|pm)\b", t)
    manha = re.search(r"\b(da manha|de manha|pela manha|da madrugada|de madrugada|am)\b", t)
    if noite and hora < 12:
        hora += 12
    elif manha and hora == 12:
        hora = 0
    elif not noite and not manha and hora <= 12:
        if tipo == "dormir":
            # Ninguém dorme às 8h da manhã por padrão: 6..11 vira noite, 12 vira meia-noite.
            if hora == 12:
                hora = 0
            elif hora >= 6:
                hora += 12
    return time(hora, minuto)


def interpretar_duracao(texto: str) -> int | None:
    """Duração de uma tarefa, em minutos ("2h", "1h30", "90 min", "meia hora", "2 dias").

    Um dia de trabalho vale 8 horas. Número solto até 12 é lido como horas
    ("3" = 3 horas); acima disso, como minutos ("45" = 45 minutos).
    """
    if tem_numero_negativo(texto, qualquer=True):
        return None
    t = _normalizar(texto)
    t = re.sub(r"\bmeia hora\b", "30 min", t)
    t = re.sub(r"\b(\d+)\s*(?:h|horas?)\s+e\s+meia\b", lambda m: f"{m.group(1)}h 30min", t)
    # "1h30" e "1 hora e 30" -> "1h 30min".
    t = re.sub(r"\b(\d+)\s*(?:h|horas?)\s*(?:e\s+)?(\d{1,2})\b(?!\s*(?:h|min|m\b))", r"\1h \2min", t)
    t = t.replace(",", ".")

    total = 0.0
    achou = False
    for numero, unidade in re.findall(r"(\d+(?:\.\d+)?)\s*(dias?|d\b|horas?|hrs?|h|minutos?|mins?|m\b)?", t):
        valor = float(numero)
        if not unidade:
            continue
        achou = True
        if unidade.startswith("d"):
            total += valor * 8 * 60
        elif unidade.startswith("h"):
            total += valor * 60
        else:
            total += valor
    if not achou:
        hora_minuto = re.search(r"(\d{1,2}):(\d{2})", t)
        if hora_minuto:
            achou, total = True, int(hora_minuto.group(1)) * 60 + int(hora_minuto.group(2))
    if not achou:
        solto = re.fullmatch(r"\D*?(\d+(?:\.\d+)?)\D*", t)
        if solto:
            valor = float(solto.group(1))
            achou, total = True, valor * 60 if valor <= 12 else valor
    if not achou:
        return None
    minutos = round(total)
    return minutos if minutos > 0 else None
