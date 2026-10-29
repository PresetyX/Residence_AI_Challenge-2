"""
Cliente compartilhado de LLM do projeto Destrava.

Envia prompts ao Ollama e retorna o texto gerado.

É o ponto único de entrada dos agentes para o LLM: se config.CLIENTE_LLM for
"transformers", a chamada é repassada para o cliente alternativo (llm.py).

Interface pública:
    perguntar(prompt: str) -> str

Os prompts e as regras de negócio ficam nos agentes,
não neste módulo.
"""

import requests

from . import config


__all__ = ["perguntar", "ErroLLM"]


# Erro próprio do projeto: os agentes tratam só este, seja qual for a falha.
class ErroLLM(RuntimeError):
    """Erro de configuração, comunicação ou resposta do Ollama."""


def perguntar(prompt: str) -> str:
    """
    Envia um prompt ao modelo definido em config.py.

    Usa o Ollama ou o cliente alternativo (llm.py), conforme config.CLIENTE_LLM.

    Args:
        prompt: Instruções e contexto preparados pelo agente.

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

    # 2. Escolhe o cliente de LLM definido no config.py.
    cliente = config.CLIENTE_LLM

    if cliente == "transformers":
        # Import aqui dentro: só carrega o transformers quando for usado.
        from . import llm

        return llm.perguntar(prompt)

    if cliente != "ollama":
        raise ErroLLM(
            'CLIENTE_LLM deve ser "ollama" ou "transformers" em config.py.'
        )

    # 3. Lê e valida as configurações do Ollama.
    modelo = config.MODELO
    base_url = config.OLLAMA_URL
    timeout = config.TIMEOUT_LLM

    if not isinstance(modelo, str) or not modelo.strip():
        raise ErroLLM(
            "MODELO deve ser uma string não vazia em config.py."
        )

    if not isinstance(base_url, str) or not base_url.strip():
        raise ErroLLM(
            "OLLAMA_URL deve ser uma URL não vazia em config.py."
        )

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or timeout <= 0
    ):
        raise ErroLLM(
            "TIMEOUT_LLM deve ser um número positivo em config.py."
        )

    # 4. Monta o endereço: "http://localhost:11434" + "/api/generate".
    url = f"{base_url.strip().rstrip('/')}/api/generate"

    # 5. Monta o pedido: qual modelo, qual texto e receber a resposta inteira
    #    de uma vez (stream False), em vez de palavra por palavra.

    payload = {
        "model": modelo.strip(),
        "prompt": prompt,
        "stream": False,
    }

    # 6. Envia ao Ollama. timeout=(5, timeout): 5 s para conectar e
    #    TIMEOUT_LLM segundos para o modelo responder.
    try:
        resposta = requests.post(
            url,
            json=payload,
            timeout=(5, timeout),
        )
    except requests.exceptions.Timeout as exc:
        raise ErroLLM(
            "O Ollama excedeu o tempo limite de conexão ou resposta. "
            "Verifique o serviço e, se necessário, aumente "
            "TIMEOUT_LLM em config.py."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ErroLLM(
            f"Não foi possível conectar ao Ollama em {base_url}. "
            "Verifique se o serviço está em execução."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ErroLLM(
            f"Falha ao enviar a requisição ao Ollama: {exc}"
        ) from exc

    # 7. Confere o código de status (200 = deu certo; 404, 500... = erro)
    #    e transforma o erro em uma mensagem clara.
    try:
        resposta.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        detalhe = ""

        try:
            dados_erro = resposta.json()
        except ValueError:
            dados_erro = None

        if isinstance(dados_erro, dict):
            erro = dados_erro.get("error")

            if isinstance(erro, str):
                detalhe = erro

        mensagem = (
            f"O Ollama retornou HTTP {resposta.status_code}."
        )

        if detalhe:
            mensagem += f" Detalhe: {detalhe}"

        if resposta.status_code == 404:
            mensagem += (
                " Verifique OLLAMA_URL e se o modelo "
                f"'{modelo.strip()}' está instalado."
            )

        raise ErroLLM(mensagem) from exc

    # 8. Converte a resposta (JSON) em dicionário Python.
    try:
        dados = resposta.json()
    except ValueError as exc:
        raise ErroLLM(
            "O Ollama retornou uma resposta que não é um JSON válido."
        ) from exc

    if not isinstance(dados, dict):
        raise ErroLLM(
            "Formato inesperado na resposta do Ollama: "
            "era esperado um objeto JSON."
        )

    if dados.get("error"):
        raise ErroLLM(
            f"O Ollama informou um erro: {dados['error']}"
        )

    # 9. Pega só o texto gerado (campo "response") e o devolve ao agente.
    texto = dados.get("response")

    if not isinstance(texto, str) or not texto.strip():
        raise ErroLLM(
            "O modelo retornou uma resposta vazia ou sem "
            "o campo 'response' válido."
        )

    return texto.strip()
