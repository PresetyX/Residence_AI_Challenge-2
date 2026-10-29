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
    """Escolhe o arquivo de token de acordo com as permissões pedidas.

    Um token só vale para os escopos que foram autorizados. Por isso,
    leitura e escrita usam arquivos separados: assim o agente de escrita
    nunca carrega por engano um token que só permite leitura.

    Args:
        escopos: escopos OAuth pedidos pelo agente.

    Returns:
        Nome do arquivo de token: config.ARQUIVO_TOKEN_SOMENTE_LEITURA se o
        único escopo for o de leitura; config.ARQUIVO_TOKEN_CALENDARIO nos
        demais casos.
    """
    if set(escopos) == {config.ESCOPO_SOMENTE_LEITURA}:
        return config.ARQUIVO_TOKEN_SOMENTE_LEITURA
    return config.ARQUIVO_TOKEN_CALENDARIO


def get_service(
    escopos: Sequence[str],
) -> Resource:
    """Autentica o usuário e devolve a conexão com a API do Google Calendar.

    Fluxo do login:
        A. Token salvo e válido     -> usa direto, sem abrir nada.
        B. Token expirado           -> renova sozinho com o refresh token.
        C. Sem token (1ª vez)       -> abre o navegador para o usuário
                                       autorizar e salva o token novo.

    O ``credentials.json`` (identificação do projeto no Google Cloud) deve
    estar na raiz do projeto. O token é salvo também na raiz.

    Args:
        escopos: lista de escopos OAuth que o agente precisa, por exemplo
            ``[config.ESCOPO_SOMENTE_LEITURA]``. Passe sempre uma lista:
            uma string solta seria lida letra por letra.

    Returns:
        Objeto ``Resource`` da API do Google Calendar (versão 3), usado
        pelas funções que consultam ou alteram eventos.

    Raises:
        ValueError: se nenhum escopo for informado.
        FileNotFoundError: se o ``credentials.json`` não estiver na raiz.
        google.auth.exceptions.RefreshError: se o token não puder ser
            renovado (ex.: acesso revogado). Apagar o arquivo de token
            força um novo login.
    """
    # Remove escopos repetidos, mantendo a ordem.
    escopos_solicitados = tuple(dict.fromkeys(escopos))
    if not escopos_solicitados:
        raise ValueError("Ao menos um escopo OAuth deve ser informado.")

    # Cada nível de permissão tem o seu arquivo de token.
    caminho_token = config.RAIZ_PROJETO / _arquivo_token(escopos_solicitados)

    # 1. Verifica que o credentials existe
    if not config.ARQUIVO_CREDENCIAIS.exists():
        raise FileNotFoundError(
            f"Arquivo OAuth não encontrado: {config.ARQUIVO_CREDENCIAIS}. "
            "Baixe-o no Google Cloud Console antes de executar o teste."
        )

    # 2. Tenta carregar o token salvo de um login anterior.
    credentials: Credentials | None = None
    if caminho_token.exists():
        credentials = Credentials.from_authorized_user_file(
            str(caminho_token), escopos_solicitados
        )

    # 3. Só faz login ou renovação se não houver token válido (caminho A pula).
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            # Caminho B: o token expirou (dura cerca de 1 hora), mas o
            # refresh token permite pedir um novo sem abrir o navegador.
            credentials.refresh(Request())
        else:
            # Caminho C: primeira vez (ou token inválido). Abre o navegador,
            # o usuário clica em "Permitir" e o Google devolve a autorização
            # para um mini servidor local (port=0 = porta livre qualquer).
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.ARQUIVO_CREDENCIAIS), escopos_solicitados
            )
            credentials = flow.run_local_server(port=0)

        # 4. Salva o token novo ou renovado para o próximo uso (caminho A).
        with caminho_token.open("w", encoding="utf-8") as arquivo_token:
            arquivo_token.write(credentials.to_json())

    # 5. Cria a conexão com a API do Google Calendar, versão 3.
    return build("calendar", "v3", credentials=credentials)


def listar_eventos(
    servico: Resource,
    inicio: str,
    fim: str,
    *,
    id_calendario: str = "primary",
) -> list[dict[str, Any]]:
    """Devolve todos os eventos que se sobrepõem ao período informado.

    Um evento entra no resultado quando o fim dele é depois de ``inicio`` e
    o começo dele é antes de ``fim``. Assim, um evento que começou antes do
    período e ainda está acontecendo também aparece.

    Eventos recorrentes (ex.: aula toda segunda) vêm expandidos: cada
    ocorrência aparece como um evento separado.

    Args:
        servico: conexão devolvida por ``get_service``.
        inicio: começo do período em ISO 8601, por exemplo
            ``"2026-10-29T00:00:00-03:00"``. Sem fuso, é tratado como UTC
            (3 horas de diferença de São Paulo): prefira sempre enviar o fuso.
        fim: fim do período, no mesmo formato.
        id_calendario: agenda a consultar. ``"primary"`` é a agenda principal
            da conta autorizada.

    Returns:
        Lista de eventos no formato bruto da API do Google (dicionários com
        ``id``, ``summary``, ``start``, ``end`` etc.), em ordem de início.

    Raises:
        ValueError: se ``inicio`` ou ``fim`` não estiverem em ISO 8601 ou se
            ``inicio`` não for anterior a ``fim``.
        googleapiclient.errors.HttpError: se a API do Google recusar a
            consulta (ex.: sem permissão ou agenda inexistente).
    """
    # Converte o texto em data para validar o formato.
    try:
        horario_inicio = datetime.datetime.fromisoformat(inicio)
        horario_fim = datetime.datetime.fromisoformat(fim)
    except ValueError as erro:
        raise ValueError("inicio e fim devem usar o formato ISO 8601.") from erro

    # A API exige data com fuso: sem fuso, assume UTC.
    if horario_inicio.tzinfo is None:
        horario_inicio = horario_inicio.replace(tzinfo=datetime.timezone.utc)
    if horario_fim.tzinfo is None:
        horario_fim = horario_fim.replace(tzinfo=datetime.timezone.utc)
    if horario_inicio >= horario_fim:
        raise ValueError("inicio deve ser anterior a fim.")

    # O Google devolve os eventos em páginas (lotes). O laço pede página
    # por página até não haver mais nenhuma (nextPageToken vazio).
    eventos: list[dict[str, Any]] = []
    token_pagina: str | None = None
    while True:
        requisicao = servico.events().list(
            calendarId=id_calendario,
            # A API do Calendar usa o fim do evento para timeMin e o início
            # para timeMax, portanto eventos que atravessam o período são incluídos.
            timeMin=horario_inicio.isoformat(),
            timeMax=horario_fim.isoformat(),
            singleEvents=True,  # expande eventos recorrentes em ocorrências
            orderBy="startTime",  # ordena pelo horário de início
            pageToken=token_pagina,
        )
        resultado_eventos = requisicao.execute()
        eventos.extend(resultado_eventos.get("items", []))
        token_pagina = resultado_eventos.get("nextPageToken")
        if not token_pagina:
            return eventos
