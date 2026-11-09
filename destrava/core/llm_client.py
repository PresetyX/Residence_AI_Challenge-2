"""
Cliente compartilhado de LLM do projeto Destrava.

Conversa com o Ollama através do LangChain (pacote ``langchain-ollama``) e
retorna o texto gerado ou os vetores (embeddings).

É o ponto único de entrada dos agentes para o LLM: nenhum outro módulo cria um
``ChatOllama`` ou um ``OllamaEmbeddings`` por conta própria. Assim, modelo,
endereço, tempo limite e tratamento de erros ficam num lugar só.

Interface pública:
    perguntar(prompt: str, formato=None) -> str
        Envia um prompt e devolve a resposta (atalho para quem não usa LCEL).
        ``formato`` (um JSON Schema) obriga a resposta a seguir esse esquema.
    criar_chat(formato=None) -> ChatOllama
        O modelo de chat do LangChain, pronto para entrar numa cadeia LCEL
        (``prompt | criar_chat() | StrOutputParser()``).
    criar_embeddings() -> EmbeddingsOllama
        O modelo de embeddings, no formato ``Embeddings`` do LangChain (usado
        pelo RAG e pelo Chroma).
    traduzir_erros(modelo)
        Bloco ``with`` que converte as exceções do Ollama em ``ErroLLM``.
    extrair_json(texto: str) -> dict
        Lê o JSON que o modelo devolveu.

Por que tudo vira ``ErroLLM``: o LangChain e o cliente do Ollama levantam
exceções de bibliotecas diferentes (``httpx``, ``ollama``, ``ConnectionError``
do Python). Os agentes e o RAG tratam uma só, seja qual for a falha.

Os prompts e as regras de negócio ficam nos agentes, não neste módulo.
"""

import json
import re
from collections.abc import Generator
from contextlib import contextmanager

import httpx
import ollama
from langchain_core.embeddings import Embeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings

from . import config


__all__ = [
    "perguntar",
    "criar_chat",
    "criar_embeddings",
    "EmbeddingsOllama",
    "traduzir_erros",
    "extrair_json",
    "ErroLLM",
]

# Segundos para conseguir abrir a conexão com o Ollama. É separado do
# TIMEOUT_LLM (tempo para a resposta chegar) para que um Ollama desligado
# falhe em segundos, e não só depois de minutos.
TIMEOUT_CONEXAO = 5.0


# Erro próprio do projeto: os agentes tratam só este, seja qual for a falha.
class ErroLLM(RuntimeError):
    """Erro de configuração, comunicação ou resposta do Ollama."""


# ------------------------------------------------------------ configuração


def _ler_config(nome_modelo: str) -> tuple[str, str, httpx.Timeout]:
    """Lê e valida modelo, endereço e tempo limite do config.py.

    Args:
        nome_modelo: Nome da constante do config com o modelo ("MODELO" ou
            "MODELO_EMBEDDING"). O nome entra nas mensagens de erro.

    Returns:
        (modelo, url_do_ollama, timeout_do_httpx)

    Raises:
        ErroLLM: Se algum valor do config for inválido.
    """
    modelo = getattr(config, nome_modelo)
    base_url = config.OLLAMA_URL
    timeout = config.TIMEOUT_LLM

    if not isinstance(modelo, str) or not modelo.strip():
        raise ErroLLM(f"{nome_modelo} deve ser uma string não vazia em config.py.")

    if not isinstance(base_url, str) or not base_url.strip():
        raise ErroLLM("OLLAMA_URL deve ser uma URL não vazia em config.py.")

    # bool é subclasse de int em Python (True == 1), por isso é barrado à parte.
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ErroLLM("TIMEOUT_LLM deve ser um número positivo em config.py.")

    # httpx.Timeout(total, connect=...): o cliente do Ollama usa httpx por
    # baixo, e o LangChain repassa este objeto a ele via `client_kwargs`.
    return (
        modelo.strip(),
        base_url.strip().rstrip("/"),
        httpx.Timeout(float(timeout), connect=TIMEOUT_CONEXAO),
    )


# --------------------------------------------------------- tradução de erros


