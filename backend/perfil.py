"""Perfil do usuário: horário de sono e calibração dos story points.

O perfil fica na conta (e-mail do Google) e vale para o backend inteiro, que
atende uma conta por vez (um token do Google por máquina). Ao entrar, o perfil
da conta é aplicado:
    - sono -> config.HORARIO_DORMIR / config.HORARIO_ACORDAR (agenda_engine,
      encaixe_pomodoro e Supervisor leem esses valores na hora do cálculo);
    - calibração -> pomodoro.MINUTOS_POR_STORY_POINT (tempo de cada story point).

TODO(BD): o perfil ainda fica em data/perfis.json. Quando o banco de dados dos
story points estiver pronto, trocar _ler_perfis/_gravar_perfis pelo acesso ao
banco (o resto do módulo não muda).

Rotas:
    GET  /perfil                      perfil da conta (onboarding pendente?)
    PUT  /perfil/sono                 salva os horários de dormir e acordar
    POST /perfil/interpretar          lê "11 da noite", "7h30", "1h30"...
"""

import json
import statistics
from datetime import datetime, time
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from destrava.core import config, pomodoro
from destrava.core.horario import interpretar_duracao, interpretar_horario

router = APIRouter()

CAMINHO_PERFIS = config.RAIZ_PROJETO / "data" / "perfis.json"
ARQUIVO_CONSENTIMENTO = config.RAIZ_PROJETO / "consentimento.json"
_LOCK = Lock()

# Valores de fábrica (config.py e pomodoro.py), restaurados ao trocar de conta.
_PADRAO_DORMIR = config.HORARIO_DORMIR
_PADRAO_ACORDAR = config.HORARIO_ACORDAR
_PADRAO_MINUTOS_SP = pomodoro.MINUTOS_POR_STORY_POINT

SONO_MINIMO_HORAS = 3
SONO_MAXIMO_HORAS = 14
MINIMO_RESPOSTAS_CALIBRACAO = 3
MINUTOS_SP_MINIMO = 5
MINUTOS_SP_MAXIMO = 8 * 60

_email_ativo: str | None = None


# ---------------------------------------------------------------------------
# Armazenamento (TODO(BD): trocar pelo banco)
# ---------------------------------------------------------------------------


