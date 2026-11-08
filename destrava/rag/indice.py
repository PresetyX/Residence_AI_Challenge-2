"""
Fase de indexação do RAG:

    base de conhecimento (arquivos) → chunking → embedding dos chunks → armazenamento

Lê os arquivos de uma base (``config.RAG_BASES``), divide em trechos e
sincroniza o banco vetorial (Chroma) com a **Indexing API do LangChain**
(``langchain_core.indexing.index``).

Como a Indexing API evita trabalho repetido:
    - Cada trecho vira um ``Document`` do LangChain. A API calcula um hash do
      conteúdo + metadados de cada um e o usa como ID.
    - Um ``RecordManager`` (aqui, ``SQLRecordManager``, num arquivo SQLite) anota
      quais hashes já estão no banco vetorial.
    - A cada execução, todos os trechos atuais são entregues à API. Ela:
        * pula os que já estão no banco (hash conhecido): nenhum embedding novo;
        * adiciona os novos ou alterados (só eles passam pelo Ollama);
        * apaga do banco os que não vieram desta vez (``cleanup="full"``):
          trechos de arquivos editados ou apagados.
  Resultado: editar um arquivo da base só gera embeddings dos trechos que
  mudaram, e o RAG nunca fica com conhecimento velho.

O que fica em disco (``config.PASTA_INDICES_RAG``, no .gitignore):

    .rag_indices/<base>/<assinatura do modelo>/chroma/          banco vetorial
    .rag_indices/<base>/<assinatura do modelo>/registro.sqlite  RecordManager

A "assinatura do modelo" é um hash do modelo de embeddings e do prefixo de
documento. Trocar qualquer um deles muda TODOS os vetores (e às vezes até o
tamanho deles), então isso cria uma pasta nova, e a antiga é apagada.

O chunking roda a cada execução (é rápido: só texto). O que a Indexing API
poupa é a parte cara, os embeddings. Os trechos do chunking também alimentam o
BM25, que funciona mesmo sem o Ollama.

Uma base vazia (sem nenhum .md ou .txt) é válida: o índice sai sem trechos.
"""

import hashlib
import json
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from langchain_classic.indexes import SQLRecordManager
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.indexing import index
from sqlalchemy.engine import URL

from destrava.core import config
from destrava.core.llm_client import ErroLLM, criar_embeddings
from destrava.rag.banco_vetorial import BancoVetorial
from destrava.rag.chunker import Trecho, dividir_texto


@dataclass
class Indice:
    """Trechos de uma base e, se o Ollama estava disponível, o banco vetorial deles.

    Attributes:
        trechos: Todos os trechos da base, na ordem dos arquivos. O BM25 usa
            esta lista, e as buscas devolvem posições nela.
        banco: Banco vetorial sincronizado com ``trechos``, ou None (Ollama fora
            do ar, ``usar_embeddings=False`` ou base vazia). None = o RAG busca
            só por palavras-chave.
        estatisticas: O que a Indexing API fez nesta execução: quantos trechos
            adicionou, pulou (já estavam no banco), atualizou e apagou.
    """

    trechos: list[Trecho]
    banco: BancoVetorial | None = None
    estatisticas: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Mapa (fonte, posição no arquivo) → posição em `trechos`. É assim que
        # um documento devolvido pelo Chroma é ligado de volta ao Trecho.
        self._posicoes = {chave: i for i, chave in enumerate(_chaves(self.trechos))}

    def posicao(self, documento: Document) -> int | None:
        """Posição em ``trechos`` de um documento do banco vetorial (None se não houver)."""
        chave = (documento.metadata.get("fonte"), documento.metadata.get("posicao"))
        return self._posicoes.get(chave)


