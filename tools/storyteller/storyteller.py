from typing import Any
from main import load_model_and_tokenizer, render_events, stream_events

MODEL_NAME = "mlx-community/gemma-4-e2b-it-OptiQ-4bit"


def storyteller(prompt:str) -> str:
    model, tokenizer = load_model_and_tokenizer(MODEL_NAME)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You are an expert story teller. Write a story given the following details:"},
        {"role": "user", "content": prompt},
    ]

    render_events(stream_events(model, tokenizer, messages))


