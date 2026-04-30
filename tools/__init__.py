from __future__ import annotations

from typing import Callable

from .browser import show_in_browser
from .files import write_file
from .memory import get_memories, memory
from .soundtracks import search_soundtracks
from .tts import kokoro_tts


TOOLS: dict[str, Callable[..., str]] = {
    "get-memories": get_memories,
    "write-file": write_file,
    "memory": memory,
    "kokoro-tts": kokoro_tts,
    "search-soundtracks": search_soundtracks,
    "show-in-browser": show_in_browser,
}


def _tool_schema(name: str, description: str | None, properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
    parameters: dict[str, object] = {"type": "object", "properties": properties}
    if required:
        parameters["required"] = required
    return {"type": "function", "function": {"name": name, "description": description, "parameters": parameters}}


TOOL_SCHEMAS = [
    _tool_schema("get-memories", get_memories.__doc__, {}),
    _tool_schema(
        "write-file",
        write_file.__doc__,
        {"path": {"type": "string"}, "content": {"type": "string"}},
        ["path", "content"],
    ),
    _tool_schema(
        "memory",
        memory.__doc__,
        {
            "action": {"type": "string", "enum": ["add", "replace", "remove"]},
            "target": {"type": "string", "enum": ["memory", "user"]},
            "content": {"type": "string"},
            "old_text": {"type": "string"},
        },
        ["action"],
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
]


__all__ = ["TOOLS", "TOOL_SCHEMAS"]
