"""
Chunking: divisão dos textos da base de conhecimento em trechos (chunks).

Usa dois splitters do pacote ``langchain-text-splitters``, em sequência:

    1. Por seção: ``ExperimentalMarkdownSyntaxTextSplitter``.
       Cada título Markdown (# ... ######) abre uma seção, e o caminho de
       títulos ("Agente Criar > Fluxo") acompanha o trecho, porque é ele que
       diz do que o texto fala. Texto sem títulos (.txt) vira uma seção só,
       com o nome do arquivo.

    2. Por tamanho: ``RecursiveCharacterTextSplitter``.
       Uma seção maior que ``tamanho_max`` é cortada tentando, em ordem, as
       fronteiras mais naturais: parágrafo, linha, frase, palavra e, em último
       caso, caractere. Partes vizinhas repetem até ``sobreposicao``
       caracteres (o fim de uma reaparece no começo da seguinte), para uma
       ideia que cai na divisa não se perder entre dois trechos.

Por que o splitter "Experimental" e não o ``MarkdownHeaderTextSplitter``: o
segundo tira a indentação das linhas (listas aninhadas e exemplos de código
perdem a estrutura) e troca as linhas em branco por "  \\n", e sem linhas em
branco o passo 2 não consegue cortar por parágrafo. O experimental preserva o
texto como está e não trata "#" dentro de blocos de código como título.

Nenhum trecho passa de ``tamanho_max`` caracteres (o caminho de títulos não
conta).
"""

from pydantic import BaseModel
from langchain_text_splitters import (
    ExperimentalMarkdownSyntaxTextSplitter,
    RecursiveCharacterTextSplitter,
)

from destrava.core import config

# Fronteiras tentadas pelo RecursiveCharacterTextSplitter, da melhor para a
# pior. Ele usa a primeira que existir no texto; a parte que ainda ficar
# grande demais é cortada de novo com as seguintes. "" (caractere) garante que
# até uma "palavra" gigante (URL, base64) caiba no limite.
SEPARADORES = ["\n\n", "\n", ". ", "! ", "? ", "; ", ": ", " ", ""]


class Trecho(BaseModel):
    """Um pedaço de uma fonte, pronto para ser indexado e devolvido na busca."""

    fonte: str          # arquivo de origem, relativo à raiz do projeto
    secao: str          # caminho de títulos, ex.: "Agente Criar > Fluxo"
    texto: str          # conteúdo do trecho (sem o caminho de títulos)

    @property
    def para_indexar(self) -> str:
        """Texto usado na busca: o caminho de títulos mais o conteúdo."""
        # Atenção: é ISTO que vira embedding e que o BM25 lê, não só `texto`.
        # O título dá o contexto que um parágrafo solto ("Ele pergunta a
        # data") não tem.
        return f"{self.secao}\n{self.texto}"


def _secoes(conteudo: str) -> list[tuple[list[str], str]]:
    """Divide o texto por título Markdown.

    Returns:
        Pares (caminho de títulos, texto da seção), na ordem do arquivo. O
        caminho é vazio para o texto antes do primeiro título (ou para um
        arquivo sem títulos). Seções sem texto não aparecem.
    """
    # strip_headers=True: a linha do título sai do texto (ela já vai no
    # caminho de títulos, não precisa aparecer duas vezes).
    documentos = ExperimentalMarkdownSyntaxTextSplitter(strip_headers=True).split_text(conteudo)

    secoes: list[tuple[list[str], str]] = []
    for doc in documentos:
        # O splitter guarda os títulos ativos nos metadados, com as chaves
        # "Header 1" ... "Header 6" (só as dos níveis presentes). Montamos o
        # caminho do nível 1 ao 6.
        caminho = [
            doc.metadata[f"Header {nivel}"].strip().rstrip("#").strip()
            for nivel in range(1, 7)
            if f"Header {nivel}" in doc.metadata
        ]
        # O splitter separa cada bloco de código (```) num documento próprio,
        # com a chave "Code" nos metadados. Para o RAG, o código faz parte da
        # seção: documentos vizinhos com o mesmo caminho são juntados de novo.
        # Como o splitter preserva as quebras de linha, basta concatenar.
        if secoes and secoes[-1][0] == caminho:
            secoes[-1] = (caminho, secoes[-1][1] + doc.page_content)
        else:
            secoes.append((caminho, doc.page_content))

    # Limitação herdada do splitter: um bloco de código aberto (```) e nunca
    # fechado é descartado inteiro, junto com o resto do arquivo depois dele.
    return [(caminho, texto.strip()) for caminho, texto in secoes if texto.strip()]


def dividir_texto(
    conteudo: str,
    fonte: str,
    tamanho_max: int | None = None,
    sobreposicao: int | None = None,
) -> list[Trecho]:
    """Divide um texto (Markdown ou texto puro) em trechos.

    Args:
        conteudo: Texto do arquivo.
        fonte: Nome do arquivo (guardado no trecho, para citar a origem).
        tamanho_max: Limite de caracteres por trecho (padrão:
            config.RAG_TAMANHO_MAX_TRECHO).
        sobreposicao: Caracteres repetidos entre partes vizinhas de uma seção
            dividida (padrão: config.RAG_SOBREPOSICAO). Deve ser menor que
            tamanho_max.

    Returns:
        Lista de trechos, na ordem do arquivo. Seções sem texto são ignoradas.

    Raises:
        ValueError: Se tamanho_max não for positivo ou a sobreposição não for
            menor que ele.
    """
    # Os padrões são lidos aqui (e não na assinatura) para respeitar mudanças
    # feitas no config depois que o módulo foi importado.
    if tamanho_max is None:
        tamanho_max = config.RAG_TAMANHO_MAX_TRECHO
    if sobreposicao is None:
        sobreposicao = config.RAG_SOBREPOSICAO
    # O LangChain também valida, mas com mensagem em inglês e sem dizer de
    # onde vêm os valores. Validamos antes, com os nomes do config.
    if tamanho_max <= 0:
        raise ValueError("tamanho_max (RAG_TAMANHO_MAX_TRECHO) deve ser positivo.")
    if not 0 <= sobreposicao < tamanho_max:
        raise ValueError(
            "sobreposicao (RAG_SOBREPOSICAO) deve ser >= 0 e menor que tamanho_max."
        )

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=tamanho_max,
        chunk_overlap=sobreposicao,
        separators=SEPARADORES,
        # Onde fica o separador depois do corte: "end" deixa o ". " no fim da
        # frase anterior. O padrão (True = "start") começaria cada trecho com
        # ". Próxima frase".
        keep_separator="end",
        # Tira espaços e quebras de linha das pontas de cada trecho.
        strip_whitespace=True,
    )

    trechos: list[Trecho] = []
    for caminho, texto in _secoes(conteudo):
        # Sem nenhum título (.txt ou texto antes do 1º título), o nome do
        # arquivo faz o papel de seção.
        secao = " > ".join(caminho) or fonte
        # Seção que já cabe no limite sai inteira (uma parte só); a sobreposição
        # só existe entre partes de uma mesma seção, nunca entre seções.
        for parte in divisor.split_text(texto):
            trechos.append(Trecho(fonte=fonte, secao=secao, texto=parte))
    return trechos
