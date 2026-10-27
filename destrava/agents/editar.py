"""Regras de negócio do agente responsável por editar eventos."""

import json
import re
from datetime import datetime, timedelta
from typing import Any

from destrava.core import config
from destrava.core.google_client import get_evento, update_evento
from destrava.core.llm_client import perguntar
from destrava.prompts.editar import PROMPT_EXTRACAO


def _corrigir_periodo_do_dia(
    alteracoes: dict[str, Any],
    pedido: str,
) -> dict[str, Any]:
    """Corrige horários de 12 horas que o modelo tenha convertido errado."""
    correspondencia = re.search(
        r"\b(?:da|de)\s+(tarde|noite)\b",
        pedido,
        flags=re.IGNORECASE,
    )
    if not correspondencia:
        return alteracoes

    resultado = dict(alteracoes)
    for campo in ("start", "end"):
        valor = resultado.get(campo)
        if not isinstance(valor, dict):
            continue
        data_hora = valor.get("dateTime")
        if not isinstance(data_hora, str):
            continue
        try:
            horario = datetime.fromisoformat(data_hora)
        except ValueError:
            continue
        if horario.hour < 12:
            resultado[campo] = {
                **valor,
                "dateTime": horario.replace(hour=horario.hour + 12).isoformat(),
            }
    return resultado


def _validar_intervalo(evento: dict[str, Any]) -> None:
    inicio = evento.get("start", {}).get("dateTime")
    fim = evento.get("end", {}).get("dateTime")
    if not isinstance(inicio, str) or not isinstance(fim, str):
        return
    try:
        inicio_dt = datetime.fromisoformat(inicio)
        fim_dt = datetime.fromisoformat(fim)
    except ValueError as erro:
        raise ValueError(
            "O início e o fim do evento devem usar datas RFC 3339 válidas."
        ) from erro
    if fim_dt <= inicio_dt:
        raise ValueError(
            "A alteração deixaria o fim do evento antes ou igual ao início. "
            "Verifique a data e o horário informados."
        )


def _ajustar_data_de_horario(
    alteracoes: dict[str, Any],
    evento_atual: dict[str, Any],
    pedido: str,
) -> dict[str, Any]:
    """Resolve a data quando o pedido altera um horário."""
    pedido_lower = pedido.lower()
    data_explicita = re.search(
        r"\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}",
        pedido,
    )
    if data_explicita:
        return alteracoes

    hoje = datetime.now(config.FUSO).date()
    data_forcada = None
    mover_evento_inteiro = False
    if re.search(r"\bdepois\s+de\s+amanh[ãa]\b", pedido_lower):
        data_forcada = hoje + timedelta(days=2)
        mover_evento_inteiro = "data do evento" in pedido_lower
    elif re.search(r"\bamanh[ãa]\b", pedido_lower):
        data_forcada = hoje + timedelta(days=1)
        mover_evento_inteiro = "data do evento" in pedido_lower
    elif re.search(r"\bhoje\b", pedido_lower):
        data_forcada = hoje
        mover_evento_inteiro = "data do evento" in pedido_lower

    resultado = dict(alteracoes)
    if mover_evento_inteiro:
        for campo in ("start", "end"):
            valor_atual = evento_atual.get(campo)
            if not isinstance(valor_atual, dict):
                continue
            data_hora_atual = valor_atual.get("dateTime")
            if not isinstance(data_hora_atual, str):
                continue
            try:
                data_hora_atual_dt = datetime.fromisoformat(data_hora_atual)
            except ValueError:
                continue
            novo_valor = dict(resultado.get(campo, valor_atual))
            novo_valor["dateTime"] = data_hora_atual_dt.replace(
                year=data_forcada.year,
                month=data_forcada.month,
                day=data_forcada.day,
            ).isoformat()
            resultado[campo] = novo_valor
        return resultado

    for campo in ("start", "end"):
        novo_valor = resultado.get(campo)
        valor_atual = evento_atual.get(campo)
        if not isinstance(novo_valor, dict) or not isinstance(valor_atual, dict):
            continue

        nova_data_hora = novo_valor.get("dateTime")
        data_hora_atual = valor_atual.get("dateTime")
        if not isinstance(nova_data_hora, str) or not isinstance(
            data_hora_atual, str
        ):
            continue
        try:
            nova_data_hora_dt = datetime.fromisoformat(nova_data_hora)
            data_hora_atual_dt = datetime.fromisoformat(data_hora_atual)
        except ValueError:
            continue

        if data_forcada is None:
            data_forcada = data_hora_atual_dt.date()

        resultado[campo] = {
            **novo_valor,
            "dateTime": nova_data_hora_dt.replace(
                year=data_forcada.year,
                month=data_forcada.month,
                day=data_forcada.day,
            ).isoformat(),
        }
    return resultado


