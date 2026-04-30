from __future__ import annotations

from typing import Callable

from .browser import show_in_browser
from .common import json_result
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

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "get-memories", "description": get_memories.__doc__, "parameters": {"type": "object", "properties": {}}}},
    {
        "type": "function",
        "function": {
            "name": "write-file",
            "description": write_file.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "overwrite": {"type": "boolean"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory",
            "description": memory.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "replace", "remove"]},
                    "target": {"type": "string", "enum": ["memory", "user"]},
                    "content": {"type": "string"},
                    "old_text": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kokoro-tts",
            "description": kokoro_tts.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "outputPath": {"type": "string"},
                    "voice": {"type": "string"},
                    "langCode": {"type": "string"},
                    "speed": {"type": "number"},
                    "splitPattern": {"type": "string"},
                    "device": {"type": "string"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search-soundtracks",
            "description": search_soundtracks.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
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
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show-in-browser",
            "description": show_in_browser.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "targets": {"type": "array", "items": {"type": "string"}},
                    "secondsPerAnimation": {"type": "number"},
                },
            },
        },
    },
]


__all__ = ["TOOLS", "TOOL_SCHEMAS", "json_result"]