def _ler_perfis() -> dict[str, dict[str, Any]]:
    if not CAMINHO_PERFIS.exists():
        return {}
    try:
        return json.loads(CAMINHO_PERFIS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _gravar_perfis(perfis: dict[str, dict[str, Any]]) -> None:
    CAMINHO_PERFIS.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO_PERFIS.write_text(json.dumps(perfis, ensure_ascii=False, indent=2), encoding="utf-8")


def obter_perfil(email: str) -> dict[str, Any]:
    return _ler_perfis().get(email.lower(), {})


def _atualizar_perfil(email: str, **campos: Any) -> dict[str, Any]:
    with _LOCK:
        perfis = _ler_perfis()
        perfil = perfis.setdefault(email.lower(), {})
        perfil.update(campos, atualizado_em=datetime.now(config.FUSO).isoformat())
        _gravar_perfis(perfis)
        return perfil


# ---------------------------------------------------------------------------
# Conta ativa
# ---------------------------------------------------------------------------


def aplicar_perfil(perfil: dict[str, Any]) -> None:
    """Aplica o sono e a calibração do perfil (ou os padrões, se faltarem)."""
    sono = perfil.get("sono") or {}
    config.HORARIO_DORMIR = time.fromisoformat(sono["dormir"]) if "dormir" in sono else _PADRAO_DORMIR
    config.HORARIO_ACORDAR = time.fromisoformat(sono["acordar"]) if "acordar" in sono else _PADRAO_ACORDAR
    calibracao = perfil.get("calibracao") or {}
    pomodoro.MINUTOS_POR_STORY_POINT = int(calibracao.get("minutos_por_story_point") or _PADRAO_MINUTOS_SP)


def ativar_conta(email: str | None) -> None:
    """Torna `email` a conta ativa e aplica o perfil dela."""
    global _email_ativo
    _email_ativo = email.lower() if email else None
    aplicar_perfil(obter_perfil(_email_ativo) if _email_ativo else {})


def ativar_conta_salva() -> None:
    """Na subida do backend: reativa a última conta que entrou (consentimento.json)."""
    try:
        email = json.loads(ARQUIVO_CONSENTIMENTO.read_text(encoding="utf-8")).get("email")
    except (OSError, json.JSONDecodeError):
        email = None
    ativar_conta(email)


def email_ativo() -> str | None:
    return _email_ativo


def _conta(email: str | None) -> str:
    conta = (email or _email_ativo or "").strip().lower()
    if not conta:
        raise HTTPException(status_code=401, detail="Entre com sua conta Google para salvar o perfil.")
    return conta


# ---------------------------------------------------------------------------
# Regras
# ---------------------------------------------------------------------------


def horas_de_sono(dormir: time, acordar: time) -> float:
    minutos = (acordar.hour * 60 + acordar.minute) - (dormir.hour * 60 + dormir.minute)
    return (minutos % (24 * 60)) / 60


def calcular_minutos_por_story_point(respostas: list[int | None], pontos: list[int]) -> float:
    """Minutos de trabalho por story point a partir das respostas de calibração.

    Respostas puladas (None) ficam de fora. Para ser robusto a um chute muito
    fora da curva, descarta as razões (minutos / pontos) mais de 3x acima ou
    abaixo da mediana e usa a média ponderada pelos pontos (soma dos minutos /
    soma dos pontos): tarefas grandes pesam mais que as de 1 ponto, cujo tempo
    varia mais.

    Raises:
        ValueError: Menos de MINIMO_RESPOSTAS_CALIBRACAO respostas válidas.
    """
    pares = [(r, p) for r, p in zip(respostas, pontos) if r is not None]
    if len(pares) < MINIMO_RESPOSTAS_CALIBRACAO:
        raise ValueError(
            f"Responda pelo menos {MINIMO_RESPOSTAS_CALIBRACAO} perguntas para calibrar."
        )
    mediana = statistics.median(r / p for r, p in pares)
    filtrados = [(r, p) for r, p in pares if mediana / 3 <= r / p <= mediana * 3] or pares
    media = sum(r for r, _ in filtrados) / sum(p for _, p in filtrados)
    return min(max(media, MINUTOS_SP_MINIMO), MINUTOS_SP_MAXIMO)


def salvar_calibracao(minutos_por_sp: float, respostas: list[int | None]) -> None:
    """Aplica a calibração e, com uma conta ativa, grava no perfil dela."""
    minutos = round(minutos_por_sp)
    pomodoro.MINUTOS_POR_STORY_POINT = minutos
    if _email_ativo:
        _atualizar_perfil(
            _email_ativo,
            calibracao={"minutos_por_story_point": minutos, "respostas": respostas},
        )


def _resumo(email: str) -> dict[str, Any]:
    perfil = obter_perfil(email)
    calibracao = perfil.get("calibracao")
    return {
        "email": email,
        "sono": perfil.get("sono"),
        "calibracao": (
            {"minutos_por_story_point": calibracao["minutos_por_story_point"]} if calibracao else None
        ),
        "minutos_por_story_point": pomodoro.MINUTOS_POR_STORY_POINT
        if email == _email_ativo
        else (calibracao or {}).get("minutos_por_story_point", _PADRAO_MINUTOS_SP),
    }


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


class SonoRequest(BaseModel):
    email: str | None = None
    dormir: str
    acordar: str


class InterpretarRequest(BaseModel):
    texto: str
    tipo: Literal["dormir", "acordar", "duracao"]


def _horario(texto: str, tipo: Literal["dormir", "acordar"]) -> time:
    try:
        return time.fromisoformat(texto.strip())
    except ValueError:
        pass
    valor = interpretar_horario(texto, tipo)
    if valor is None:
        verbo = "dormir" if tipo == "dormir" else "acordar"
        raise HTTPException(
            status_code=422,
            detail=f"Não entendi o horário de {verbo} \"{texto}\". Tente algo como 23h, 23:30 ou 7 da manhã.",
        )
    return valor


@router.get("/perfil")
def ler_perfil(email: str | None = None) -> dict[str, Any]:
    return _resumo(_conta(email))


@router.put("/perfil/sono")
def salvar_sono(corpo: SonoRequest) -> dict[str, Any]:
    conta = _conta(corpo.email)
    dormir = _horario(corpo.dormir, "dormir")
    acordar = _horario(corpo.acordar, "acordar")
    horas = horas_de_sono(dormir, acordar)
    if not SONO_MINIMO_HORAS <= horas <= SONO_MAXIMO_HORAS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Dormindo às {dormir:%H:%M} e acordando às {acordar:%H:%M} são {horas:.1f} h de sono. "
                f"Informe um sono entre {SONO_MINIMO_HORAS} e {SONO_MAXIMO_HORAS} horas."
            ),
        )
    _atualizar_perfil(conta, sono={"dormir": f"{dormir:%H:%M}", "acordar": f"{acordar:%H:%M}"})
    if conta == _email_ativo or _email_ativo is None:
        ativar_conta(conta)
    return _resumo(conta)


@router.post("/perfil/interpretar")
def interpretar(corpo: InterpretarRequest) -> dict[str, Any]:
    """Lê a resposta do onboarding: {valor} é "HH:MM" (sono) ou minutos (duração), ou null."""
    if corpo.tipo == "duracao":
        return {"valor": interpretar_duracao(corpo.texto)}
    valor = interpretar_horario(corpo.texto, corpo.tipo)
    return {"valor": f"{valor:%H:%M}" if valor else None}