@contextmanager
def traduzir_erros(modelo: str) -> Generator[None, None, None]:
    """Converte as exceções do Ollama/LangChain levantadas no bloco em ErroLLM.

    Uso:
        with traduzir_erros("gemma2:2b"):
            resposta = chat.invoke(prompt)

    Args:
        modelo: Nome do modelo em uso (aparece na dica de ``ollama pull``).

    Raises:
        ErroLLM: No lugar de qualquer falha de comunicação ou do servidor.
            Outras exceções (por exemplo, um ErroLLM já levantado ou um erro
            de programação) passam sem alteração.
    """
    try:
        yield
    except ollama.ResponseError as exc:
        # O servidor respondeu, mas com erro HTTP. 404 quase sempre é modelo
        # não baixado no Ollama.
        mensagem = f"O Ollama retornou HTTP {exc.status_code}. Detalhe: {exc.error}."
        if exc.status_code == 404:
            mensagem += f" Verifique se o modelo '{modelo}' está instalado (ollama pull {modelo})."
        raise ErroLLM(mensagem) from exc
    except httpx.TimeoutException as exc:
        # Vem antes do ConnectError porque o tempo esgotado também é um erro de
        # transporte do httpx; a mensagem aqui é mais útil.
        raise ErroLLM(
            "O Ollama excedeu o tempo limite de conexão ou resposta. Verifique o "
            "serviço e, se necessário, aumente TIMEOUT_LLM em config.py."
        ) from exc
    except (ConnectionError, httpx.ConnectError) as exc:
        # Servidor desligado: o cliente do Ollama às vezes levanta o
        # ConnectionError do Python, às vezes o httpx.ConnectError (depende de
        # a chamada ser em streaming ou não). Os dois significam o mesmo.
        raise ErroLLM(
            f"Não foi possível conectar ao Ollama em {config.OLLAMA_URL}. "
            "Verifique se o serviço está em execução."
        ) from exc
    except httpx.HTTPError as exc:
        # Qualquer outra falha de rede (rede caiu no meio da resposta etc.).
        raise ErroLLM(f"Falha na comunicação com o Ollama: {exc}") from exc


# ----------------------------------------------------------------- chat (LLM)


def criar_chat(formato: dict | None = None) -> ChatOllama:
    """Cria o modelo de chat do LangChain com o modelo de config.MODELO.

    Args:
        formato: JSON Schema que a resposta deve seguir (saída estruturada do
            Ollama). Com ele, o Ollama só deixa o modelo gerar um JSON que
            caiba no esquema: sem Markdown, sem texto antes ou depois. None
            (padrão) deixa a resposta livre.

    O objeto devolvido é um ``Runnable``: pode ser chamado direto
    (``chat.invoke("texto")``) ou encadeado com ``|`` numa cadeia LCEL.
    Criar o objeto não contata o Ollama; a conexão só acontece no ``invoke``.

    Raises:
        ErroLLM: Se a configuração for inválida.
    """
    modelo, base_url, timeout = _ler_config("MODELO")
    return ChatOllama(
        model=modelo,
        base_url=base_url,
        client_kwargs={"timeout": timeout},
        format=formato,
    )


def perguntar(prompt: str, formato: dict | None = None) -> str:
    """
    Envia um prompt ao modelo definido em config.py, via Ollama.

    Args:
        prompt: Instruções e contexto preparados pelo agente.
        formato: JSON Schema que a resposta deve seguir (ver criar_chat).

    Returns:
        Texto gerado pelo modelo.

    Raises:
        TypeError: Se o prompt não for uma string.
        ValueError: Se o prompt estiver vazio.
        ErroLLM: Se a configuração for inválida ou a chamada falhar.
    """
    # 1. Valida o prompt recebido do agente.
    if not isinstance(prompt, str):
        raise TypeError("O prompt deve ser uma string.")

    if not prompt.strip():
        raise ValueError("O prompt não pode estar vazio.")

    # 2. Cria o chat e envia. Um texto puro vira uma única mensagem do
    #    usuário ("human"). Isso importa para o Gemma 2, que não tem papel
    #    "system": todas as instruções já vêm dentro do próprio prompt.
    chat = criar_chat(formato)
    with traduzir_erros(config.MODELO):
        mensagem = chat.invoke(prompt)

    # 3. O chat devolve uma mensagem (AIMessage); o texto fica em .content.
    texto = mensagem.content
    if not isinstance(texto, str) or not texto.strip():
        raise ErroLLM("O modelo retornou uma resposta vazia.")

    return texto.strip()


# ------------------------------------------------------------------ embeddings


def _validar_textos(textos: list[str]) -> None:
    """Barra entradas que o modelo de embeddings não deve receber.

    Raises:
        TypeError: Se textos não for uma lista de strings.
        ValueError: Se a lista estiver vazia ou houver texto vazio.
    """
    if not isinstance(textos, list) or not all(isinstance(t, str) for t in textos):
        raise TypeError("textos deve ser uma lista de strings.")

    # Texto vazio não tem significado: alguns modelos falham, outros devolvem
    # um vetor sem sentido. Melhor barrar aqui com uma mensagem clara.
    if not textos or any(not t.strip() for t in textos):
        raise ValueError("A lista de textos e cada texto não podem estar vazios.")


