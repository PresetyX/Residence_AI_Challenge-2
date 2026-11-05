"""RAG do Supervisor: busca na documentação dos agentes e nos exemplos de roteamento.

    from destrava.rag import RagSupervisor

    rag = RagSupervisor()
    contexto = rag.contexto("marca dentista amanhã às 15h")
"""

from destrava.rag.recuperador import RagSupervisor, TrechoEncontrado

__all__ = ["RagSupervisor", "TrechoEncontrado"]
