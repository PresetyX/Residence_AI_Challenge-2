"""
Divisão dos arquivos Markdown em trechos (chunks) para o RAG.

Cada trecho é uma seção do documento (um título e o texto abaixo dele). Seções
grandes são divididas por parágrafo, sem nunca cortar um bloco de código ou
uma tabela no meio. O caminho de títulos ("Agente Criar > Fluxo") acompanha o
trecho, porque é ele que diz do que o texto fala.
"""

import re

from pydantic import BaseModel

from destrava.core import config

_TITULO = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


class Trecho(BaseModel):
    """Um pedaço de uma fonte, pronto para ser indexado e devolvido na busca."""

    fonte: str          # arquivo de origem, relativo à raiz do projeto
    secao: str          # caminho de títulos, ex.: "Agente Criar > Fluxo"
    texto: str          # conteúdo do trecho (sem o caminho de títulos)

    @property
    def para_indexar(self) -> str:
        """Texto usado na busca: o caminho de títulos mais o conteúdo."""
        return f"{self.secao}\n{self.texto}"


def _blocos(linhas: list[str]) -> list[str]:
    """Agrupa as linhas em blocos separados por linha em branco.

    Linha em branco dentro de um bloco de código (```) não separa blocos.
    """
    blocos: list[str] = []
    atual: list[str] = []
    em_codigo = False

    for linha in linhas:
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo
        if not linha.strip() and not em_codigo:
            if atual:
                blocos.append("\n".join(atual))
                atual = []
        else:
            atual.append(linha)

    if atual:
        blocos.append("\n".join(atual))
    return blocos


def _juntar(blocos: list[str], tamanho_max: int) -> list[str]:
    """Junta blocos vizinhos até o limite de tamanho (um bloco grande fica sozinho)."""
    partes: list[str] = []
    atual = ""

    for bloco in blocos:
        if atual and len(atual) + len(bloco) + 2 > tamanho_max:
            partes.append(atual)
            atual = bloco
        else:
            atual = f"{atual}\n\n{bloco}" if atual else bloco

    if atual:
        partes.append(atual)
    return partes


def dividir_markdown(
    conteudo: str, fonte: str, tamanho_max: int | None = None
) -> list[Trecho]:
    """Divide um texto Markdown em trechos.

    Args:
        conteudo: Texto do arquivo.
        fonte: Nome do arquivo (guardado no trecho, para citar a origem).
        tamanho_max: Limite de caracteres por trecho (padrão:
            config.RAG_TAMANHO_MAX_TRECHO).

    Returns:
        Lista de trechos, na ordem do arquivo. Seções sem texto são ignoradas.
    """
    if tamanho_max is None:
        tamanho_max = config.RAG_TAMANHO_MAX_TRECHO

    trechos: list[Trecho] = []
    caminho: list[str] = []   # títulos ativos, do nível 1 ao atual
    corpo: list[str] = []
    em_codigo = False

    def fechar_secao() -> None:
        texto = "\n".join(corpo).strip()
        if not texto:
            return
        secao = " > ".join(caminho) or fonte
        for parte in _juntar(_blocos(texto.splitlines()), tamanho_max):
            trechos.append(Trecho(fonte=fonte, secao=secao, texto=parte))

    for linha in conteudo.splitlines():
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo

        achou = None if em_codigo else _TITULO.match(linha)
        if achou:
            fechar_secao()
            corpo = []
            nivel = len(achou.group(1))
            caminho = caminho[: nivel - 1] + [achou.group(2)]
        else:
            corpo.append(linha)

    fechar_secao()
    return trechos
