from __future__ import annotations

from typing import Any

from tools import TOOLS
from tools.common import json_result


def _suffix_prefix_len(text: str, marker: str) -> int:
    max_len = min(len(text), len(marker) - 1)
    for size in range(max_len, 0, -1):
        if marker.startswith(text[-size:]):
            return size
    return 0


class ToolCallCapture:
    def __init__(self, start_marker: str, end_marker: str, hide_tool_calls: bool = False):
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.hide_tool_calls = hide_tool_calls
        self.visible_parts: list[str] = []
        self.tool_texts: list[str] = []
        self._buffer = ""
        self._tool_parts: list[str] = []
        self._state = "normal"
        self._saw_tool_call = False

    def push(self, text: str) -> str:
        self._buffer += text
        visible_parts: list[str] = []

        while self._buffer:
            if self._state == "normal":
                index = self._buffer.find(self.start_marker)
                if index >= 0:
                    visible = self._buffer[:index]
                    if not self._saw_tool_call or not self.hide_tool_calls:
                        visible_parts.append(visible)
                        self.visible_parts.append(visible)
                    if not self.hide_tool_calls:
                        visible_parts.append(self.start_marker)
                    self._buffer = self._buffer[index + len(self.start_marker) :]
                    self._state = "tool"
                    self._saw_tool_call = True
                    continue

                keep = _suffix_prefix_len(self._buffer, self.start_marker)
                visible = self._buffer[:-keep] if keep else self._buffer
                if visible and (not self._saw_tool_call or not self.hide_tool_calls):
                    visible_parts.append(visible)
                    self.visible_parts.append(visible)
                self._buffer = self._buffer[-keep:] if keep else ""
                break

            index = self._buffer.find(self.end_marker)
            if index >= 0:
                tool_text = self._buffer[:index]
                self._tool_parts.append(tool_text)
                if not self.hide_tool_calls:
                    visible_parts.append(tool_text + self.end_marker)
                self.tool_texts.append("".join(self._tool_parts))
                self._tool_parts = []
                self._buffer = self._buffer[index + len(self.end_marker) :]
                self._state = "normal"
                continue

            keep = _suffix_prefix_len(self._buffer, self.end_marker)
            tool_text = self._buffer[:-keep] if keep else self._buffer
            self._tool_parts.append(tool_text)
            if tool_text and not self.hide_tool_calls:
                visible_parts.append(tool_text)
            self._buffer = self._buffer[-keep:] if keep else ""
            break

        return "".join(visible_parts)

    def finish(self) -> str:
        if self._state == "tool":
            visible = self._buffer if not self.hide_tool_calls else ""
            self._tool_parts.append(self._buffer)
            tool_text = "".join(self._tool_parts)
            if tool_text.strip():
                self.tool_texts.append(tool_text)
            self._buffer = ""
            self._tool_parts = []
            return visible

        visible = self._buffer if not self._saw_tool_call or not self.hide_tool_calls else ""
        self.visible_parts.append(visible)
        self._buffer = ""
        return visible

    @property
    def visible_text(self) -> str:
        return "".join(self.visible_parts)


class HiddenSpanCapture:
    def __init__(self, start_marker: str, end_marker: str):
        self.start_marker = start_marker
        self.end_marker = end_marker
        self._buffer = ""
        self._state = "normal"

    def push(self, text: str) -> str:
        self._buffer += text
        visible_parts: list[str] = []

        while self._buffer:
            if self._state == "normal":
                index = self._buffer.find(self.start_marker)
                if index >= 0:
                    visible_parts.append(self._buffer[:index])
                    self._buffer = self._buffer[index + len(self.start_marker) :]
                    self._state = "hidden"
                    continue

                keep = _suffix_prefix_len(self._buffer, self.start_marker)
                visible_parts.append(self._buffer[:-keep] if keep else self._buffer)
                self._buffer = self._buffer[-keep:] if keep else ""
                break

            index = self._buffer.find(self.end_marker)
            if index >= 0:
                self._buffer = self._buffer[index + len(self.end_marker) :]
                self._state = "normal"
                continue

            keep = _suffix_prefix_len(self._buffer, self.end_marker)
            self._buffer = self._buffer[-keep:] if keep else ""
            break

        return "".join(visible_parts)

    def finish(self) -> str:
        if self._state == "hidden":
            self._buffer = ""
            return ""

        visible = self._buffer
        self._buffer = ""
        return visible


def parse_tool_calls(
    tokenizer: Any,
    tool_texts: list[str],
    tool_schemas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []
    for tool_text in tool_texts:
        parsed = tokenizer.tool_parser(tool_text, tool_schemas)
        for item in parsed if isinstance(parsed, list) else [parsed]:
            tool_call = {"type": "function", "function": {"name": item["name"], "arguments": item["arguments"]}}
            if "id" in item:
                tool_call["id"] = item["id"]
            tool_calls.append(tool_call)
    return tool_calls


def execute_tool_call(tool_call: dict[str, Any]) -> str:
    function = tool_call["function"]
    if function["name"] not in TOOLS:
        return json_result(
            f"Unknown tool: {function['name']}",
            {"success": False, "error": "unknown_tool"},
        )
    return TOOLS[function["name"]](**function["arguments"])


def tool_message(tool_call: dict[str, Any], result: str) -> dict[str, Any]:
    message = {
        "role": "tool",
        "name": tool_call["function"]["name"],
        "content": result,
    }
    if "id" in tool_call:
        message["tool_call_id"] = tool_call["id"]
    return message
