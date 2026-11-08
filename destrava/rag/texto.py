"""
Normalização de texto para a busca por palavras-chave (BM25) do RAG.

Usa o NLTK para as duas partes que dependem do idioma:
    - ``stopwords.words("portuguese")``: palavras sem valor de busca (artigos,
      preposições, pronomes...), mais uma lista curta própria do projeto.
    - ``RSLPStemmer``: o stemmer RSLP, feito para o português, que reduz cada
      palavra ao seu radical ("agendar", "agenda", "agendamento" → "agend";
      "criar", "criação" → "cri").

Quem usa este módulo: só o BM25 (recuperador.py). A busca por significado
(embeddings) NÃO passa por aqui: o modelo recebe o texto original.

A MESMA função (``tokenizar``) precisa ser aplicada aos trechos e à pergunta.
Se um lado fosse normalizado de um jeito e o outro de outro, as palavras nunca
se encontrariam.

Dados do NLTK: a lista de stopwords e as regras do RSLP não vêm no pacote,
são baixadas uma vez (para ~/nltk_data). ``tokenizar`` baixa sozinho na
primeira chamada; sem internet, levanta um erro dizendo o comando para baixar
manualmente:

    python -m nltk.downloader stopwords rslp
"""

import re
import unicodedata
from functools import lru_cache

import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer

# Recursos do NLTK usados aqui: (nome para o download, caminho para o find).
RECURSOS_NLTK = (("stopwords", "corpora/stopwords"), ("rslp", "stemmers/rslp"))

# Palavras que a lista do NLTK não traz, mas que aparecem em quase todo pedido
# ao assistente e não ajudam a decidir o que é relevante ("QUERO marcar
# dentista", "PRECISO ver a agenda").
STOPWORDS_EXTRAS = """
    quero queria quer gostaria preciso precisa pode podem poderia favor pra
    vc voce ai la ja so
""".split()


def sem_acentos(texto: str) -> str:
    """Remove os acentos ("agenda é" -> "agenda e")."""
    # NFKD separa a letra do acento: "é" vira "e" + "´" (dois caracteres).
    # Depois descartamos os caracteres "combinantes" (os acentos soltos).
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _garantir_recursos_nltk() -> None:
    """Baixa os dados do NLTK que faltarem (só na primeira vez).

    Raises:
        RuntimeError: Se não for possível baixar (sem internet, por exemplo).
    """
    for nome, caminho in RECURSOS_NLTK:
        try:
            nltk.data.find(caminho)       # já existe em algum nltk_data?
        except LookupError:
            # quiet=True: sem barra de progresso. Devolve False se falhar.
            if not nltk.download(nome, quiet=True):
                raise RuntimeError(
                    f"Não foi possível baixar o recurso '{nome}' do NLTK. Com "
                    "internet, rode: python -m nltk.downloader stopwords rslp"
                ) from None


# lru_cache: carrega stemmer e stopwords UMA vez por processo, e só quando
# alguém tokeniza pela primeira vez (importar o módulo não baixa nada).
@lru_cache(maxsize=1)
def _stemmer() -> RSLPStemmer:
    _garantir_recursos_nltk()
    return RSLPStemmer()


@lru_cache(maxsize=1)
def _stopwords() -> frozenset[str]:
    """Stopwords do NLTK + as do projeto, sem acento (para comparar com qualquer grafia)."""
    _garantir_recursos_nltk()
    return frozenset(sem_acentos(p) for p in stopwords.words("portuguese") + STOPWORDS_EXTRAS)


def _radicais(palavra: str) -> set[str]:
    """Radical(is) de uma palavra, já sem acento.

    Por que pode haver dois: o RSLP depende dos acentos ("reunião" → "reun",
    mas "reuniao" → "reunia"). Como muita gente digita sem acento, geramos o
    radical da palavra como veio E da versão sem acento. Isso vale para os
    trechos e para a pergunta, então basta um dos radicais coincidir.
    """
    # Números e códigos ("15h", "2026") ficam como estão: o RSLP é para
    # palavras, e datas/horas ajudam a achar os exemplos certos.
    if any(c.isdigit() for c in palavra):
        return {palavra}
    stemmer = _stemmer()
    return {sem_acentos(stemmer.stem(forma)) for forma in {palavra, sem_acentos(palavra)}}


def tokenizar(texto: str) -> list[str]:
    """Quebra o texto em radicais, sem acentos, sem maiúsculas e sem stopwords.

    Exemplo:
        tokenizar("Quero marcar dentista amanhã às 15h")
        → ["marc", "dent", "amanha", "amanh", "15h"]
        ("quero" e "às" são stopwords; "amanhã" gera dois radicais, ver _radicais)

    Raises:
        RuntimeError: Se os dados do NLTK faltarem e não puderem ser baixados.
    """
    # \w+ pega letras (inclusive acentuadas) e dígitos; descarta pontuação.
    # O acento é mantido neste ponto porque o RSLP precisa dele.
    palavras = re.findall(r"\w+", texto.lower())
    tokens: list[str] = []
    for palavra in palavras:
        # Letras soltas e stopwords não entram. A comparação é sem acento,
        # para "voce" e "você" serem tratadas igual.
        if len(palavra) < 2 or sem_acentos(palavra) in _stopwords():
            continue
        # sorted: ordem fixa entre os dois radicais (set não tem ordem).
        tokens.extend(sorted(_radicais(palavra)))
    return tokens
