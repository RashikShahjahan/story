from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Iterator
from typing import Any

from tools.animator.animator import batch_animator
from tools.browser.browser import show_in_browser
from tools.scriptwriter.scriptwriter import script_writer
from tools.storyteller.storyteller import story_teller
from tools.tts.tts import kokoro_tts


def _result_output(result: str) -> str:
    return json.loads(result)["output"]


def _result_metadata(result: str) -> dict[str, Any]:
    return json.loads(result)["metadata"]


def _json_text(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    array = re.search(r"\[.*\]", text, re.DOTALL)
    return array.group(0).strip() if array else text.strip()


def _script_scenes(script: str) -> list[Any]:
    parsed = json.loads(_json_text(script))
    scenes = parsed.get("scenes") if isinstance(parsed, dict) else parsed
    return scenes


def _scene_text(scene: Any) -> str:
    return json.dumps(scene, ensure_ascii=False, indent=2)


def _dialogue_lines(scene: dict[str, Any]) -> list[dict[str, str]]:
    lines = []
    for item in scene["dialogue"]:
        character = item["character"].strip()
        line = item["line"].strip()
        if line:
            lines.append({"character": character, "line": line})
    return lines


def _with_scene_audio(scene: Any, index: int) -> tuple[Any, list[str]]:
    audio: list[dict[str, str]] = []
    audio_paths: list[str] = []
    voiceover = scene["voiceover"].strip()
    if voiceover:
        output_path = f"animations/audio/scene-{index:02d}-voiceover.wav"
        result = kokoro_tts(voiceover, outputPath=output_path)
        path = _result_metadata(result)["output_path"]
        audio.append({"type": "voiceover", "text": voiceover, "path": path})
        audio_paths.append(path)

    for dialogue_index, item in enumerate(_dialogue_lines(scene), start=1):
        output_path = f"animations/audio/scene-{index:02d}-dialogue-{dialogue_index:02d}.wav"
        result = kokoro_tts(item["line"], outputPath=output_path)
        path = _result_metadata(result)["output_path"]
        audio.append({"type": "dialogue", "character": item["character"], "text": item["line"], "path": path})
        audio_paths.append(path)

    return scene | {"audio": audio}, audio_paths


def stream_events(user_input: str) -> Iterator[dict[str, Any]]:
    yield {"type": "tool_start", "name": "story-teller"}
    story = _result_output(story_teller(user_input))
    yield {"type": "text_delta", "text": f"\nStory:\n{story}\n"}

    yield {"type": "tool_start", "name": "script-writer"}
    script = _result_output(script_writer(story))
    yield {"type": "text_delta", "text": f"\nScript:\n{script}\n"}

    animation_paths: list[str] = []
    animation_inputs: list[dict[str, str]] = []
    scenes = _script_scenes(script)
    for index, scene in enumerate(scenes, start=1):
        yield {"type": "tool_start", "name": f"kokoro-tts scene {index}"}
        scene_with_audio, audio_paths = _with_scene_audio(scene, index)
        for path in audio_paths:
            yield {"type": "text_delta", "text": f"\nCreated audio: {path}\n"}

        title = f"scene-{index:02d}"
        output_path = f"animations/{title}.html"
        animation_inputs.append(
            {"script": _scene_text(scene_with_audio), "title": title, "outputPath": output_path}
        )

    if animation_inputs:
        yield {"type": "tool_start", "name": f"animator {len(animation_inputs)} scenes"}
        result = batch_animator(animation_inputs)
        metadata = _result_metadata(result)
        for item in metadata["animations"]:
            path = item["path"]
            animation_paths.append(path)
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
