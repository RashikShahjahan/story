from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from mlx_lm import load, stream_generate

from tools import TOOL_SCHEMAS, TOOLS, json_result


WORKSPACE = Path(__file__).resolve().parent
PROMPT_PATH = WORKSPACE / "PROMPT.md"
MODEL_ID = "mlx-community/Qwen3.5-9B-OptiQ-4bit"
TOOL_CALL_OPEN = "<tool_call>"
TOOL_CALL_CLOSE = "</tool_call>"
THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"


def _tool_prompt() -> str:
    return (
        "\n\n# Tools\n\n"
        "You have access to the following functions:\n\n"
        "<tools>\n"
        + "\n".join(json.dumps(tool, ensure_ascii=False) for tool in TOOL_SCHEMAS)
        + "\n</tools>\n\n"
        "If you choose to call a function ONLY reply in this Qwen3.5 format with NO suffix. "
        "Call one function per assistant turn; wait for the tool response before calling another function.\n\n"
        "<tool_call>\n"
        "<function=tool-name>\n"
        "<parameter=arg>value</parameter>\n"
        "</function>\n"
        "</tool_call>\n\n"
        "You may provide private reasoning before the function call, but do not write user-facing text after it."
    )


def _render_prompt(messages: list[dict[str, Any]], tokenizer: Any) -> str:
    apply_chat_template = getattr(tokenizer, "apply_chat_template", None)
    if apply_chat_template:
        for extra_kwargs in ({"enable_thinking": False}, {}):
            try:
                return apply_chat_template(
                    messages,
                    tools=TOOL_SCHEMAS,
                    tokenize=False,
                    add_generation_prompt=True,
                    **extra_kwargs,
                )
            except TypeError:
                if extra_kwargs:
                    continue
                break
            except Exception:
                break
    return _render_qwen35_prompt(messages)


def _render_qwen35_prompt(messages: list[dict[str, Any]]) -> str:
    system_message = ""
    remaining_messages = messages
    if messages and messages[0].get("role") == "system":
        system_message = str(messages[0].get("content") or "").strip()
        remaining_messages = messages[1:]

    rendered = ["<|im_start|>system\n", _tool_prompt().strip()]
    if system_message:
        rendered.append("\n\n" + system_message)
    rendered.append("<|im_end|>\n")

    index = 0
    while index < len(remaining_messages):
        message = remaining_messages[index]
        role = message.get("role")
        content = str(message.get("content") or "")

        if role == "tool":
            rendered.append("<|im_start|>user")
            while index < len(remaining_messages) and remaining_messages[index].get("role") == "tool":
                rendered.append("\n<tool_response>\n")
                rendered.append(str(remaining_messages[index].get("content") or ""))
                rendered.append("\n</tool_response>")
                index += 1
            rendered.append("<|im_end|>\n")
            continue

        if role in {"user", "system"}:
            rendered.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")
        elif role == "assistant":
            rendered.append("<|im_start|>assistant\n")
            if content.strip():
                rendered.append(content.strip())
            for tool_call in message.get("tool_calls") or []:
                if content.strip() or not rendered[-1].endswith("\n"):
                    rendered.append("\n")
                rendered.append(_render_tool_call(tool_call))
            rendered.append("<|im_end|>\n")
        index += 1

    rendered.append("<|im_start|>assistant\n<think>\n\n</think>\n\n")
    return "".join(rendered)


def _render_tool_call(tool_call: dict[str, Any]) -> str:
    function = tool_call.get("function") or tool_call
    name = function.get("name", "")
    arguments = _parse_tool_arguments(function.get("arguments") or {})
    lines = [TOOL_CALL_OPEN, f"<function={name}>"]
    for key, value in arguments.items():
        if isinstance(value, (dict, list, bool, int, float)) or value is None:
            rendered_value = json.dumps(value, ensure_ascii=False)
        else:
            rendered_value = str(value)
        lines.append(f"<parameter={key}>\n{rendered_value}\n</parameter>")
    lines.extend(["</function>", TOOL_CALL_CLOSE])
    return "\n".join(lines)


def _extract_tool_calls(text: str) -> list[dict[str, Any]]:
    calls = []
    for match in re.finditer(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL):
        block = match.group(1).strip()
        if not block:
            continue
        if block.startswith("{"):
            try:
                call = _normalize_tool_call(json.loads(block))
            except json.JSONDecodeError:
                continue
            if call:
                calls.append(call)
            continue
        for function_match in re.finditer(r"<function=([^>\s]+)>\s*(.*?)\s*</function>", block, re.DOTALL):
            arguments = {}
            body = function_match.group(2)
            for parameter_match in re.finditer(r"<parameter=([^>\s]+)>\s*(.*?)\s*</parameter>", body, re.DOTALL):
                raw_value = html.unescape(parameter_match.group(2)).strip()
                arguments[parameter_match.group(1)] = _parse_tool_argument(raw_value)
            calls.append({"name": function_match.group(1), "arguments": arguments})
    return calls


