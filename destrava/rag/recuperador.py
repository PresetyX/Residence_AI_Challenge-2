"""
Fase de inferência do RAG, até a recuperação de contexto:

    pergunta → embedding da pergunta → busca por similaridade → N trechos mais próximos

Como a busca funciona:
    1. Embeddings (significado): o banco vetorial (Chroma) gera o vetor da
       pergunta com o mesmo modelo da indexação e devolve os trechos de maior
       cosseno ("marcar dentista" acha "criar evento" mesmo sem palavras em
       comum).
    2. BM25 (palavras-chave), com a biblioteca ``rank-bm25``: sempre
       disponível, não precisa do Ollama. Também acha o que o significado
       deixa passar (nomes próprios, siglas, números).
    3. Com as duas, as listas são combinadas por Reciprocal Rank Fusion (RRF),
       que soma 1 / (60 + posição) de cada lista e dispensa comparar notas de
       escalas diferentes.

Se o Ollama cair no meio do uso, a busca daquele pedido segue só com BM25.

Roteiro para ler o arquivo:
    Recuperador.__init__          → monta o BM25 e liga o banco vetorial
    _ordem_lexica                 → a busca por palavras-chave
    _ordem_por_significado        → a busca por embeddings
    Recuperador.buscar            → valida, roda as duas buscas e combina com RRF
"""

from typing import Literal

from rank_bm25 import BM25Plus

from destrava.core import config
from destrava.core.llm_client import ErroLLM
from destrava.rag.chunker import Trecho
from destrava.rag.indice import Indice
from destrava.rag.texto import tokenizar

# Constante do RRF: 60 é o valor do artigo original (Cormack et al., 2009).
# Suaviza a diferença entre posições: o 1º lugar vale 1/61, o 2º 1/62...
RRF_K = 60


class TrechoEncontrado(Trecho):
    """Um trecho devolvido pela busca, com a nota e o método que o achou.

    A nota só serve para ordenar resultados do mesmo método: "lexico" é a nota
    BM25, "hibrido" é a soma RRF.
    """

    # Herda fonte/secao/texto de Trecho e acrescenta a nota. Atenção: o score
    # NÃO é comparável entre métodos (BM25 vai de 0 a dezenas; RRF fica em
    # torno de 0.03). Use-o para ordenar, não como "porcentagem de confiança".
    score: float
    metodo: Literal["lexico", "hibrido"]