class EmbeddingsOllama(Embeddings):
    """Modelo de embeddings do Ollama com os prefixos do RAG e erros em ErroLLM.

    É um ``Embeddings`` do LangChain, então o Chroma e a Indexing API o aceitam
    diretamente. Embrulha (não substitui) o ``OllamaEmbeddings`` do
    ``langchain-ollama`` para acrescentar três coisas:

    1. Prefixos: o nomic-embed-text foi treinado para distinguir "texto de
       documento" de "texto de pergunta". O LangChain separa os dois casos em
       métodos diferentes (``embed_documents`` e ``embed_query``), e é ali que
       cada prefixo entra (config.RAG_PREFIXO_DOCUMENTO / _CONSULTA).
    2. Erros: toda falha do Ollama vira ErroLLM (ver traduzir_erros).
    3. Conferência: um vetor por texto, nenhum vazio. O RAG liga vetor e
       trecho pela posição; um vetor a menos trocaria os trechos sem erro.
    """

    def __init__(
        self,
        base: Embeddings | None = None,
        prefixo_documento: str | None = None,
        prefixo_consulta: str | None = None,
    ):
        """
        Args:
            base: Embeddings que de fato gera os vetores. Padrão: um
                ``OllamaEmbeddings`` com config.MODELO_EMBEDDING. Nos testes,
                passa-se um falso, sem rede.
            prefixo_documento: Padrão: config.RAG_PREFIXO_DOCUMENTO.
            prefixo_consulta: Padrão: config.RAG_PREFIXO_CONSULTA.

        Raises:
            ErroLLM: Se a configuração do Ollama for inválida.
        """
        if base is None:
            modelo, base_url, timeout = _ler_config("MODELO_EMBEDDING")
            # Criar o OllamaEmbeddings não contata o Ollama; só embed_* contata.
            base = OllamaEmbeddings(
                model=modelo, base_url=base_url, client_kwargs={"timeout": timeout}
            )
        self.base = base
        # Nome do modelo, só para as mensagens de erro (um falso pode não ter).
        self.modelo = getattr(base, "model", config.MODELO_EMBEDDING)
        self.prefixo_documento = (
            config.RAG_PREFIXO_DOCUMENTO if prefixo_documento is None else prefixo_documento
        )
        self.prefixo_consulta = (
            config.RAG_PREFIXO_CONSULTA if prefixo_consulta is None else prefixo_consulta
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Um vetor por texto indexado (trechos da base), na mesma ordem.

        Raises:
            TypeError, ValueError: Entrada inválida (ver _validar_textos).
            ErroLLM: Falha do Ollama ou resposta incompleta.
        """
        _validar_textos(texts)
        # O OllamaEmbeddings envia todos os textos numa requisição só
        # (/api/embed aceita lista). Quem limita o tamanho do lote é quem
        # chama: a Indexing API, com batch_size=config.RAG_LOTE_EMBEDDING.
        with traduzir_erros(self.modelo):
            vetores = self.base.embed_documents([self.prefixo_documento + t for t in texts])

        if (
            not isinstance(vetores, list)
            or len(vetores) != len(texts)
            or not all(isinstance(v, list) and v for v in vetores)
        ):
            raise ErroLLM("O Ollama não devolveu um embedding para cada texto.")
        return vetores

    def embed_query(self, text: str) -> list[float]:
        """O vetor da pergunta do usuário (com o prefixo de consulta).

        Raises:
            TypeError, ValueError: Entrada inválida.
            ErroLLM: Falha do Ollama ou resposta vazia.
        """
        _validar_textos([text])
        with traduzir_erros(self.modelo):
            vetor = self.base.embed_query(self.prefixo_consulta + text)

        if not isinstance(vetor, list) or not vetor:
            raise ErroLLM("O Ollama não devolveu o embedding da pergunta.")
        return vetor


def criar_embeddings() -> EmbeddingsOllama:
    """O modelo de embeddings do projeto (config.MODELO_EMBEDDING, com prefixos).

    Raises:
        ErroLLM: Se a configuração for inválida.
    """
    return EmbeddingsOllama()


# ------------------------------------------------------------- leitura de JSON


def extrair_json(texto: str) -> dict:
    """
    Lê o objeto JSON devolvido pelo modelo.

    Modelos pequenos (como o Gemma 2) às vezes colocam o JSON dentro de um
    bloco Markdown (```json ... ```) ou escrevem algo antes/depois. Esta
    função tira isso e devolve só o dicionário.

    Raises:
        ValueError: Se não houver um objeto JSON válido no texto.
    """
    if not isinstance(texto, str):
        raise ValueError("A resposta do modelo não é texto.")

    limpo = texto.strip()
    limpo = re.sub(r"^```(?:json)?\s*", "", limpo)
    limpo = re.sub(r"\s*```$", "", limpo)

    try:
        dados = json.loads(limpo)
    except json.JSONDecodeError:
        inicio = limpo.find("{")
        fim = limpo.rfind("}")
        if inicio == -1 or fim <= inicio:
            raise ValueError("O modelo não retornou um JSON válido.") from None
        try:
            dados = json.loads(limpo[inicio:fim + 1])
        except json.JSONDecodeError as erro:
            raise ValueError("O modelo não retornou um JSON válido.") from erro

    if not isinstance(dados, dict):
        raise ValueError("O modelo não retornou um objeto JSON.")

    return dados
