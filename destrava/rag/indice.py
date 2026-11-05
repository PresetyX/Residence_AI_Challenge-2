"""
Índice do RAG do Supervisor: lê as fontes, divide em trechos, gera os
embeddings e guarda uma cópia em disco.

A cópia (config.ARQUIVO_INDICE_RAG) só é reaproveitada se as fontes, o
tamanho dos trechos e o modelo de embeddings forem os mesmos; senão o índice
é refeito sozinho. Assim, editar um .md das fontes não deixa o Supervisor
com conhecimento velho.
"""

import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel

from destrava.core import config
from destrava.core.llm_client import ErroLLM, gerar_embeddings
from destrava.rag.chunker import Trecho, dividir_markdown


class Indice(BaseModel):
    """Trechos indexados e, se o Ollama estava disponível, o vetor de cada um."""

    assinatura: str
    trechos: list[Trecho]
    embeddings: list[list[float]] | None = None


def ler_fontes(
    fontes: tuple[str, ...] | list[str] | None = None, raiz: Path | None = None
) -> dict[str, str]:
    """Lê o texto de cada fonte (caminhos relativos à raiz do projeto).

    Raises:
        FileNotFoundError: Se alguma fonte não existir.
    """
    fontes = config.RAG_FONTES if fontes is None else fontes
    raiz = config.RAIZ_PROJETO if raiz is None else raiz

    conteudos: dict[str, str] = {}
    for fonte in fontes:
        caminho = raiz / fonte
        if not caminho.is_file():
            raise FileNotFoundError(
                f"Fonte do RAG não encontrada: {fonte} (procurada em {raiz})."
            )
        conteudos[fonte] = caminho.read_text(encoding="utf-8")
    return conteudos


def calcular_assinatura(conteudos: dict[str, str]) -> str:
    """Impressão digital das fontes e dos parâmetros que mudam o índice."""
    base = json.dumps(
        {
            "fontes": conteudos,
            "tamanho_max": config.RAG_TAMANHO_MAX_TRECHO,
            "modelo_embedding": config.MODELO_EMBEDDING,
            "prefixo_documento": config.RAG_PREFIXO_DOCUMENTO,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _gerar_vetores(
    trechos: list[Trecho], usar_embeddings: bool | None
) -> list[list[float]] | None:
    """Gera os embeddings dos trechos, conforme o modo pedido.

    Args:
        trechos: Trechos a vetorizar.
        usar_embeddings: False não usa embeddings; True exige (propaga o erro
            do Ollama); None tenta e, se o Ollama falhar, segue sem eles.
    """
    if usar_embeddings is False or not trechos:
        return None

    textos = [config.RAG_PREFIXO_DOCUMENTO + t.para_indexar for t in trechos]
    try:
        return gerar_embeddings(textos)
    except ErroLLM:
        if usar_embeddings:
            raise
        return None


def _ler_cache(arquivo: Path, assinatura: str) -> Indice | None:
    """Devolve o índice salvo se ele for válido e atual; senão, None."""
    try:
        indice = Indice.model_validate_json(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if indice.assinatura != assinatura:
        return None
    if indice.embeddings is not None and len(indice.embeddings) != len(indice.trechos):
        return None
    return indice


def _salvar_cache(arquivo: Path, indice: Indice) -> None:
    """Salva o índice em disco. Falha de escrita não é erro: o índice só será refeito."""
    temporario = arquivo.with_suffix(arquivo.suffix + ".tmp")
    try:
        temporario.write_text(indice.model_dump_json(), encoding="utf-8")
        os.replace(temporario, arquivo)
    except OSError:
        temporario.unlink(missing_ok=True)


def construir_indice(
    usar_embeddings: bool | None = None,
    fontes: tuple[str, ...] | list[str] | None = None,
    raiz: Path | None = None,
    arquivo_cache: Path | None = None,
) -> Indice:
    """Monta o índice do RAG, reaproveitando a cópia em disco quando possível.

    Args:
        usar_embeddings: None (padrão) tenta gerar os embeddings e, se o Ollama
            ou o modelo não estiverem disponíveis, segue só com palavras-chave.
            True exige os embeddings (levanta ErroLLM se falharem). False nunca
            chama o Ollama.
        fontes: Arquivos a indexar (padrão: config.RAG_FONTES).
        raiz: Pasta base das fontes (padrão: raiz do projeto).
        arquivo_cache: Onde guardar a cópia (padrão: config.ARQUIVO_INDICE_RAG).

    Raises:
        FileNotFoundError: Se alguma fonte não existir.
        ErroLLM: Só com usar_embeddings=True e Ollama indisponível.
    """
    arquivo_cache = config.ARQUIVO_INDICE_RAG if arquivo_cache is None else arquivo_cache

    conteudos = ler_fontes(fontes, raiz)
    assinatura = calcular_assinatura(conteudos)

    # 1. Cópia em disco válida: reaproveita. Se ela ficou sem embeddings (Ollama
    #    estava fora) e agora eles são desejados, tenta gerar de novo.
    indice = _ler_cache(arquivo_cache, assinatura)
    if indice is not None:
        if indice.embeddings is None and usar_embeddings is not False:
            vetores = _gerar_vetores(indice.trechos, usar_embeddings)
            if vetores is not None:
                indice = indice.model_copy(update={"embeddings": vetores})
                _salvar_cache(arquivo_cache, indice)
        return indice

    # 2. Sem cópia válida: divide as fontes e gera os embeddings.
    trechos = [
        trecho
        for fonte, conteudo in conteudos.items()
        for trecho in dividir_markdown(conteudo, fonte)
    ]
    indice = Indice(
        assinatura=assinatura,
        trechos=trechos,
        embeddings=_gerar_vetores(trechos, usar_embeddings),
    )
    _salvar_cache(arquivo_cache, indice)
    return indice
