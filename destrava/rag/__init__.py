"""RAG do Destrava: busca na base de conhecimento de cada agente.

    from destrava.rag import obter_rag

    rag = obter_rag("supervisor")   # ou "planejador"
    contexto = rag.contexto("marca dentista amanhã às 15h")

Ver docs/rag.md.
"""

from destrava.rag.rag import Rag, RespostaRag, obter_rag
from destrava.rag.recuperador import TrechoEncontrado

__all__ = ["Rag", "RespostaRag", "TrechoEncontrado", "obter_rag"]
