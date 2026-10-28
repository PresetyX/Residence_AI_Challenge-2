"""Agente responsável por excluir eventos do Google Calendar."""

from __future__ import annotations

import json
import unicodedata
from datetime import date, datetime, time, timedelta
from typing import Any

from ..core import config
from ..core.google_client import get_service, listar_eventos
from ..core.llm_client import ErroLLM, perguntar
from ..prompts.excluir import PROMPT_EXTRACAO, PROMPT_RESPOSTA


__all__ = ["excluir_evento_agenda"]


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto para facilitar a comparação de títulos."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    return " ".join(texto.casefold().split())


def _carregar_json_resposta(texto: str) -> dict[str, Any]:
    """Converte a resposta do LLM em dicionário, tolerando blocos ```json```."""
    resposta = texto.strip()

    if resposta.startswith("```"):
        linhas = resposta.splitlines()
        if linhas:
            linhas = linhas[1:]
        if linhas and linhas[-1].strip().startswith("```"):
            linhas = linhas[:-1]
        resposta = "\n".join(linhas).strip()

    # Caso o modelo escreva algum texto extra, tenta aproveitar somente o JSON.
    inicio_json = resposta.find("{")
    fim_json = resposta.rfind("}")
    if inicio_json != -1 and fim_json > inicio_json:
        resposta = resposta[inicio_json : fim_json + 1]

    try:
        dados = json.loads(resposta)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "O modelo não retornou um JSON válido para identificar o evento."
        ) from exc

    if not isinstance(dados, dict):
        raise ValueError("A resposta do modelo deve ser um objeto JSON.")

    return dados


def _extrair_pedido(pedido: str) -> tuple[str | None, date | None, time | None]:
    """Usa o LLM para extrair título, data e horário do pedido."""
    agora = datetime.now(config.FUSO)

    prompt = PROMPT_EXTRACAO.format(
        data_de_hoje=agora.date().isoformat(),
        fuso=str(config.FUSO),
        pergunta_do_usuario=pedido,
    )

    dados = _carregar_json_resposta(perguntar(prompt))

    titulo_bruto = dados.get("titulo")
    data_bruta = dados.get("data")
    horario_bruto = dados.get("horario")

    titulo: str | None = None
    if isinstance(titulo_bruto, str) and titulo_bruto.strip():
        titulo = titulo_bruto.strip()
    elif titulo_bruto is not None:
        raise ValueError("O campo 'titulo' retornado pelo modelo é inválido.")

    data_evento: date | None = None
    if isinstance(data_bruta, str) and data_bruta.strip():
        try:
            data_evento = date.fromisoformat(data_bruta.strip())
        except ValueError as exc:
            raise ValueError(
                "O campo 'data' retornado pelo modelo não está no formato AAAA-MM-DD."
            ) from exc
    elif data_bruta is not None:
        raise ValueError("O campo 'data' retornado pelo modelo é inválido.")

    horario_evento: time | None = None
    if isinstance(horario_bruto, str) and horario_bruto.strip():
        try:
            horario_evento = time.fromisoformat(horario_bruto.strip())
        except ValueError as exc:
            raise ValueError(
                "O campo 'horario' retornado pelo modelo não está no formato HH:MM."
            ) from exc
    elif horario_bruto is not None:
        raise ValueError("O campo 'horario' retornado pelo modelo é inválido.")

    return titulo, data_evento, horario_evento


def _inicio_evento(evento: dict[str, Any]) -> datetime | None:
    """Retorna o início do evento no fuso configurado, quando houver horário."""
    inicio = evento.get("start", {})
    if not isinstance(inicio, dict):
        return None

    valor = inicio.get("dateTime")
    if not isinstance(valor, str) or not valor.strip():
        return None

    try:
        momento = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None

    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=config.FUSO)

    return momento.astimezone(config.FUSO)


def _evento_compativel(
    evento: dict[str, Any],
    titulo: str | None,
    horario: time | None,
) -> bool:
    """Verifica se um evento combina com os dados extraídos do pedido."""
    if titulo:
        titulo_pedido = _normalizar_texto(titulo)
        titulo_evento = _normalizar_texto(str(evento.get("summary", "")))

        if not titulo_evento:
            return False

        # Aceita igualdade e também títulos como "Consulta Dentista" para o
        # pedido "dentista".
        if titulo_pedido not in titulo_evento and titulo_evento not in titulo_pedido:
            return False

    if horario:
        inicio = _inicio_evento(evento)
        if inicio is None:
            return False

        if (inicio.hour, inicio.minute) != (horario.hour, horario.minute):
            return False

    return True


def _descricao_evento(evento: dict[str, Any]) -> str:
    """Cria uma descrição curta para mensagens de ambiguidade."""
    titulo = str(evento.get("summary") or "Evento sem título")
    inicio = evento.get("start", {})

    if isinstance(inicio, dict):
        data_hora = inicio.get("dateTime")
        data_inteira = inicio.get("date")

        if isinstance(data_hora, str):
            try:
                momento = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
                if momento.tzinfo is None:
                    momento = momento.replace(tzinfo=config.FUSO)
                momento = momento.astimezone(config.FUSO)
                return f"{titulo} - {momento.strftime('%d/%m às %H:%M')}"
            except ValueError:
                pass

        if isinstance(data_inteira, str):
            try:
                dia = date.fromisoformat(data_inteira)
                return f"{titulo} - {dia.strftime('%d/%m')} (dia inteiro)"
            except ValueError:
                pass

    return titulo


