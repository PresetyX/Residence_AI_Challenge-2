import json
from pathlib import Path

from openai import OpenAI

from destrava.core.models import Visualization

client = OpenAI()

PROMPT_PATH = Path("destrava/prompts/visualizacao.txt")


def explain_visualization(
    user_message: str,
    visualization: Visualization,
) -> str:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    user_prompt = f"""
Pedido do usuário:
{user_message}

Dados calculados:
{visualization.model_dump_json(indent=2)}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content or ""


def visualization_to_text(visualization: Visualization) -> str:
    return json.dumps(
        visualization.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
