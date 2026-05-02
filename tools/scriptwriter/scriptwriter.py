from __future__ import annotations

from typing import Any

from ..common import clean_model_output, json_result, openrouter_chat_completion, openrouter_model

MODEL_NAME = openrouter_model("OPENROUTER_SCRIPT_MODEL")
MAX_TOKENS = 8192


def script_writer(story: str) -> str:
    """Turn a story into a scene-by-scene script with voiceover, dialogue, animation, and soundtrack notes."""
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
    script = clean_model_output(openrouter_chat_completion(messages, model=MODEL_NAME, max_tokens=MAX_TOKENS))

    return json_result(script, {"success": True})
