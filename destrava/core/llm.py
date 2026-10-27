import os
from pathlib import Path

from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer

from destrava.core.models import Visualization

load_dotenv()

PROMPT_PATH = Path("destrava/prompts/visualizacao.txt")
MODEL_NAME = os.getenv("LOCAL_LLM_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")

_tokenizer = None
_model = None


def _load_model():
    global _tokenizer, _model

    if _tokenizer is None or _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            device_map="auto",
            torch_dtype="auto",
        )

    return _tokenizer, _model


def explain_visualization(
    user_message: str,
    visualization: Visualization,
) -> str:
    tokenizer, model = _load_model()

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    user_prompt = f"""
Pedido do usuário:
{user_message}

Dados calculados:
{visualization.model_dump_json(indent=2)}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=350,
        temperature=0.3,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

    generated = outputs[0][inputs["input_ids"].shape[1]:]

    return tokenizer.decode(
        generated,
        skip_special_tokens=True,
    ).strip()


def visualization_to_text(visualization: Visualization) -> str:
    import json

    return json.dumps(
        visualization.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
