"""
Contrato de resposta padrão de TODOS os agentes do Destrava.

Por que existe:
    Cada agente faz uma coisa diferente (visualizar, criar, editar, excluir),
    mas o supervisor precisa ler a resposta de todos do mesmo jeito. Por isso
    todos devolvem o mesmo JSON, só mudando o conteúdo de ``dados``.

Formato (exemplo do agente de criar):

    {
      "agente": "criar",
      "status": "sucesso",                 # "sucesso" | "erro" | "cancelado"
      "acao": "evento_criado",             # o que aconteceu, em snake_case
      "mensagem": "Pronto! Criei ...",     # texto do LLM para o usuário
      "periodo": {                          # período tratado pelo agente
        "inicio": "2026-11-15T14:00:00-03:00",
        "fim": "2026-11-15T15:00:00-03:00",
        "duracao_minutos": 60.0
      },
      "dados": { ... },                     # específico de cada agente
      "fluxo": {                            # as 3 etapas que todo agente segue
        "inicio": {"etapa": "extracao", "status": "ok", "detalhe": {...}},
        "meio":   {"etapa": "google_calendar", "status": "ok", "detalhe": {...}},
        "fim":    {"etapa": "resposta", "status": "ok", "detalhe": null}
      },
      "erro": null                          # {"tipo": "...", "mensagem": "..."}
    }

As 3 etapas do fluxo (iguais para todos os agentes):
    inicio -> o LLM entende o pedido e devolve JSON (PROMPT_EXTRACAO)
    meio   -> o código fala com o Google Calendar
    fim    -> o LLM escreve a resposta final (PROMPT_RESPOSTA)

Como um agente usa:
    Implementa três funções (extrair, executar, responder) e chama
    ``executar_fluxo(...)``. O tratamento de erros, o preenchimento do fluxo
    e a montagem do JSON ficam todos aqui, para nenhum agente reinventar.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from destrava.core import config


StatusResposta = Literal["sucesso", "erro", "cancelado"]
StatusEtapa = Literal["ok", "erro", "cancelado", "pendente"]


class Periodo(BaseModel):
    """Intervalo de tempo tratado pelo agente (com fuso de config.FUSO)."""

    inicio: datetime
    fim: datetime
    duracao_minutos: float

    @classmethod
    def de(cls, inicio: datetime, fim: datetime) -> "Periodo":
        """Monta o período já normalizado no fuso do projeto."""
        inicio = _no_fuso(inicio)
        fim = _no_fuso(fim)
        return cls(
            inicio=inicio,
            fim=fim,
            duracao_minutos=(fim - inicio).total_seconds() / 60,
        )


class Etapa(BaseModel):
    """Uma etapa do fluxo do agente."""

    etapa: str
    status: StatusEtapa = "pendente"
    detalhe: Any = None


class Fluxo(BaseModel):
    """Início, meio e fim do fluxo do agente."""

    inicio: Etapa
    meio: Etapa
    fim: Etapa


class ErroInfo(BaseModel):
    """Erro que interrompeu (ou afetou) o fluxo."""

    tipo: str
    mensagem: str


class RespostaAgente(BaseModel):
    """Resposta padrão devolvida por todos os agentes."""

    agente: str
    status: StatusResposta
    acao: str
    mensagem: str
    periodo: Periodo | None = None
    dados: dict[str, Any] | None = None
    fluxo: Fluxo
    erro: ErroInfo | None = None

    def para_dict(self) -> dict[str, Any]:
        """Dicionário pronto para json.dumps (datas viram texto ISO 8601)."""
        return self.model_dump(mode="json")

    def para_json(self, indent: int | None = 2) -> str:
        """Texto JSON da resposta (mantém acentos)."""
        return json.dumps(self.para_dict(), ensure_ascii=False, indent=indent)


@dataclass
class ResultadoExecucao:
    """O que a etapa "meio" de um agente devolve para o executar_fluxo."""

    dados: dict[str, Any]
    periodo: Periodo | None = None
    detalhe: Any = None


class Cancelado(Exception):
    """Levantada quando o usuário não confirma a ação (ex.: não digitou CRIAR)."""


def executar_fluxo(
    *,
    agente: str,
    acao_sucesso: str,
    acao_erro: str,
    pergunta: str,
    extrair: Callable[[str], dict[str, Any]],
    executar: Callable[[dict[str, Any]], ResultadoExecucao],
    responder: Callable[[str, dict[str, Any]], str],
    mensagem_padrao: Callable[[dict[str, Any]], str],
    confirmar: Callable[[dict[str, Any]], bool] | None = None,
    etapa_meio: str = "google_calendar",
) -> RespostaAgente:
    """Roda início, meio e fim de um agente e devolve sempre o JSON padrão.

    Args:
        agente: nome do agente ("visualizar", "criar", ...).
        acao_sucesso: valor de ``acao`` quando dá certo (ex.: "evento_criado").
        acao_erro: valor de ``acao`` quando falha (ex.: "evento_nao_criado").
        pergunta: pedido do usuário em texto livre.
        extrair: etapa início. Recebe a pergunta e devolve os dados extraídos.
        executar: etapa meio. Recebe os dados extraídos e fala com o Google.
        responder: etapa fim. Recebe a pergunta e ``dados`` e devolve o texto.
        mensagem_padrao: texto usado se o LLM falhar na etapa fim.
        confirmar: opcional. Recebe os dados extraídos; se devolver False,
            o fluxo para com status "cancelado" (nada é alterado na agenda).
        etapa_meio: nome da etapa meio no JSON.

    Returns:
        RespostaAgente. Nunca levanta exceção: erros viram ``status="erro"``.
    """
    fluxo = Fluxo(
        inicio=Etapa(etapa="extracao"),
        meio=Etapa(etapa=etapa_meio),
        fim=Etapa(etapa="resposta"),
    )

    # INÍCIO: o LLM entende o pedido.
    try:
        extraido = extrair(pergunta)
    except Exception as erro:  # noqa: BLE001 - todo erro vira JSON
        fluxo.inicio.status = "erro"
        return _resposta_erro(agente, acao_erro, fluxo, erro, "Não entendi o pedido")

    fluxo.inicio.status = "ok"
    fluxo.inicio.detalhe = extraido

    if confirmar is not None and not confirmar(extraido):
        fluxo.meio.status = "cancelado"
        fluxo.fim.status = "cancelado"
        return RespostaAgente(
            agente=agente,
            status="cancelado",
            acao=acao_erro,
            mensagem="Ação cancelada pelo usuário. Nada foi alterado na agenda.",
            periodo=_periodo_extraido(extraido),
            dados=None,
            fluxo=fluxo,
        )

    # MEIO: o código fala com o Google Calendar.
    try:
        resultado = executar(extraido)
    except Cancelado as erro:
        fluxo.meio.status = "cancelado"
        fluxo.fim.status = "cancelado"
        return RespostaAgente(
            agente=agente,
            status="cancelado",
            acao=acao_erro,
            mensagem=str(erro) or "Ação cancelada.",
            periodo=_periodo_extraido(extraido),
            fluxo=fluxo,
        )
    except Exception as erro:  # noqa: BLE001
        fluxo.meio.status = "erro"
        resposta = _resposta_erro(
            agente, acao_erro, fluxo, erro, "Não foi possível concluir a ação"
        )
        resposta.periodo = _periodo_extraido(extraido)
        return resposta

    fluxo.meio.status = "ok"
    fluxo.meio.detalhe = resultado.detalhe

    # FIM: o LLM escreve a resposta. Se falhar, a ação já foi feita, então
    # o status continua "sucesso" e usamos uma mensagem padrão.
    erro_fim: ErroInfo | None = None
    try:
        mensagem = responder(pergunta, resultado.dados).strip()
        if not mensagem:
            raise ValueError("O modelo devolveu uma resposta vazia.")
        fluxo.fim.status = "ok"
    except Exception as erro:  # noqa: BLE001
        fluxo.fim.status = "erro"
        erro_fim = ErroInfo(tipo=type(erro).__name__, mensagem=str(erro))
        mensagem = mensagem_padrao(resultado.dados)

    return RespostaAgente(
        agente=agente,
        status="sucesso",
        acao=acao_sucesso,
        mensagem=mensagem,
        periodo=resultado.periodo,
        dados=resultado.dados,
        fluxo=fluxo,
        erro=erro_fim,
    )


def _resposta_erro(
    agente: str,
    acao_erro: str,
    fluxo: Fluxo,
    erro: Exception,
    prefixo: str,
) -> RespostaAgente:
    """Monta a resposta de erro, marcando as etapas seguintes como pendentes."""
    return RespostaAgente(
        agente=agente,
        status="erro",
        acao=acao_erro,
        mensagem=f"{prefixo}: {erro}",
        fluxo=fluxo,
        erro=ErroInfo(tipo=type(erro).__name__, mensagem=str(erro)),
    )


def _periodo_extraido(extraido: dict[str, Any]) -> Periodo | None:
    """Tenta montar o período a partir dos campos inicio/fim extraídos."""
    try:
        return Periodo.de(
            _para_datetime(extraido["inicio"]), _para_datetime(extraido["fim"])
        )
    except (KeyError, TypeError, ValueError):
        return None


def _para_datetime(valor: datetime | str) -> datetime:
    if isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(valor)


def _no_fuso(momento: datetime) -> datetime:
    if momento.tzinfo is None:
        return momento.replace(tzinfo=config.FUSO)
    return momento.astimezone(config.FUSO)
