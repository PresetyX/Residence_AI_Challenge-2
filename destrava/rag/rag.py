"""
RAG completo de uma base de conhecimento (uma por agente).

Une as duas fases:

    Indexação (feita ao criar o Rag):
        base de conhecimento → chunking → embedding dos chunks → armazenamento

    Inferência (a cada pergunta):
        pergunta → embedding → busca por similaridade → recuperação de contexto
        → construção do prompt → geração da resposta

As duas últimas etapas usam o LangChain:
    - ``ChatPromptTemplate``: o prompt com as lacunas {contexto} e
      {pergunta_do_usuario}, preenchidas na hora.
    - LCEL (LangChain Expression Language): o operador ``|`` encadeia
      "Runnables", e a saída de um vira a entrada do próximo:

          ChatPromptTemplate | ChatOllama | StrOutputParser
          (monta o prompt)    (gera)       (AIMessage → str)

Uso, no Supervisor ou no Planejador:

    from destrava.rag import obter_rag

    rag = obter_rag("supervisor")                  # crie uma vez e reaproveite
    contexto = rag.contexto("marca dentista amanhã")      # só os trechos
    prompt = rag.montar_prompt(pedido, template=MEU_PROMPT)  # trechos no prompt do agente
    resposta = rag.responder("como funciona X?")          # busca + prompt + LLM

O conteúdo das bases (config.RAG_BASES) é mantido por quem cuida delas; este
módulo só indexa e busca.

Três níveis de uso, do mais simples ao mais completo:
    contexto()      → só o texto dos trechos (você monta o prompt)
    montar_prompt() → o prompt pronto, com o contexto dentro (você chama o LLM)
    responder()     → busca + prompt + LLM, devolve a resposta final
"""

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from destrava.core import config
from destrava.core.llm_client import ErroLLM, criar_chat, traduzir_erros
from destrava.prompts.rag import PROMPT_RAG, RESPOSTA_SEM_CONTEXTO
from destrava.rag.indice import Indice, construir_indice
from destrava.rag.recuperador import Recuperador, TrechoEncontrado


class RespostaRag(BaseModel):
    """Resposta gerada a partir da base, com os trechos usados como fonte."""

    resposta: str
    # Devolver os trechos junto com a resposta permite mostrar/citar as fontes
    # e depurar ("por que ele respondeu isso?").
    trechos: list[TrechoEncontrado]
    usou_llm: bool   # False quando nada foi encontrado e a resposta é o texto fixo


