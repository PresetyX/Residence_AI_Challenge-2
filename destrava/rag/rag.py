"""
RAG completo de uma base de conhecimento (uma por agente).

Une as duas fases:

    Indexação (feita uma vez, ao criar o Rag):
        base de conhecimento → chunking → embedding dos chunks → armazenamento

    Inferência (a cada pergunta):
        pergunta → embedding → busca por similaridade → recuperação de contexto
        → construção do prompt → geração da resposta

Uso, no Supervisor ou no Planejador:

    from destrava.rag import obter_rag

    rag = obter_rag("supervisor")                  # crie uma vez e reaproveite
    contexto = rag.contexto("marca dentista amanhã")      # só os trechos
    prompt = rag.montar_prompt(pedido, template=MEU_PROMPT)  # trechos no prompt do agente
    resposta = rag.responder("como funciona X?")          # busca + prompt + LLM

O conteúdo das bases (config.RAG_BASES) é mantido por quem cuida delas; este
módulo só indexa e busca.
"""

from functools import lru_cache

from pydantic import BaseModel

from destrava.core import config
from destrava.core.llm_client import perguntar
from destrava.prompts.rag import PROMPT_RAG, RESPOSTA_SEM_CONTEXTO
from destrava.rag.indice import Indice, construir_indice
from destrava.rag.recuperador import Recuperador, TrechoEncontrado


class RespostaRag(BaseModel):
    """Resposta gerada a partir da base, com os trechos usados como fonte."""

    resposta: str
    trechos: list[TrechoEncontrado]
    usou_llm: bool   # False quando nada foi encontrado e a resposta é o texto fixo


class Rag:
    """RAG de uma base de conhecimento."""

    def __init__(
        self,
        nome: str = "supervisor",
        usar_embeddings: bool | None = None,
        indice: Indice | None = None,
    ):
        """
        Args:
            nome: Base a usar (chave de config.RAG_BASES: "supervisor" ou
                "planejador").
            usar_embeddings: None (padrão) usa embeddings se o Ollama estiver
                disponível; True exige (levanta ErroLLM se não estiver); False
                usa só palavras-chave e nunca chama o Ollama.
            indice: Índice já pronto (para testes). Se omitido, é construído a
                partir da base, com cópia em disco.

        Raises:
            ValueError: Se a base não existir em config.RAG_BASES.
            FileNotFoundError: Se uma fonte da base não existir.
        """
        if indice is None:
            indice = construir_indice(nome, usar_embeddings)
        elif nome not in config.RAG_BASES:
            raise ValueError(
                f"Base de conhecimento desconhecida: {nome!r}. "
                f"Bases configuradas: {', '.join(config.RAG_BASES)}."
            )

        self.nome = nome
        self._recuperador = Recuperador(indice, usar_embeddings)

    @property
    def usa_embeddings(self) -> bool:
        """True se a busca combina palavras-chave com embeddings."""
        return self._recuperador.usa_embeddings

    @property
    def total_trechos(self) -> int:
        return self._recuperador.total_trechos

    @property
    def vazia(self) -> bool:
        """True se a base ainda não tem nenhum trecho."""
        return self.total_trechos == 0

    def buscar(self, pergunta: str, k: int | None = None) -> list[TrechoEncontrado]:
        """Os k trechos mais relevantes para a pergunta (ver Recuperador.buscar)."""
        return self._recuperador.buscar(pergunta, k)

    def contexto(self, pergunta: str, k: int | None = None) -> str:
        """Texto de contexto para colocar num prompt.

        Cada trecho vem numerado e com a origem. Devolve "" se nada for
        relevante (ou se a base estiver vazia).
        """
        return self._formatar(self.buscar(pergunta, k))

    @staticmethod
    def _formatar(trechos: list[TrechoEncontrado]) -> str:
        return "\n\n".join(
            f"[{n}] Fonte: {t.fonte} | {t.secao}\n{t.texto}"
            for n, t in enumerate(trechos, start=1)
        )

    def montar_prompt(
        self,
        pergunta: str,
        template: str = PROMPT_RAG,
        k: int | None = None,
        **campos: str,
    ) -> str:
        """Constrói o prompt: o template com o contexto recuperado e a pergunta.

        Args:
            pergunta: Pergunta do usuário (também é o que se busca na base).
            template: Prompt com as lacunas {contexto} e {pergunta_do_usuario}
                (padrão: PROMPT_RAG). Pode ter outras lacunas, passadas em
                ``campos``. Chaves literais devem ser escritas {{ e }}.
            k: Quantos trechos usar (padrão: config.RAG_TOP_K).
            **campos: Valores das outras lacunas do template (ex.: entrada=...).

        Returns:
            O prompt pronto. Sem trechos relevantes, {contexto} vira um aviso
            de que não há contexto.
        """
        contexto = self.contexto(pergunta, k) or "(nenhum trecho relevante encontrado)"
        return template.format(
            contexto=contexto, pergunta_do_usuario=pergunta, **campos
        )

    def responder(self, pergunta: str, k: int | None = None) -> RespostaRag:
        """Busca o contexto, monta o prompt e gera a resposta com o LLM.

        Se nada relevante for encontrado, devolve o texto fixo
        RESPOSTA_SEM_CONTEXTO sem chamar o modelo (que inventaria a resposta).

        Raises:
            ErroLLM: Se o Ollama falhar ao gerar a resposta.
            (mais os erros de ``buscar``)
        """
        trechos = self.buscar(pergunta, k)
        if not trechos:
            return RespostaRag(resposta=RESPOSTA_SEM_CONTEXTO, trechos=[], usou_llm=False)

        prompt = PROMPT_RAG.format(
            contexto=self._formatar(trechos), pergunta_do_usuario=pergunta
        )
        return RespostaRag(resposta=perguntar(prompt), trechos=trechos, usou_llm=True)


@lru_cache(maxsize=None)
def obter_rag(nome: str) -> Rag:
    """O Rag de uma base, criado na primeira chamada e reaproveitado depois.

    Montar o índice pode chamar o Ollama; por isso o Supervisor e o Planejador
    devem usar esta função em vez de criar um Rag a cada pedido.
    """
    return Rag(nome)