def interpretar_pedido(pedido: str) -> dict[str, Any]:
    """Converte um pedido em linguagem natural no contrato de edição."""
    if not isinstance(pedido, str) or not pedido.strip():
        raise ValueError("pedido deve ser uma string não vazia.")

    prompt = PROMPT_EXTRACAO.format(
        data_de_hoje=datetime.now(config.FUSO).date().isoformat(),
        fuso=str(config.FUSO),
        pergunta_do_usuario=pedido.strip(),
    )
    resposta = perguntar(prompt).strip()
    if resposta.startswith("```"):
        linhas = resposta.splitlines()
        resposta = "\n".join(linhas[1:-1]).strip()

    try:
        dados = json.loads(resposta)
    except json.JSONDecodeError as erro:
        raise ValueError(
            "O modelo não retornou um JSON válido para a edição."
        ) from erro

    if not isinstance(dados, dict):
        raise ValueError("A interpretação do pedido deve ser um objeto JSON.")

    evento_id = dados.get("evento_id")
    alteracoes = dados.get("alteracoes")
    if not isinstance(evento_id, str) or not evento_id.strip():
        raise ValueError("Não foi possível identificar o ID do evento.")
    if not isinstance(alteracoes, dict) or not alteracoes:
        raise ValueError("Não foi possível identificar alterações no pedido.")

    return {
        "evento_id": evento_id.strip(),
        "alteracoes": _corrigir_periodo_do_dia(alteracoes, pedido),
    }


def editar_evento_agenda(
    servico: Any,
    pedido: str,
    *,
    id_calendario: str = "primary",
) -> dict[str, Any]:
    """Interpreta um pedido, aplica as alterações e retorna um resumo."""
    dados = interpretar_pedido(pedido)
    evento_atualizado, alteracoes_aplicadas = _editar_evento(
        servico,
        dados["evento_id"],
        dados["alteracoes"],
        id_calendario=id_calendario,
        pedido=pedido,
    )
    return {
        "evento": evento_atualizado,
        "alteracoes": alteracoes_aplicadas,
    }


def _editar_evento(
    servico: Any,
    evento_id: str,
    alteracoes: dict[str, Any],
    *,
    id_calendario: str,
    pedido: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    evento_atual = get_evento(
        servico,
        evento_id,
        id_calendario=id_calendario,
    )
    descricao = evento_atual.get("description", "")
    if (
        evento_atual.get("eventType") == "focusTime"
        and isinstance(descricao, str)
        and "tasks.google.com" in descricao
    ):
        raise ValueError(
            f"O evento {evento_id!r} é uma tarefa do Google Tasks "
            "exibida no Calendar. Edite-a pela Google Tasks API; "
            "o Calendar API não salva alterações no título, descrição "
            "ou anexos desse item."
        )
    if pedido is not None:
        alteracoes = _ajustar_data_de_horario(
            alteracoes,
            evento_atual,
            pedido,
        )
    evento_atualizado = {**evento_atual, **alteracoes}
    _validar_intervalo(evento_atualizado)
    resultado = update_evento(
        servico,
        evento_id,
        evento_atualizado,
        id_calendario=id_calendario,
    )
    return resultado, alteracoes


def editar_eventos(
    servico: Any,
    eventos: list[dict[str, Any]],
    *,
    id_calendario: str = "primary",
    pedido: str | None = None,
) -> list[dict[str, Any]]:
    """Busca e atualiza cada evento recebido, nessa ordem.

    Cada item deve conter ``id`` e ``alteracoes``. O GET fornece a versão mais
    recente do evento; as alterações são mescladas superficialmente antes do
    UPDATE para preservar os campos que não foram solicitados.
    """
    if not isinstance(eventos, list):
        raise TypeError("eventos deve ser uma lista.")

    resultados: list[dict[str, Any]] = []
    for item in eventos:
        if not isinstance(item, dict):
            raise TypeError("Cada evento deve ser um dicionário.")

        evento_id = item.get("id")
        alteracoes = item.get("alteracoes")
        if not isinstance(evento_id, str) or not evento_id.strip():
            raise ValueError("Cada evento deve conter um id não vazio.")
        if not isinstance(alteracoes, dict):
            raise ValueError(
                f"O evento {evento_id!r} deve conter um objeto 'alteracoes'."
            )

        evento_atualizado, _ = _editar_evento(
            servico,
            evento_id,
            alteracoes,
            id_calendario=id_calendario,
            pedido=pedido,
        )
        resultados.append(evento_atualizado)

    return resultados