from __future__ import annotations

from typing import Callable

from .animator.animator import animator
from .browser.browser import show_in_browser
from .files.files import write_file
from .scriptwriter.scriptwriter import script_writer
from .soundtracks.soundtracks import search_soundtracks
from .storyteller.storyteller import story_teller
from .tts.tts import kokoro_tts
from .webfetch.webfetch import webfetch


TOOLS: dict[str, Callable[..., str]] = {
    "story-teller": story_teller,
    "script-writer": script_writer,
    "animator": animator,
    "write-file": write_file,
    "kokoro-tts": kokoro_tts,
    "search-soundtracks": search_soundtracks,
    "show-in-browser": show_in_browser,
    "webfetch": webfetch,
}


def _tool_schema(name: str, description: str | None, properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
    parameters: dict[str, object] = {"type": "object", "properties": properties}
    if required:
        parameters["required"] = required
    return {"type": "function", "function": {"name": name, "description": description, "parameters": parameters}}


TOOL_SCHEMAS = [
    _tool_schema(
        "story-teller",
        story_teller.__doc__,
        {"prompt": {"type": "string"}},
        ["prompt"],
    ),
    _tool_schema(
        "script-writer",
        script_writer.__doc__,
        {"story": {"type": "string"}},
        ["story"],
    ),
    _tool_schema(
        "animator",
        animator.__doc__,
        {
            "script": {"type": "string"},
            "title": {"type": "string"},
            "outputPath": {"type": "string"},
        },
        ["script"],
    ),
    _tool_schema(
        "write-file",
        write_file.__doc__,
        {"path": {"type": "string"}, "content": {"type": "string"}},
        ["path", "content"],
    ),
    _tool_schema(
        "kokoro-tts",
        kokoro_tts.__doc__,
        {
            "text": {"type": "string"},
            "outputPath": {"type": "string"},
            "voice": {"type": "string"},
            "langCode": {"type": "string"},
            "speed": {"type": "number"},
            "splitPattern": {"type": "string"},
            "device": {"type": "string"},
        },
        ["text"],
    ),
    _tool_schema(
        "search-soundtracks",
        search_soundtracks.__doc__,
        {
            "query": {"type": "string"},
            "count": {"type": "integer"},
            "page": {"type": "integer"},
            "category": {"type": "string"},
            "source": {"type": "string"},
            "license": {"type": "string"},
            "extension": {"type": "string"},
            "minDurationSeconds": {"type": "integer"},
            "maxDurationSeconds": {"type": "integer"},
            "includeMature": {"type": "boolean"},
        },
        ["query"],
    ),
    _tool_schema(
        "show-in-browser",
        show_in_browser.__doc__,
        {"target": {"type": "string"}, "targets": {"type": "array", "items": {"type": "string"}}, "secondsPerAnimation": {"type": "number"}},
    ),
    _tool_schema(
        "webfetch",
        webfetch.__doc__,
        {
            "url": {"type": "string"},
            "format": {"type": "string", "enum": ["markdown", "text", "html"]},
            "timeout": {"type": "integer"},
        },
        ["url"],
    ),
]


__all__ = ["TOOLS", "TOOL_SCHEMAS"]
