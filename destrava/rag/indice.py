"""
Fase de indexação do RAG:

    base de conhecimento (arquivos) → chunking → embedding dos chunks → armazenamento

Lê os arquivos de uma base (``config.RAG_BASES``), divide em trechos, gera um
embedding por trecho no Ollama (em lotes) e guarda o resultado em disco
(``config.PASTA_INDICES_RAG``).

A cópia em disco só é reaproveitada se os arquivos, os parâmetros de chunking e
o modelo de embeddings forem os mesmos; senão o índice é refeito sozinho. Assim,
editar um arquivo da base não deixa o RAG com conhecimento velho.

Uma base vazia (sem nenhum .md ou .txt) é válida: o índice sai sem trechos.
"""

import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel

from destrava.core import config
from destrava.core.llm_client import ErroLLM, gerar_embeddings
from destrava.rag.banco_vetorial import BancoVetorialLocal
from destrava.rag.chunker import Trecho, dividir_texto


class Indice(BaseModel):
    """Trechos indexados e, se o Ollama estava disponível, o vetor de cada um."""

    assinatura: str
    trechos: list[Trecho]
    embeddings: list[list[float]] | None = None

    def banco_vetorial(self) -> BancoVetorialLocal | None:
        """O banco vetorial deste índice, ou None se não há embeddings."""
        if self.embeddings is None:
            return None
        return BancoVetorialLocal(self.trechos, self.embeddings)


def listar_arquivos(
    fontes: tuple[str, ...] | list[str], raiz: Path | None = None
) -> list[str]:
    """Lista os arquivos da base, em ordem estável, relativos à raiz.

    Cada fonte pode ser um arquivo ou uma pasta; de pasta entram os arquivos
    com extensão de ``config.RAG_EXTENSOES``, inclusive nas subpastas. Arquivos
    e pastas ocultos (nome começando com ".") são ignorados.

    Raises:
        FileNotFoundError: Se alguma fonte não existir.
    """
    raiz = config.RAIZ_PROJETO if raiz is None else raiz
    achados: set[str] = set()

    for fonte in fontes:
        caminho = raiz / fonte
        if caminho.is_file():
            candidatos = [caminho]
        elif caminho.is_dir():
            candidatos = [
                c for c in caminho.rglob("*")
                if c.is_file() and c.suffix.lower() in config.RAG_EXTENSOES
            ]
        else:
            raise FileNotFoundError(
                f"Fonte do RAG não encontrada: {fonte} (procurada em {raiz})."
            )

        for c in candidatos:
            relativo = c.relative_to(raiz)
            if not any(parte.startswith(".") for parte in relativo.parts):
                achados.add(relativo.as_posix())

    return sorted(achados)


def ler_fontes(
    fontes: tuple[str, ...] | list[str], raiz: Path | None = None
) -> dict[str, str]:
    """Lê o texto de cada arquivo da base (nome relativo → conteúdo).

    Raises:
        FileNotFoundError: Se alguma fonte não existir.
        ValueError: Se algum arquivo não estiver em UTF-8.
    """
    raiz = config.RAIZ_PROJETO if raiz is None else raiz
    conteudos: dict[str, str] = {}

    for arquivo in listar_arquivos(fontes, raiz):
        try:
            # utf-8-sig: aceita (e descarta) o BOM que o Bloco de Notas coloca.
            conteudos[arquivo] = (raiz / arquivo).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as erro:
            raise ValueError(f"{arquivo} não está em UTF-8.") from erro
    return conteudos


def calcular_assinatura(conteudos: dict[str, str]) -> str:
    """Impressão digital dos arquivos e dos parâmetros que mudam o índice."""
    base = json.dumps(
        {
            "fontes": conteudos,
            "tamanho_max": config.RAG_TAMANHO_MAX_TRECHO,
            "sobreposicao": config.RAG_SOBREPOSICAO,
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
    """Gera os embeddings dos trechos, em lotes de config.RAG_LOTE_EMBEDDING.

    Args:
        trechos: Trechos a vetorizar.
        usar_embeddings: False não usa embeddings; True exige (propaga o erro
            do Ollama); None tenta e, se o Ollama falhar, segue sem eles.
    """
    if usar_embeddings is False or not trechos:
        return None

    textos = [config.RAG_PREFIXO_DOCUMENTO + t.para_indexar for t in trechos]
    lote = max(1, config.RAG_LOTE_EMBEDDING)
    vetores: list[list[float]] = []
    try:
        for inicio in range(0, len(textos), lote):
            vetores.extend(gerar_embeddings(textos[inicio:inicio + lote]))
    except ErroLLM:
        if usar_embeddings:
            raise
        return None
    return vetores


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
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        temporario.write_text(indice.model_dump_json(), encoding="utf-8")
        os.replace(temporario, arquivo)
    except OSError:
        temporario.unlink(missing_ok=True)


def construir_indice(
    nome: str,
    usar_embeddings: bool | None = None,
    fontes: tuple[str, ...] | list[str] | None = None,
    raiz: Path | None = None,
    arquivo_cache: Path | None = None,
) -> Indice:
    """Monta o índice de uma base, reaproveitando a cópia em disco quando possível.

    Args:
        nome: Nome da base (chave de config.RAG_BASES, ex.: "supervisor"). Dá
            nome ao arquivo da cópia em disco.
        usar_embeddings: None (padrão) tenta gerar os embeddings e, se o Ollama
            ou o modelo não estiverem disponíveis, segue só com palavras-chave.
            True exige os embeddings (levanta ErroLLM se falharem). False nunca
            chama o Ollama.
        fontes: Arquivos/pastas a indexar (padrão: config.RAG_BASES[nome]).
        raiz: Pasta base das fontes (padrão: raiz do projeto).
        arquivo_cache: Onde guardar a cópia (padrão:
            config.PASTA_INDICES_RAG / "<nome>.json").

    Raises:
        ValueError: Se a base não existir em config.RAG_BASES (e as fontes não
            forem informadas) ou se algum arquivo não estiver em UTF-8.
        FileNotFoundError: Se alguma fonte não existir.
        ErroLLM: Só com usar_embeddings=True e Ollama indisponível.
    """
    if fontes is None:
        if nome not in config.RAG_BASES:
            raise ValueError(
                f"Base de conhecimento desconhecida: {nome!r}. "
                f"Bases configuradas: {', '.join(config.RAG_BASES)}."
            )
        fontes = config.RAG_BASES[nome]
    if arquivo_cache is None:
        arquivo_cache = config.PASTA_INDICES_RAG / f"{nome}.json"

    conteudos = ler_fontes(fontes, raiz)
    assinatura = calcular_assinatura(conteudos)

    # 1. Cópia em disco válida: reaproveita. Se ela ficou sem embeddings (Ollama
    #    estava fora) e agora eles são desejados, tenta gerar de novo.
    indice = _ler_cache(arquivo_cache, assinatura)
    if indice is not None:
        if indice.embeddings is None and indice.trechos and usar_embeddings is not False:
            vetores = _gerar_vetores(indice.trechos, usar_embeddings)
            if vetores is not None:
                indice = indice.model_copy(update={"embeddings": vetores})
                _salvar_cache(arquivo_cache, indice)
        return indice

    # 2. Sem cópia válida: divide os arquivos e gera os embeddings.
    trechos = [
        trecho
        for arquivo, conteudo in conteudos.items()
        for trecho in dividir_texto(conteudo, arquivo)
    ]
    indice = Indice(
        assinatura=assinatura,
        trechos=trechos,
        embeddings=_gerar_vetores(trechos, usar_embeddings),
    )
    _salvar_cache(arquivo_cache, indice)
    return indice
