"""
Normalização de texto para a busca por palavras-chave do RAG.

Funções simples e sem dependências externas: tiram acento e maiúscula, cortam
o texto em palavras, descartam palavras sem valor de busca (artigos,
preposições) e reduzem cada palavra a um radical curto, para que "agendar",
"agenda" e "agendamento" se encontrem.
"""

import re
import unicodedata

# Palavras muito comuns em português, sem valor para decidir o que é relevante.
STOPWORDS = frozenset(
    """
    a o as os um uma uns umas de do da dos das em no na nos nas por para pra com
    sem sobre ao aos e ou mas que se me te nos eu tu ele ela voce vc meu minha
    seu sua e ser estar ter tem ha foi vai vou quero queria quer gostaria
    preciso pode podem poderia favor por favor ai la ja so mais muito
    """.split()
)

# Tamanho do radical: corta a palavra depois de tirar o plural. É uma
# aproximação (não é um stemmer completo), mas basta para um corpus pequeno.
TAMANHO_RADICAL = 6


def sem_acentos(texto: str) -> str:
    """Remove os acentos ("agenda é" -> "agenda e")."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def radical(palavra: str) -> str:
    """Reduz a palavra a um radical curto (tira o plural e corta o resto)."""
    if len(palavra) > 3 and palavra.endswith("s"):
        palavra = palavra[:-1]
    return palavra[:TAMANHO_RADICAL]


def tokenizar(texto: str) -> list[str]:
    """Quebra o texto em radicais, sem acentos, sem maiúsculas e sem stopwords.

    Números são mantidos ("2026", "15h" vira "15h"), pois datas e horas
    ajudam a achar os exemplos certos.
    """
    palavras = re.findall(r"[a-z0-9]+", sem_acentos(texto).lower())
    return [radical(p) for p in palavras if p not in STOPWORDS and len(p) > 1]
