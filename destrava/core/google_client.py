"""
Cliente compartilhado para autenticação e acesso ao Google Calendar.

  O que este arquivo faz:
    - Autenticação OAuth e criação do service do Google Calendar
    - Funções básicas de acesso à API (sem regras de negócio dos agentes)

  Decisão do grupo sobre escopos:
    get_service(escopos) recebe o escopo como PARÂMETRO, e cada agente pede
    apenas o que precisa (princípio do menor privilégio):
      - visualizar -> https://www.googleapis.com/auth/calendar.readonly
      - criar / editar / excluir -> https://www.googleapis.com/auth/calendar
    Assim, o agente de visualização continua sem permissão de escrita.

  Tokens:
    Cada nível de escopo usa o seu próprio token (ex.: token_readonly.json e
    token_calendar.json), pois um token só vale para os escopos autorizados.

  Segurança:
    credentials.json e token*.json NUNCA devem ir para o Git (já estão no .gitignore).
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from . import config


def _arquivo_token(escopos: Sequence[str]) -> str:
    """Retorna o nome do arquivo de token associado às permissões solicitadas."""
    if set(escopos) == {config.ESCOPO_SOMENTE_LEITURA}:
        return config.ARQUIVO_TOKEN_SOMENTE_LEITURA
    return config.ARQUIVO_TOKEN_CALENDARIO


def get_service(
    escopos: Sequence[str],
) -> Resource:
    """Autentica o usuário e retorna um serviço da API do Google Calendar.

    O arquivo do cliente OAuth deve ser salvo como ``credentials.json`` na raiz
    do projeto. O token de atualização é armazenado na raiz do projeto para
    que chamadas posteriores não exijam uma nova autorização no navegador.
    Escopos somente leitura e com permissão de escrita usam arquivos de token
    diferentes para evitar reutilizar um token com permissões insuficientes.
    """
    escopos_solicitados = tuple(dict.fromkeys(escopos))
    if not escopos_solicitados:
        raise ValueError("Ao menos um escopo OAuth deve ser informado.")

    caminho_token = config.RAIZ_PROJETO / _arquivo_token(escopos_solicitados)

    if not config.ARQUIVO_CREDENCIAIS.exists():
        raise FileNotFoundError(
            f"Arquivo OAuth não encontrado: {config.ARQUIVO_CREDENCIAIS}. "
            "Baixe-o no Google Cloud Console antes de executar o teste."
        )
    
    credentials: Credentials | None = None
    if caminho_token.exists():
        credentials = Credentials.from_authorized_user_file(
            str(caminho_token), escopos_solicitados
        )

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.ARQUIVO_CREDENCIAIS), escopos_solicitados
            )
            credentials = flow.run_local_server(port=0)

        with caminho_token.open("w", encoding="utf-8") as arquivo_token:
            arquivo_token.write(credentials.to_json())

    return build("calendar", "v3", credentials=credentials)


def listar_eventos(
    servico: Resource,
    inicio: str,
    fim: str,
    *,
    id_calendario: str = "primary",
) -> list[dict[str, Any]]:
    """Retorna todos os eventos que se sobrepõem ao intervalo informado.

    ``inicio`` e ``fim`` usam o formato ISO 8601, por exemplo
    ``"2026-10-27T00:00"``. Datas e horas sem deslocamento explícito são
    tratadas como UTC, conforme exigido pelos parâmetros RFC 3339 da API do
    Google Calendar. Os eventos são incluídos quando seu fim é posterior a
    ``inicio`` e seu início é anterior a ``fim``.
    """
    try:
        horario_inicio = datetime.datetime.fromisoformat(inicio)
        horario_fim = datetime.datetime.fromisoformat(fim)
    except ValueError as erro:
        raise ValueError("inicio e fim devem usar o formato ISO 8601.") from erro

    if horario_inicio.tzinfo is None:
        horario_inicio = horario_inicio.replace(tzinfo=datetime.timezone.utc)
    if horario_fim.tzinfo is None:
        horario_fim = horario_fim.replace(tzinfo=datetime.timezone.utc)
    if horario_inicio >= horario_fim:
        raise ValueError("inicio deve ser anterior a fim.")

    eventos: list[dict[str, Any]] = []
    token_pagina: str | None = None
    while True:
        requisicao = servico.events().list(
            calendarId=id_calendario,
            # A API do Calendar usa o fim do evento para timeMin e o início
            # para timeMax, portanto eventos que atravessam o período são incluídos.
            timeMin=horario_inicio.isoformat(),
            timeMax=horario_fim.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            pageToken=token_pagina,
        )
        resultado_eventos = requisicao.execute()
        eventos.extend(resultado_eventos.get("items", []))
        token_pagina = resultado_eventos.get("nextPageToken")
        if not token_pagina:
            return eventos