def _chaves(trechos: list[Trecho]) -> list[tuple[str, int]]:
    """Identifica cada trecho por (arquivo, posição dentro do arquivo).

    Por que posição DENTRO do arquivo, e não na lista inteira: a chave entra
    nos metadados e, portanto, no hash da Indexing API. Com a posição global,
    editar o primeiro arquivo deslocaria a posição de todos os trechos dos
    arquivos seguintes, e todos seriam "novos" (embeddings refeitos à toa).
    Assim, só os trechos do arquivo editado mudam.
    """
    contagem: Counter[str] = Counter()
    chaves = []
    for trecho in trechos:
        chaves.append((trecho.fonte, contagem[trecho.fonte]))
        contagem[trecho.fonte] += 1
    return chaves


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
    # `set` evita duplicata quando uma pasta e um arquivo dentro dela são
    # listados juntos nas fontes.
    achados: set[str] = set()

    for fonte in fontes:
        caminho = raiz / fonte
        # Um arquivo explícito entra sem filtro de extensão; já os arquivos de
        # dentro de uma pasta só entram se forem .md/.txt (RAG_EXTENSOES).
        if caminho.is_file():
            candidatos = [caminho]
        elif caminho.is_dir():
            candidatos = [
                c for c in caminho.rglob("*")
                if c.is_file() and c.suffix.lower() in config.RAG_EXTENSOES
            ]
        else:
            # Falhar alto: uma fonte com nome errado não pode virar uma base
            # vazia em silêncio.
            raise FileNotFoundError(
                f"Fonte do RAG não encontrada: {fonte} (procurada em {raiz})."
            )

        for c in candidatos:
            relativo = c.relative_to(raiz)
            # Ignora ocultos em qualquer nível do caminho (.git, .venv, ...).
            if not any(parte.startswith(".") for parte in relativo.parts):
                # as_posix(): sempre "/" como separador, para o nome (e o hash
                # dos documentos) ser igual em Windows e Linux.
                achados.add(relativo.as_posix())

    # sorted: ordem estável. Sem isso a ordem dos trechos poderia mudar de uma
    # execução para outra.
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