def _normalize_tool_call(call: dict[str, Any]) -> dict[str, Any] | None:
    function = call.get("function") or call
    name = function.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    return {"name": name.strip(), "arguments": _parse_tool_arguments(function.get("arguments") or {})}


def _parse_tool_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str) and arguments.strip():
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _parse_tool_argument(value: str) -> Any:
    if not value:
        return value
    if value in {"true", "false", "null"} or value[:1] in {'"', "[", "{", "-"} or value[:1].isdigit():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _call_tool(call: dict[str, Any]) -> str:
    name = call.get("name")
    arguments = _parse_tool_arguments(call.get("arguments") or {})
    if name not in TOOLS:
        return json_result(f"Unknown tool: {name}", {"success": False})
    try:
        return TOOLS[name](**arguments)
    except Exception as exc:
        return json_result(f"Tool {name} failed: {exc}", {"success": False, "tool": name})


def _generate_response(model: Any, tokenizer: Any, prompt: str, max_tokens: int) -> str:
    text = ""
    printed_length = 0
    for response in stream_generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens):
        text += response.text
        printed_length = _print_visible_delta(text, printed_length, final=False)
        tool_call_end = _first_tool_call_end(text)
        if tool_call_end is not None:
            text = text[:tool_call_end]
            _print_visible_delta(text, printed_length, final=True)
            return text
    _print_visible_delta(text, printed_length, final=True)
    return text


def _first_tool_call_end(text: str) -> int | None:
    start = text.find(TOOL_CALL_OPEN)
    if start == -1:
        return None
    end = text.find(TOOL_CALL_CLOSE, start)
    if end == -1:
        return None
    return end + len(TOOL_CALL_CLOSE)


def _print_visible_delta(text: str, printed_length: int, final: bool) -> int:
    visible = _visible_response_text(text, final=final)
    if len(visible) > printed_length:
        print(visible[printed_length:], end="", flush=True)
        return len(visible)
    return printed_length


def _visible_response_text(text: str, final: bool) -> str:
    visible = re.sub(r"<\|im_start\|>\s*assistant\s*", "", text)
    visible = re.sub(r"<\|im_end\|>.*$", "", visible, flags=re.DOTALL)
    visible = re.sub(r"<think>.*?</think>\s*", "", visible, flags=re.DOTALL)
    visible = re.sub(r"<think>.*$", "", visible, flags=re.DOTALL)
    if TOOL_CALL_OPEN in visible:
        visible = visible.split(TOOL_CALL_OPEN, 1)[0]
    return visible if final else _hold_partial_hidden_tag(visible)


def _hold_partial_hidden_tag(text: str) -> str:
    hidden_tags = (TOOL_CALL_OPEN, THINK_OPEN, "<|im_start|>", "<|im_end|>")
    max_tag_length = max(len(tag) for tag in hidden_tags)
    for length in range(min(max_tag_length - 1, len(text)), 0, -1):
        suffix = text[-length:]
        if any(tag.startswith(suffix) for tag in hidden_tags):
            return text[:-length]
    return text


def _clean_response(text: str) -> str:
    cleaned = _visible_response_text(text, final=True)
    cleaned = cleaned.replace(THINK_OPEN, "").replace(THINK_CLOSE, "")
    return cleaned.strip()


def _assistant_tool_message(response: str, tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": _clean_response(response),
        "tool_calls": [
            {
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": _parse_tool_arguments(call.get("arguments") or {}),
                },
            }
            for call in tool_calls
        ],
    }


def run_agent(user_prompt: str, max_tokens: int = 32768, max_tool_rounds: int = 6) -> str:
    model, tokenizer = load(MODEL_ID)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    final_response = ""
    for _ in range(max_tool_rounds + 1):
        prompt = _render_prompt(messages, tokenizer)
        response = _generate_response(model, tokenizer, prompt, max_tokens)
        final_response = _clean_response(response)
        tool_calls = _extract_tool_calls(response)
        if not tool_calls:
            return final_response
        messages.append(_assistant_tool_message(response, tool_calls))
        for call in tool_calls:
            messages.append({"role": "tool", "content": _call_tool(call)})
    return final_response


def main() -> None:
    user_prompt = input().strip()
    if not user_prompt:
        raise SystemExit("Provide a prompt.")

    run_agent(user_prompt)
    print()


if __name__ == "__main__":
    main()