class Recuperador:
    """Busca os trechos mais relevantes de um índice para uma pergunta."""

    def __init__(self, indice: Indice, usar_embeddings: bool | None = None):
        """
        Args:
            indice: Índice já construído (ver indice.construir_indice).
            usar_embeddings: None (padrão) usa embeddings se o índice tiver
                banco vetorial e o Ollama responder; True exige (levanta
                ErroLLM se não responder); False usa só palavras-chave e
                nunca chama o Ollama.
        """
        self._indice = indice
        self._usar_embeddings = usar_embeddings
        self._trechos = indice.trechos

        # O BM25 é montado AQUI, a cada criação do Recuperador, a partir dos
        # trechos (não fica no Chroma). Tokeniza o mesmo texto que foi para o
        # embedding (seção + conteúdo), SEM o prefixo "search_document: ", que
        # só faz sentido para o modelo de embeddings.
        corpus = [tokenizar(t.para_indexar) for t in self._trechos]
        # O vocabulário de cada trecho decide quem entra na busca lexical: só
        # trechos com pelo menos uma palavra da pergunta (ver _ordem_lexica).
        self._vocabulario = [set(tokens) for tokens in corpus]
        # Por que BM25Plus e não o BM25Okapi (o mais citado): o Okapi calcula
        # um idf que fica NEGATIVO ou zero quando a palavra aparece em metade
        # ou mais dos trechos. Numa base pequena (2 ou 3 trechos, como nos
        # testes ou numa base nova) isso deixa notas negativas e uma ordem sem
        # sentido. O BM25Plus usa idf = log((N + 1) / n), sempre positivo.
        # O rank-bm25 divide pelo tamanho médio dos trechos: com todos vazios
        # (média 0) daria divisão por zero, então nesse caso não há BM25.
        self._bm25 = BM25Plus(corpus) if any(corpus) else None

        # Só usa embeddings se o índice tiver banco vetorial e o modo permitir.
        # indice.banco é None quando o Ollama estava fora na indexação.
        self._banco = indice.banco if usar_embeddings is not False else None

    @property
    def usa_embeddings(self) -> bool:
        """True se a busca combina BM25 com embeddings."""
        return self._banco is not None

    @property
    def total_trechos(self) -> int:
        return len(self._trechos)

    def _ordem_lexica(self, pergunta: str) -> tuple[list[int], dict[int, float]]:
        """Posições dos trechos por BM25, do melhor para o pior, e a nota de cada um.

        Só entram trechos com pelo menos uma palavra (radical) em comum com a
        pergunta.
        """
        consulta = tokenizar(pergunta)
        if self._bm25 is None or not consulta:
            return [], {}

        # get_scores devolve um array do numpy: uma nota por trecho, na ordem
        # de self._trechos.
        notas = self._bm25.get_scores(consulta)
        termos = set(consulta)
        # O BM25Plus dá uma pequena nota-base (o "delta") por palavra da
        # pergunta, mesmo a trechos que não a contêm. Ela é igual para todos
        # os trechos, então não muda a ordem, mas faz toda nota ser > 0. Por
        # isso o filtro de relevância é feito à parte, pelo vocabulário.
        candidatos = [i for i, vocab in enumerate(self._vocabulario) if vocab & termos]
        # sorted(reverse=True) é estável: no empate, vence o trecho que vem
        # primeiro no índice.
        ordem = sorted(candidatos, key=lambda i: notas[i], reverse=True)
        # float(): o numpy devolve numpy.float64, e o pydantic quer float.
        return ordem, {i: float(notas[i]) for i in ordem}

    def _ordem_por_significado(self, pergunta: str) -> list[int] | None:
        """Posições dos trechos por similaridade de significado, ou None se indisponível."""
        # Contrato do retorno: None = "esta busca não está disponível" (o
        # chamador segue só com BM25); lista vazia = "busquei e nada passou do
        # mínimo". São situações diferentes, e o buscar() as trata diferente.
        if self._banco is None:
            return None

        try:
            # O Chroma gera o vetor da pergunta (prefixo de CONSULTA, ver
            # EmbeddingsOllama.embed_query) e compara. Aqui o Ollama é chamado
            # a cada pergunta. k = todos: o corte em k é feito depois, no RRF.
            pares = self._banco.buscar(
                pergunta, k=self.total_trechos, minimo=config.RAG_SIMILARIDADE_MINIMA
            )
        except ErroLLM:
            # Degradação elegante: modo None cai para BM25; modo True (exige
            # embeddings) propaga o erro.
            if self._usar_embeddings:
                raise
            return None

        # O Chroma devolve Documents; os metadados (fonte, posição no arquivo)
        # dizem qual Trecho é. A nota é descartada: o RRF usa só a POSIÇÃO.
        posicoes = [self._indice.posicao(doc) for doc, _ in pares]
        return [p for p in posicoes if p is not None]

    def buscar(self, pergunta: str, k: int | None = None) -> list[TrechoEncontrado]:
        """Devolve os k trechos mais relevantes para a pergunta, do melhor para o pior.

        Args:
            pergunta: Pedido do usuário em texto livre.
            k: Quantos trechos devolver (padrão: config.RAG_TOP_K).

        Returns:
            Lista de trechos (vazia se a base for vazia ou nada for relevante).

        Raises:
            TypeError: Se a pergunta não for texto.
            ValueError: Se a pergunta estiver vazia ou k não for positivo.
            ErroLLM: Só com usar_embeddings=True e o Ollama indisponível.
        """
        # --- Validação da entrada ---
        if not isinstance(pergunta, str):
            raise TypeError("A pergunta deve ser uma string.")
        if not pergunta.strip():
            raise ValueError("A pergunta não pode estar vazia.")

        k = config.RAG_TOP_K if k is None else k
        # `bool` é subclasse de `int` em Python (True == 1), então precisa ser
        # barrado explicitamente.
        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise ValueError("k deve ser um inteiro positivo.")

        if not self._trechos:
            return []

        # --- As duas buscas ---
        ordem_lexica, notas_lexicas = self._ordem_lexica(pergunta)
        ordem_significado = self._ordem_por_significado(pergunta)

        # Só palavras-chave: a própria nota BM25 ordena.
        # (None = busca por significado indisponível. Uma lista VAZIA não cai
        # aqui: segue para o RRF, que então ordena só com a lista lexical.)
        if ordem_significado is None:
            return [
                TrechoEncontrado(
                    **self._trechos[i].model_dump(), score=notas_lexicas[i], metodo="lexico"
                )
                for i in ordem_lexica[:k]
            ]

        # Palavras-chave + significado: soma as posições das duas listas (RRF).
        # Cada lista dá 1/(60 + posição) a cada trecho. Quem aparece nas DUAS
        # listas soma duas parcelas e sobe; quem aparece em uma só ainda pode
        # entrar. Usa só a posição porque as notas do BM25 e do cosseno estão
        # em escalas incomparáveis.
        notas_rrf: dict[int, float] = {}
        for ordem in (ordem_lexica, ordem_significado):
            for posicao, i in enumerate(ordem, start=1):
                notas_rrf[i] = notas_rrf.get(i, 0.0) + 1 / (RRF_K + posicao)

        # Maior nota primeiro; no empate, a menor posição no índice (resultado
        # determinístico). Só aqui se corta em k.
        melhores = sorted(notas_rrf, key=lambda i: (-notas_rrf[i], i))[:k]
        # model_dump() copia fonte/secao/texto do Trecho original para o
        # TrechoEncontrado, que acrescenta score e método.
        return [
            TrechoEncontrado(
                **self._trechos[i].model_dump(), score=notas_rrf[i], metodo="hibrido"
            )
            for i in melhores
        ]
