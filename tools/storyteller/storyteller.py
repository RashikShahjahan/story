from __future__ import annotations

from typing import Any

from mlx_lm import stream_generate
from mlx_lm.utils import _download, load_model, load_tokenizer

from ..common import apply_chat_template, clean_model_output, json_result

MODEL_NAME = "mlx-community/gemma-4-e2b-it-OptiQ-4bit"
MAX_TOKENS = 128000


def _load_model_and_tokenizer(model_name: str) -> tuple[Any, Any]:
    model_path = _download(model_name)
    model, config = load_model(model_path, strict=False)
    tokenizer = load_tokenizer(model_path, eos_token_ids=config.get("eos_token_id"))
    return model, tokenizer


def story_teller(prompt: str) -> str:
    """Write a complete short story from the user's prompt or creative brief."""
    model, tokenizer = _load_model_and_tokenizer(MODEL_NAME)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You are an expert storyteller. Write a complete, vivid short story from the user's brief."},
        {"role": "user", "content": prompt},
    ]
    chat_prompt = apply_chat_template(tokenizer, messages)
    story = clean_model_output("".join(
        chunk.text
        for chunk in stream_generate(
            model,
            tokenizer,
            prompt=chat_prompt,
            max_tokens=MAX_TOKENS,
        )
    ))

    return json_result(story, {"success": True})
