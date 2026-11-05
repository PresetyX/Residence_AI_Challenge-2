"""
Chunking: divisão dos textos da base de conhecimento em trechos (chunks).

Como o texto é dividido, em ordem:
    1. Por seção. Cada título Markdown (# ... ######) abre uma seção, e o caminho
       de títulos ("Agente Criar > Fluxo") acompanha o trecho, porque é ele que
       diz do que o texto fala. Texto sem títulos (.txt) vira uma seção só.
    2. Por parágrafo. Uma seção maior que o limite é dividida em blocos
       separados por linha em branco; blocos pequenos vizinhos são juntados até
       o limite. Linha em branco dentro de um bloco de código (```) não separa.
    3. Por linha, frase e palavra. Um bloco sozinho maior que o limite (um
       parágrafo enorme, uma tabela comprida) é cortado nessas fronteiras, e
       cada parte repete o fim da anterior (sobreposição), para uma ideia que
       cai na divisa não se perder entre dois trechos.

Nenhum trecho passa de ``tamanho_max`` caracteres (o caminho de títulos não
conta).
"""

import re

from pydantic import BaseModel

from destrava.core import config

_TITULO = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FIM_DE_FRASE = re.compile(r"(?<=[.!?;:])\s+")


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


def _unidades_de_texto_longo(texto: str, tamanho_max: int) -> list[str]:
    """Quebra um texto sem quebra de linha em unidades menores que tamanho_max.

    Prefere o fim de uma frase; uma frase ainda grande demais vira palavras; uma
    palavra maior que o limite (URL, base64) é cortada no meio. As unidades não
    são empacotadas aqui: isso é feito depois, junto com a sobreposição.
    """
    unidades: list[str] = []

    for frase in _FIM_DE_FRASE.split(texto):
        pedacos = [frase] if len(frase) <= tamanho_max else frase.split(" ")
        for pedaco in pedacos:
            while len(pedaco) > tamanho_max:
                unidades.append(pedaco[:tamanho_max])
                pedaco = pedaco[tamanho_max:]
            if pedaco:
                unidades.append(pedaco)
    return unidades


def _montar(unidades: list[tuple[str, str]]) -> str:
    """Junta as unidades (separador, texto) no texto final de um trecho."""
    return "".join((sep if i else "") + texto for i, (sep, texto) in enumerate(unidades))


def _dividir_bloco_grande(bloco: str, tamanho_max: int, sobreposicao: int) -> list[str]:
    """Divide um bloco maior que o limite, repetindo o fim de cada parte na seguinte."""
    # Unidades: as linhas do bloco; uma linha longa vira várias unidades.
    # Cada unidade guarda o separador que a precede ("\n" ou " ").
    unidades: list[tuple[str, str]] = []
    for linha in bloco.splitlines():
        if len(linha) <= tamanho_max:
            unidades.append(("\n", linha))
        else:
            for i, pedaco in enumerate(_unidades_de_texto_longo(linha, tamanho_max)):
                unidades.append(("\n" if i == 0 else " ", pedaco))

    partes: list[list[tuple[str, str]]] = []
    atual: list[tuple[str, str]] = []

    for unidade in unidades:
        if atual and len(_montar(atual + [unidade])) > tamanho_max:
            partes.append(atual)

            # Sobreposição: leva para a próxima parte as últimas unidades da
            # anterior que cabem em `sobreposicao`.
            repetidas: list[tuple[str, str]] = []
            for anterior in reversed(atual):
                if len(_montar([anterior] + repetidas)) > sobreposicao:
                    break
                repetidas.insert(0, anterior)
            # Só repete se sobrar espaço para a unidade nova.
            atual = repetidas if len(_montar(repetidas + [unidade])) <= tamanho_max else []
        atual.append(unidade)

    if atual:
        partes.append(atual)
    return [_montar(parte) for parte in partes]


def _juntar(blocos: list[str], tamanho_max: int, sobreposicao: int) -> list[str]:
    """Junta blocos vizinhos até o limite; divide o bloco que sozinho passa dele."""
    partes: list[str] = []
    atual = ""

    for bloco in blocos:
        if len(bloco) > tamanho_max:
            if atual:
                partes.append(atual)
                atual = ""
            partes.extend(_dividir_bloco_grande(bloco, tamanho_max, sobreposicao))
        elif atual and len(atual) + len(bloco) + 2 > tamanho_max:
            partes.append(atual)
            atual = bloco
        else:
            atual = f"{atual}\n\n{bloco}" if atual else bloco

    if atual:
        partes.append(atual)
    return partes


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
        sobreposicao: Caracteres repetidos entre as partes de uma seção
            dividida (padrão: config.RAG_SOBREPOSICAO). Deve ser menor que
            tamanho_max.

    Returns:
        Lista de trechos, na ordem do arquivo. Seções sem texto são ignoradas.

    Raises:
        ValueError: Se tamanho_max não for positivo ou a sobreposição não for
            menor que ele.
    """
    if tamanho_max is None:
        tamanho_max = config.RAG_TAMANHO_MAX_TRECHO
    if sobreposicao is None:
        sobreposicao = config.RAG_SOBREPOSICAO
    if tamanho_max <= 0:
        raise ValueError("tamanho_max deve ser positivo.")
    if not 0 <= sobreposicao < tamanho_max:
        raise ValueError("sobreposicao deve ser >= 0 e menor que tamanho_max.")

    trechos: list[Trecho] = []
    caminho: list[str] = []   # títulos ativos, do nível 1 ao atual
    corpo: list[str] = []
    em_codigo = False

    def fechar_secao() -> None:
        texto = "\n".join(corpo).strip()
        if not texto:
            return
        secao = " > ".join(caminho) or fonte
        for parte in _juntar(_blocos(texto.splitlines()), tamanho_max, sobreposicao):
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
