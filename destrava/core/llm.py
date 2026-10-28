"""
Cliente ALTERNATIVO de LLM do projeto Destrava, via Hugging Face Transformers.

Use quando não for possível instalar o Ollama (ex.: computador da faculdade).
O cliente oficial é o llm_client.py (Ollama). Para usar este, defina
CLIENTE_LLM = "transformers" em config.py. Os agentes não importam este
arquivo diretamente: eles chamam perguntar() do llm_client.py, que repassa
a chamada para cá.

Interface pública:
    perguntar(prompt: str) -> str

O modelo e os parâmetros de geração ficam em config.py
(MODELO_TRANSFORMERS, MAX_TOKENS_TRANSFORMERS, TEMPERATURA_TRANSFORMERS).
O modelo é baixado do Hugging Face na primeira chamada e fica carregado
na memória enquanto o programa estiver rodando.
"""

from . import config
from .llm_client import ErroLLM


__all__ = ["perguntar", "ErroLLM"]

_tokenizer = None
_modelo = None


def _carregar_modelo():
    """Carrega o tokenizer e o modelo uma única vez (na primeira chamada)."""
    global _tokenizer, _modelo

    if _tokenizer is None or _modelo is None:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise ErroLLM(
                "A biblioteca 'transformers' não está instalada. "
                "Ela só é necessária para o cliente alternativo (llm.py)."
            ) from exc

        try:
            _tokenizer = AutoTokenizer.from_pretrained(
                config.MODELO_TRANSFORMERS
            )
            _modelo = AutoModelForCausalLM.from_pretrained(
                config.MODELO_TRANSFORMERS,
                device_map="auto",
                torch_dtype="auto",
            )
        except Exception as exc:
            raise ErroLLM(
                "Não foi possível carregar o modelo "
                f"'{config.MODELO_TRANSFORMERS}': {exc}"
            ) from exc

    return _tokenizer, _modelo


def perguntar(prompt: str) -> str:
    """
    Envia um prompt ao modelo definido em config.MODELO_TRANSFORMERS.

    O prompt vai como uma única mensagem de usuário (sem papel "system"),
    o que funciona tanto para o Qwen quanto para o Gemma 2.

    Args:
        prompt: Instruções e contexto preparados pelo agente.

    Returns:
        Texto gerado pelo modelo.

    Raises:
        TypeError: Se o prompt não for uma string.
        ValueError: Se o prompt estiver vazio.
        ErroLLM: Se o modelo não puder ser carregado ou a geração falhar.
    """
    if not isinstance(prompt, str):
        raise TypeError("O prompt deve ser uma string.")

    if not prompt.strip():
        raise ValueError("O prompt não pode estar vazio.")

    tokenizer, modelo = _carregar_modelo()

    try:
        texto_entrada = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
        entradas = tokenizer(texto_entrada, return_tensors="pt").to(
            modelo.device
        )
        saidas = modelo.generate(
            **entradas,
            max_new_tokens=config.MAX_TOKENS_TRANSFORMERS,
            temperature=config.TEMPERATURA_TRANSFORMERS,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    except Exception as exc:
        raise ErroLLM(f"Falha ao gerar a resposta: {exc}") from exc

    # Devolve só o texto novo, sem repetir o prompt.
    gerado = saidas[0][entradas["input_ids"].shape[1]:]
    texto = tokenizer.decode(gerado, skip_special_tokens=True).strip()

    if not texto:
        raise ErroLLM("O modelo retornou uma resposta vazia.")

    return texto