def criar_template(texto: str) -> ChatPromptTemplate:
    """Transforma o texto de um prompt num ChatPromptTemplate do LangChain.

    O prompt inteiro vira UMA mensagem do usuário ("human"). Não há mensagem
    "system" porque o Gemma 2 não tem esse papel: as instruções ficam dentro do
    próprio prompt (ver prompts/rag.py).

    As lacunas seguem o formato do ``str.format``: {nome} é preenchido na hora,
    e chaves literais (um JSON de exemplo no prompt) devem ser escritas {{ e }}.
    """
    return ChatPromptTemplate.from_messages([("human", texto)])


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
                partir da base, sincronizando o banco vetorial em disco.

        Raises:
            ValueError: Se a base não existir em config.RAG_BASES.
            FileNotFoundError: Se uma fonte da base não existir.
        """
        # Este é o momento da FASE DE INDEXAÇÃO: construir_indice faz o
        # chunking e sincroniza o Chroma pela Indexing API (pode chamar o
        # Ollama para os trechos novos). Por isso criar um Rag pode ser lento.
        if indice is None:
            indice = construir_indice(nome, usar_embeddings)
        # Com um índice injetado (testes), construir_indice não roda e não
        # valida o nome; essa checagem cobre o caso.
        elif nome not in config.RAG_BASES:
            raise ValueError(
                f"Base de conhecimento desconhecida: {nome!r}. "
                f"Bases configuradas: {', '.join(config.RAG_BASES)}."
            )

        self.nome = nome
        # Público para inspeção (ex.: indice.estatisticas no script de teste).
        self.indice = indice
        # O Recuperador monta o BM25 e liga o banco vetorial (ver recuperador.py).
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
        # Só repassa. É aqui que começa a FASE DE INFERÊNCIA.
        return self._recuperador.buscar(pergunta, k)

    def contexto(self, pergunta: str, k: int | None = None) -> str:
        """Texto de contexto para colocar num prompt.

        Cada trecho vem numerado e com a origem. Devolve "" se nada for
        relevante (ou se a base estiver vazia).
        """
        return self._formatar(self.buscar(pergunta, k))

    @staticmethod
    def _formatar(trechos: list[TrechoEncontrado]) -> str:
        # Cada trecho vira um bloco: "[1] Fonte: arquivo.md | Seção > Subseção"
        # e, na linha de baixo, o texto. Blocos separados por linha em branco.
        # A numeração e a fonte permitem ao modelo (e a você) rastrear de onde
        # veio cada informação. Sem trechos, o resultado é "" (string vazia).
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
        # Este é o método para os agentes (Supervisor, Planejador) que têm o
        # PRÓPRIO prompt e só querem o contexto encaixado nele.
        # Diferença para responder(): aqui, sem trechos, o prompt AINDA é
        # montado, com um aviso no lugar do contexto. A decisão do que fazer
        # fica com o agente. (responder() simplesmente não chama o modelo.)
        contexto = self.contexto(pergunta, k) or "(nenhum trecho relevante encontrado)"
        # format_messages preenche as lacunas e devolve a lista de mensagens
        # (aqui, uma só: a "human"). O agente quer o texto, então pegamos o
        # .content dela. Só as chaves do TEMPLATE são interpretadas: chaves
        # dentro do contexto ou da pergunta (ex.: um JSON) não dão problema.
        mensagens = criar_template(template).format_messages(
            contexto=contexto, pergunta_do_usuario=pergunta, **campos
        )
        return mensagens[0].content

    def cadeia_de_resposta(self) -> Runnable:
        """A cadeia LCEL que gera a resposta a partir do contexto e da pergunta.

        Entrada: {"contexto": str, "pergunta_do_usuario": str}. Saída: str.

        Cada ``|`` liga a saída de um passo à entrada do próximo:
            1. ChatPromptTemplate preenche o PROMPT_RAG → ChatPromptValue
            2. ChatOllama (config.MODELO) gera → AIMessage
            3. StrOutputParser tira o texto da mensagem → str

        A cadeia não contata o Ollama ao ser criada, só no ``invoke``.
        """
        return criar_template(PROMPT_RAG) | criar_chat() | StrOutputParser()

    def responder(self, pergunta: str, k: int | None = None) -> RespostaRag:
        """Busca o contexto, monta o prompt e gera a resposta com o LLM.

        Se nada relevante for encontrado, devolve o texto fixo
        RESPOSTA_SEM_CONTEXTO sem chamar o modelo (que inventaria a resposta).

        Raises:
            ErroLLM: Se o Ollama falhar ao gerar a resposta.
            (mais os erros de ``buscar``)
        """
        trechos = self.buscar(pergunta, k)
        # Curto-circuito: sem contexto, o LLM não é chamado. Perguntar a um
        # modelo sem contexto o faria responder "de cabeça" e inventar,
        # exatamente o que o RAG existe para evitar. Também economiza uma chamada.
        if not trechos:
            return RespostaRag(resposta=RESPOSTA_SEM_CONTEXTO, trechos=[], usou_llm=False)

        # A busca fica FORA da cadeia LCEL porque precisamos dos trechos para
        # devolvê-los na RespostaRag e para o curto-circuito acima.
        # traduzir_erros: qualquer falha do Ollama vira ErroLLM.
        with traduzir_erros(config.MODELO):
            texto = self.cadeia_de_resposta().invoke(
                {"contexto": self._formatar(trechos), "pergunta_do_usuario": pergunta}
            )
        if not texto.strip():
            raise ErroLLM("O modelo retornou uma resposta vazia.")
        return RespostaRag(resposta=texto.strip(), trechos=trechos, usou_llm=True)


# lru_cache funciona como um "singleton por nome": a primeira chamada com
# "supervisor" cria o Rag; as próximas, no mesmo processo, devolvem o MESMO
# objeto, sem reindexar. Atenção às consequências:
#   - Editar os arquivos da base com o programa rodando NÃO tem efeito até
#     reiniciar (o índice só é sincronizado ao criar o Rag).
#   - Se o Ollama estava fora quando o Rag foi criado, ele fica só com
#     palavras-chave até reiniciar (o banco vetorial não é ligado depois).
#   - Se a criação falhar com exceção, nada é guardado no cache; a próxima
#     chamada tenta de novo.
@lru_cache(maxsize=None)
def obter_rag(nome: str) -> Rag:
    """O Rag de uma base, criado na primeira chamada e reaproveitado depois.

    Montar o índice pode chamar o Ollama; por isso o Supervisor e o Planejador
    devem usar esta função em vez de criar um Rag a cada pedido.
    """
    return Rag(nome)
