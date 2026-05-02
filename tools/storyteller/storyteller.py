from __future__ import annotations

from ..common import clean_model_output, json_result, openrouter_chat_completion, openrouter_model

MODEL_NAME = openrouter_model("OPENROUTER_STORY_MODEL")
MAX_TOKENS = 8192


def story_teller(prompt: str) -> str:
    """Write a complete short story from the user's prompt or creative brief."""
    story = clean_model_output(
        openrouter_chat_completion(
            [
                {"role": "system", "content": "You are an expert storyteller. Write a complete, vivid short story from the user's brief."},
                {"role": "user", "content": prompt},
            ],
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
        )
    )
    return json_result(story, {"success": True})
