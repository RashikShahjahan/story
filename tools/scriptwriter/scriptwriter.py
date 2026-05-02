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


def script_writer(story: str) -> str:
    """Turn a story into a scene-by-scene script with voiceover, dialogue, animation, and soundtrack notes."""
    model, tokenizer = _load_model_and_tokenizer(MODEL_NAME)
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an expert script writer for animated shorts. Split the story into a list of scenes. "
                "Use 6 to 8 scenes unless the user's request explicitly requires a different count. "
                "Use voiceover narration for exposition, transitions, inner thoughts, and scene-setting. "
                "Use dialogue only for words spoken by characters on screen. If the story does not call for "
                "dialogue, use an empty dialogue list. Return only valid JSON in this format:\n"
                "[\n"
                "  {\"voiceover\": \"Voiceover narration text for Scene 1\", \"dialogue\": [{\"character\": \"Character name\", \"line\": \"Spoken dialogue line\"}], \"animation\": \"Description of the animation for Scene 1\", \"soundtrack\": \"Description of soundtrack to use for Scene 1\"},\n"
                "  {\"voiceover\": \"Voiceover narration text for Scene N\", \"dialogue\": [{\"character\": \"Character name\", \"line\": \"Spoken dialogue line\"}], \"animation\": \"Description of the animation for Scene N\", \"soundtrack\": \"Description of soundtrack to use for Scene N\"}\n"
                "]\n"
                "For each scene, keep spoken content in playback order. If both voiceover and dialogue happen "
                "in the same scene, make the animation clear about who is speaking and when. Dialogue should "
                "be concise enough to fit the scene timing."
            ),
        },
        {"role": "user", "content": story},
    ]
    chat_prompt = apply_chat_template(tokenizer, messages)
    script = clean_model_output("".join(
        chunk.text
        for chunk in stream_generate(
            model,
            tokenizer,
            prompt=chat_prompt,
            max_tokens=MAX_TOKENS,
        )
    ))

    return json_result(script, {"success": True})
