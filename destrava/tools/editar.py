"""
Agente de edição de eventos no Google Calendar.

Segue a mesma lógica dos agentes de visualização e de criação: recebe um JSON
e devolve um JSON, sem usar LLM.

    executar_json(entrada) -> recebe {"id", "titulo"?, "inicio"?, "fim"?,
                              "descricao"?, "local"?}, confere o evento no
                              Google, altera só os campos enviados e devolve o
                              evento atualizado em JSON.

O evento a alterar é identificado pelo ID (o Supervisor ou o painel manual já
sabem qual é). Escopo OAuth: calendar (escrita).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError, field_validator, model_validator

from destrava.core import config
from destrava.core.google_client import atualizar_evento, get_service, obter_evento
from destrava.core.models import ErroInfo, Etapa, Fluxo, Periodo, RespostaAgente


class PedidoEdicao(BaseModel):
    """Pedido de entrada do agente de edição: o ID e os campos que mudam.

    Campos ausentes (None) ficam como estão. Datas sem fuso valem no horário
    de config.FUSO. Início e fim, se enviados, vêm juntos e em ordem.
    """

    id: str
    titulo: str | None = None
    inicio: datetime | None = None
    fim: datetime | None = None
    descricao: str | None = None
    local: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _id_obrigatorio(cls, valor):
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("O ID do evento é obrigatório.")
        return valor.strip()

    @field_validator("titulo")
    @classmethod
    def _titulo_nao_vazio(cls, valor: str | None) -> str | None:
        if valor is not None and not valor.strip():
            raise ValueError("O título do evento não pode ficar vazio.")
        return valor.strip() if valor is not None else None

    @field_validator("inicio", "fim")
    @classmethod
    def _no_fuso_do_projeto(cls, valor: datetime | None) -> datetime | None:
        if valor is None:
            return None
        if valor.tzinfo is None:
            return valor.replace(tzinfo=config.FUSO)
        return valor.astimezone(config.FUSO)

    @model_validator(mode="after")
    def _horarios_coerentes(self):
        if (self.inicio is None) != (self.fim is None):
            raise ValueError("Envie início e fim juntos para mudar o horário.")
        if self.inicio is not None and self.fim is not None and self.inicio >= self.fim:
            raise ValueError("O início deve ser anterior ao fim.")
        return self


def _move_para_o_passado(pedido: PedidoEdicao, atual: dict[str, Any]) -> bool:
    """Novo início no passado. Manter o horário de um evento antigo continua valendo."""
    if pedido.inicio is None or pedido.inicio > datetime.now(config.FUSO):
        return False
    inicio = atual.get("start", {})
    bruto = inicio.get("dateTime") or inicio.get("date")
    if not bruto:
        return True
    antes = datetime.fromisoformat(bruto.replace("Z", "+00:00"))
    if antes.tzinfo is None:
        antes = antes.replace(tzinfo=config.FUSO)
    return antes != pedido.inicio


def montar_alteracoes(pedido: PedidoEdicao) -> dict[str, Any]:
    """Corpo do PATCH do Google com só os campos enviados."""
    alteracoes: dict[str, Any] = {}
    if pedido.titulo is not None:
        alteracoes["summary"] = pedido.titulo
    if pedido.descricao is not None:
        alteracoes["description"] = pedido.descricao
    if pedido.local is not None:
        alteracoes["location"] = pedido.local
    if pedido.inicio is not None and pedido.fim is not None:
        alteracoes["start"] = {"dateTime": pedido.inicio.isoformat(), "timeZone": str(config.FUSO)}
        alteracoes["end"] = {"dateTime": pedido.fim.isoformat(), "timeZone": str(config.FUSO)}
    return alteracoes


def evento_resumido(evento: dict[str, Any]) -> dict[str, Any]:
    """Converte o evento bruto do Google para o formato dos agentes."""
    inicio = evento.get("start", {})
    fim = evento.get("end", {})
    meta = evento.get("extendedProperties", {}).get("private", {}).get("meta")
    resumo = {
        "id": evento.get("id"),
        "titulo": evento.get("summary") or "(sem título)",
        "inicio": inicio.get("dateTime") or inicio.get("date"),
        "fim": fim.get("dateTime") or fim.get("date"),
        "link": evento.get("htmlLink"),
        "descricao": evento.get("description") or "",
        "local": evento.get("location") or "",
    }
    if meta:
        resumo["meta"] = meta
    return resumo


class AgenteEditar:
    """Agente responsável por editar eventos no Google Calendar."""

    def __init__(self, servico=None):
        # Permite injetar um serviço falso nos testes.
        self._servico = servico

    def _service(self):
        return self._servico or get_service([config.ESCOPO_CALENDARIO])

    def executar_json(self, entrada: dict | str) -> dict:
        """Recebe o pedido em JSON, altera o evento e devolve JSON (sem LLM).

        Returns:
            Mesmo formato dos outros agentes. Sucesso: acao "evento_editado" e
            dados {"evento": {...}}. Erro: status "erro" e erro {tipo, mensagem}.
        """
        fluxo = Fluxo(
            inicio=Etapa(etapa="validacao"),
            meio=Etapa(etapa="google_calendar"),
            fim=Etapa(etapa="conferencia"),
        )

        # 1. INÍCIO: valida o pedido.
        try:
            if isinstance(entrada, str):
                pedido = PedidoEdicao.model_validate_json(entrada)
            else:
                pedido = PedidoEdicao.model_validate(entrada)
        except ValidationError as erro:
            fluxo.inicio.status = "erro"
            mensagens = [
                detalhe["msg"].removeprefix("Value error, ")
                for detalhe in erro.errors(include_url=False, include_context=False)
            ]
            return RespostaAgente(
                status="erro",
                acao="evento_nao_editado",
                fluxo=fluxo,
                erro=ErroInfo(tipo="ValidationError", mensagem=" ".join(dict.fromkeys(mensagens))),
            ).model_dump(mode="json")

        alteracoes = montar_alteracoes(pedido)
        fluxo.inicio.status = "ok"
        fluxo.inicio.detalhe = {"evento_id": pedido.id, "campos": sorted(alteracoes)}

        # 2. MEIO: confere que o evento existe e aplica o PATCH.
        try:
            servico = self._service()
            atual = obter_evento(servico, pedido.id)
            if atual.get("status") == "cancelled":
                raise LookupError("Este evento foi excluído.")
            if _move_para_o_passado(pedido, atual):
                raise ValueError("Não é permitido mover eventos para o passado.")
            atualizado = atualizar_evento(servico, pedido.id, alteracoes) if alteracoes else atual
        except Exception as erro:
            fluxo.meio.status = "erro"
            return RespostaAgente(
                status="erro",
                acao="evento_nao_editado",
                fluxo=fluxo,
                erro=ErroInfo(tipo=type(erro).__name__, mensagem=str(erro)),
            ).model_dump(mode="json")

        fluxo.meio.status = "ok"
        fluxo.meio.detalhe = {"evento_id": atualizado.get("id")}

        evento = evento_resumido(atualizado)
        periodo = None
        try:
            inicio = datetime.fromisoformat(str(evento["inicio"]).replace("Z", "+00:00"))
            fim = datetime.fromisoformat(str(evento["fim"]).replace("Z", "+00:00"))
            periodo = Periodo(inicio=inicio, fim=fim, duracao_minutos=(fim - inicio).total_seconds() / 60)
        except (TypeError, ValueError):
            pass

        # 3. FIM: confere se o horário devolvido é o pedido.
        fluxo.fim.status = "ok"
        if pedido.inicio is not None and periodo is not None:
            fluxo.fim.detalhe = {
                "periodo_confere": periodo.inicio == pedido.inicio and periodo.fim == pedido.fim
            }

        return RespostaAgente(
            status="sucesso",
            acao="evento_editado",
            periodo=periodo,
            dados={"evento": evento},
            fluxo=fluxo,
        ).model_dump(mode="json")