def _dados_evento_excluido(evento: dict[str, Any]) -> dict[str, Any]:
    """Seleciona somente dados úteis para a resposta final."""
    return {
        "titulo": evento.get("summary") or "Evento sem título",
        "inicio": evento.get("start"),
        "fim": evento.get("end"),
    }


def excluir_evento_agenda(pedido: str) -> str:
    """Exclui um evento da agenda a partir de um pedido em linguagem natural.

    Fluxo:
        1. O LLM extrai título, data e horário.
        2. O código consulta o Google Calendar.
        3. O código filtra os eventos compatíveis.
        4. Só exclui quando existe exatamente um candidato.
        5. O LLM redige a confirmação final.

    Args:
        pedido: Pedido do usuário, por exemplo
            "cancele o dentista de amanhã".

    Returns:
        Mensagem em português informando o resultado.
    """
    if not isinstance(pedido, str):
        raise TypeError("O pedido deve ser uma string.")

    pedido = pedido.strip()
    if not pedido:
        raise ValueError("O pedido não pode estar vazio.")

    try:
        titulo, data_evento, horario = _extrair_pedido(pedido)
    except ErroLLM as exc:
        return f"Não consegui interpretar o pedido porque o modelo de IA falhou: {exc}"
    except ValueError as exc:
        return f"Não consegui interpretar o pedido com segurança: {exc}"

    # Para evitar buscar e apagar eventos em um intervalo indefinido, a data é
    # obrigatória nesta primeira versão do agente.
    if data_evento is None:
        return (
            "Preciso saber a data do evento antes de excluí-lo. "
            "Por exemplo: 'cancele o dentista de amanhã'."
        )

    # Sem título e sem horário não há informação suficiente para escolher um
    # evento com segurança.
    if titulo is None and horario is None:
        return (
            "Não consegui identificar qual evento você quer excluir. "
            "Informe o nome do evento ou o horário."
        )

    inicio_busca = datetime.combine(data_evento, time.min).replace(
        tzinfo=config.FUSO
    )
    fim_busca = inicio_busca + timedelta(days=1)

    try:
        servico = get_service([config.ESCOPO_CALENDARIO])
        eventos = listar_eventos(
            servico,
            inicio_busca.isoformat(),
            fim_busca.isoformat(),
        )
    except Exception as exc:
        return f"Não consegui consultar o Google Calendar: {exc}"

    candidatos = [
        evento
        for evento in eventos
        if _evento_compativel(evento, titulo, horario)
    ]

    if not candidatos:
        detalhes = []
        if titulo:
            detalhes.append(f"com o título '{titulo}'")
        if horario:
            detalhes.append(f"às {horario.strftime('%H:%M')}")

        identificacao = " ".join(detalhes)
        return (
            f"Não encontrei nenhum evento {identificacao} "
            f"em {data_evento.strftime('%d/%m/%Y')}."
        ).replace("  ", " ")

    if len(candidatos) > 1:
        opcoes = "\n".join(
            f"- {_descricao_evento(evento)}" for evento in candidatos[:5]
        )
        complemento = ""
        if len(candidatos) > 5:
            complemento = f"\n- ... e mais {len(candidatos) - 5} evento(s)."

        return (
            "Encontrei mais de um evento compatível e não excluí nenhum. "
            "Informe mais detalhes, como o horário ou o título completo:\n"
            f"{opcoes}{complemento}"
        )

    evento = candidatos[0]
    id_evento = evento.get("id")

    if not isinstance(id_evento, str) or not id_evento.strip():
        return "Encontrei o evento, mas ele não possui um identificador válido para exclusão."

    dados_excluidos = _dados_evento_excluido(evento)

    try:
        # Nesta versão, a chamada DELETE fica no agente. Se o grupo quiser
        # centralizar todas as operações da API no core, este trecho pode ser
        # movido depois para uma função excluir_evento() em google_client.py.
        servico.events().delete(
            calendarId="primary",
            eventId=id_evento,
        ).execute()
    except Exception as exc:
        return f"Encontrei o evento, mas não consegui excluí-lo do Google Calendar: {exc}"

    prompt_resposta = PROMPT_RESPOSTA.format(
        evento_excluido=json.dumps(
            dados_excluidos,
            ensure_ascii=False,
            default=str,
        ),
        pergunta_do_usuario=pedido,
    )

    try:
        return perguntar(prompt_resposta)
    except ErroLLM:
        # A exclusão já aconteceu. Se o LLM falhar neste ponto, é importante
        # não dar a impressão de que a operação falhou.
        return f"O evento '{dados_excluidos['titulo']}' foi excluído com sucesso."