def assinatura_do_modelo() -> str:
    """Hash curto de tudo que muda os vetores guardados (modelo e prefixo de documento).

    Vira o nome da pasta do banco: outro modelo → outra pasta → índice novo.
    O prefixo de CONSULTA não entra porque só afeta a pergunta, não o que foi
    guardado. Os parâmetros de chunking também não: eles mudam o texto dos
    trechos, e a Indexing API já percebe isso pelo hash de cada um.
    """
    dados = json.dumps(
        {"modelo": config.MODELO_EMBEDDING, "prefixo_documento": config.RAG_PREFIXO_DOCUMENTO},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(dados.encode("utf-8")).hexdigest()[:16]


def _documentos(trechos: list[Trecho]) -> list[Document]:
    """Converte os trechos em Documents do LangChain, o formato da Indexing API.

    ``page_content`` é o que o modelo de embeddings recebe (título + texto).
    Os metadados vão para o Chroma junto com o vetor e permitem, na busca,
    achar o Trecho de origem (ver Indice.posicao).
    """
    return [
        Document(
            page_content=trecho.para_indexar,
            metadata={"fonte": fonte, "posicao": posicao, "secao": trecho.secao},
        )
        for trecho, (fonte, posicao) in zip(trechos, _chaves(trechos))
    ]


def _sincronizar_banco(
    nome: str, trechos: list[Trecho], embeddings: Embeddings, pasta_base: Path
) -> tuple[BancoVetorial, dict[str, int]]:
    """Deixa o Chroma da base igual aos trechos atuais, gerando só os embeddings que faltam.

    Raises:
        ErroLLM: Se o Ollama falhar ao gerar algum embedding.
    """
    assinatura = assinatura_do_modelo()
    pasta = pasta_base / assinatura

    # Pastas de outro modelo/prefixo são de vetores que não servem mais.
    # (ignore_errors: no Windows um arquivo aberto não pode ser apagado; a
    # pasta só fica sobrando, sem atrapalhar.)
    if pasta_base.is_dir():
        for outra in pasta_base.iterdir():
            if outra.is_dir() and outra.name != assinatura:
                shutil.rmtree(outra, ignore_errors=True)

    banco = BancoVetorial(pasta / "chroma", embeddings)

    # O RecordManager anota o hash e a data de cada documento indexado. O
    # namespace separa registros de bancos diferentes que dividam o arquivo.
    # URL.create monta o endereço do SQLite com segurança mesmo com espaços e
    # acentos no caminho (o projeto fica em ".../2° Challenge/...").
    registro = SQLRecordManager(
        namespace=f"chroma/{nome}",
        db_url=URL.create("sqlite", database=str(pasta / "registro.sqlite")),
    )
    registro.create_schema()   # cria a tabela se ainda não existir

    resultado = index(
        _documentos(trechos),
        registro,
        banco.vector_store,
        # "full": tudo o que estava no banco e não veio nesta lista é apagado.
        # Funciona porque sempre entregamos a base INTEIRA.
        cleanup="full",
        # Quantos documentos por vez vão ao banco (e portanto ao Ollama).
        batch_size=max(1, config.RAG_LOTE_EMBEDDING),
        # Algoritmo do hash que identifica cada documento. O padrão (SHA-1)
        # funciona, mas emite um aviso de segurança a cada execução.
        key_encoder="sha256",
    )
    # IndexingResult é um dict: num_added, num_updated, num_skipped, num_deleted.
    return banco, dict(resultado)


def construir_indice(
    nome: str,
    usar_embeddings: bool | None = None,
    fontes: tuple[str, ...] | list[str] | None = None,
    raiz: Path | None = None,
    pasta: Path | None = None,
    embeddings: Embeddings | None = None,
) -> Indice:
    """Divide a base em trechos e sincroniza o banco vetorial dela.

    Args:
        nome: Nome da base (chave de config.RAG_BASES, ex.: "supervisor"). Dá
            nome à pasta do banco vetorial.
        usar_embeddings: None (padrão) tenta sincronizar o banco vetorial e, se
            o Ollama ou o modelo não estiverem disponíveis, segue só com
            palavras-chave. True exige os embeddings (levanta ErroLLM se
            falharem). False nunca chama o Ollama nem abre o banco.
        fontes: Arquivos/pastas a indexar (padrão: config.RAG_BASES[nome]).
        raiz: Pasta base das fontes (padrão: raiz do projeto).
        pasta: Onde guardar o banco (padrão: config.PASTA_INDICES_RAG / nome).
        embeddings: Modelo de embeddings (padrão: llm_client.criar_embeddings()).

    Raises:
        ValueError: Se a base não existir em config.RAG_BASES (e as fontes não
            forem informadas), se algum arquivo não estiver em UTF-8 ou se os
            parâmetros de chunking forem inválidos.
        FileNotFoundError: Se alguma fonte não existir.
        ErroLLM: Só com usar_embeddings=True e Ollama indisponível.
    """
    # fontes/raiz/pasta/embeddings existem principalmente para testes (pasta
    # temporária, embeddings falsos). No uso normal só se passa `nome`.
    if fontes is None:
        if nome not in config.RAG_BASES:
            raise ValueError(
                f"Base de conhecimento desconhecida: {nome!r}. "
                f"Bases configuradas: {', '.join(config.RAG_BASES)}."
            )
        fontes = config.RAG_BASES[nome]
    if pasta is None:
        pasta = config.PASTA_INDICES_RAG / nome

    # 1. Chunking: sempre, de todos os arquivos (é rápido). Um arquivo vira
    #    vários Trechos, todos numa lista única, na ordem de ler_fontes.
    trechos = [
        trecho
        for arquivo, conteudo in ler_fontes(fontes, raiz).items()
        for trecho in dividir_texto(conteudo, arquivo)
    ]

    # 2. Sem embeddings pedidos, ou sem nada para indexar: só palavras-chave.
    if usar_embeddings is False or not trechos:
        return Indice(trechos)

    # 3. Embeddings + armazenamento, pela Indexing API.
    try:
        if embeddings is None:
            embeddings = criar_embeddings()
        banco, estatisticas = _sincronizar_banco(nome, trechos, embeddings, pasta)
    except ErroLLM:
        if usar_embeddings:
            raise
        # Modo None: o Ollama falhou e isso NÃO derruba o sistema; o RAG segue
        # só com BM25. Se a falha foi no meio, os lotes já gravados ficam
        # registrados, e a próxima execução continua de onde parou.
        return Indice(trechos)
    return Indice(trechos, banco, estatisticas)
