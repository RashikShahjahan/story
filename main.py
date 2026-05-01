from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Iterator
from typing import Any

from tools.animator.animator import animator
from tools.browser.browser import show_in_browser
from tools.scriptwriter.scriptwriter import script_writer
from tools.storyteller.storyteller import story_teller
from tools.tts.tts import kokoro_tts


def _result_output(result: str) -> str:
    payload = json.loads(result)
    return str(payload["output"])


def _result_metadata(result: str) -> dict[str, Any]:
    payload = json.loads(result)
    metadata = payload.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _json_text(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    array = re.search(r"\[.*\]", text, re.DOTALL)
    return array.group(0).strip() if array else text.strip()


def _script_scenes(script: str) -> list[Any]:
    try:
        parsed = json.loads(_json_text(script))
    except json.JSONDecodeError:
        return [script]

    scenes = parsed.get("scenes") if isinstance(parsed, dict) else parsed
    return scenes if isinstance(scenes, list) and scenes else [script]


def _scene_text(scene: Any, index: int) -> str:
    if isinstance(scene, dict):
        return json.dumps(scene, ensure_ascii=False, indent=2)
    return f"Scene {index}:\n{scene}"


def _dialogue_lines(scene: dict[str, Any]) -> list[dict[str, str]]:
    dialogue = scene.get("dialogue", [])
    if not isinstance(dialogue, list):
        return []

    lines = []
    for item in dialogue:
        if not isinstance(item, dict):
            continue
        character = str(item.get("character", "Character")).strip() or "Character"
        line = str(item.get("line", "")).strip()
        if line:
            lines.append({"character": character, "line": line})
    return lines


def _with_scene_audio(scene: Any, index: int) -> tuple[Any, list[str]]:
    if not isinstance(scene, dict):
        return scene, []

    audio: list[dict[str, str]] = []
    audio_paths: list[str] = []
    voiceover = str(scene.get("voiceover", "")).strip()
    if voiceover:
        output_path = f"animations/audio/scene-{index:02d}-voiceover.wav"
        result = kokoro_tts(voiceover, outputPath=output_path)
        path = str(_result_metadata(result).get("output_path", output_path))
        audio.append({"type": "voiceover", "text": voiceover, "path": path})
        audio_paths.append(path)

    for dialogue_index, item in enumerate(_dialogue_lines(scene), start=1):
        output_path = f"animations/audio/scene-{index:02d}-dialogue-{dialogue_index:02d}.wav"
        result = kokoro_tts(item["line"], outputPath=output_path)
        path = str(_result_metadata(result).get("output_path", output_path))
        audio.append({"type": "dialogue", "character": item["character"], "text": item["line"], "path": path})
        audio_paths.append(path)

    return {**scene, "audio": audio}, audio_paths


def stream_events(user_input: str) -> Iterator[dict[str, Any]]:
    yield {"type": "tool_start", "name": "story-teller"}
    story = _result_output(story_teller(user_input))
    yield {"type": "text_delta", "text": f"\nStory:\n{story}\n"}

    yield {"type": "tool_start", "name": "script-writer"}
    script = _result_output(script_writer(story))
    yield {"type": "text_delta", "text": f"\nScript:\n{script}\n"}

    animation_paths: list[str] = []
    scenes = _script_scenes(script)
    for index, scene in enumerate(scenes, start=1):
        yield {"type": "tool_start", "name": f"kokoro-tts scene {index}"}
        scene_with_audio, audio_paths = _with_scene_audio(scene, index)
        for path in audio_paths:
            yield {"type": "text_delta", "text": f"\nCreated audio: {path}\n"}

        yield {"type": "tool_start", "name": f"animator scene {index}"}
        title = f"scene-{index:02d}"
        output_path = f"animations/{title}.html"
        result = animator(_scene_text(scene_with_audio, index), title=title, outputPath=output_path)
        metadata = _result_metadata(result)
        if path := metadata.get("path"):
            animation_paths.append(str(path))
            yield {"type": "text_delta", "text": f"\nCreated animation: {path}\n"}

    if animation_paths:
        yield {"type": "tool_start", "name": "show-in-browser"}
        yield {"type": "text_delta", "text": f"\n{_result_output(show_in_browser(targets=animation_paths))}\n"}

    yield {"type": "done"}


def render_events(events: Iterable[dict[str, Any]]) -> None:
    needs_newline = False
    for event in events:
        if event["type"] == "text_delta":
            text = event["text"]
            print(text, end="", flush=True)
            needs_newline = not text.endswith("\n")
        elif event["type"] == "tool_start":
            if needs_newline:
                print(file=sys.stderr, flush=True)
                needs_newline = False
            print(f"[tool] {event['name']}", file=sys.stderr, flush=True)
        elif event["type"] == "done":
            if needs_newline:
                print()


def main() -> None:
    user_input = input("Enter your request: ")
    render_events(stream_events(user_input))


if __name__ == "__main__":
    main()
