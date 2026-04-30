from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from mlx_lm import generate, load, stream_generate

from tools import TOOL_SCHEMAS, TOOLS, json_result


WORKSPACE = Path(__file__).resolve().parent
PROMPT_PATH = WORKSPACE / "PROMPT.md"
MODEL_ID = "mlx-community/Qwen3.5-9B-OptiQ-4bit"


def _tool_prompt() -> str:
    return (
        "\n\nYou can call tools by outputting one or more blocks exactly like this:\n"
        "<tool_call>{\"name\": \"tool-name\", \"arguments\": {}}</tool_call>\n"
        "Available tools:\n"
        + json.dumps(TOOL_SCHEMAS, ensure_ascii=False, indent=2)
    )


def _render_prompt(messages: list[dict[str, str]], tokenizer: Any) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(messages, tools=TOOL_SCHEMAS, tokenize=False, add_generation_prompt=True)
        except Exception:
            pass
    rendered = []
    for message in messages:
        rendered.append(f"{message['role'].upper()}:\n{message['content']}")
    rendered.append("ASSISTANT:")
    return "\n\n".join(rendered)


def _extract_tool_calls(text: str) -> list[dict[str, Any]]:
    calls = []
    for match in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL):
        calls.append(json.loads(match.group(1)))
    return calls


def _call_tool(call: dict[str, Any]) -> str:
    name = call.get("name")
    arguments = call.get("arguments") or {}
    if name not in TOOLS:
        return json_result(f"Unknown tool: {name}", {"success": False})
    try:
        return TOOLS[name](**arguments)
    except Exception as exc:
        return json_result(f"Tool {name} failed: {exc}", {"success": False, "tool": name})


def _generate_response(model: Any, tokenizer: Any, prompt: str, max_tokens: int, stream: bool) -> str:
    if not stream:
        return generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens)

    chunks = []
    for response in stream_generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens):
        print(response.text, end="", flush=True)
        chunks.append(response.text)
    return "".join(chunks)


def run_agent(user_prompt: str, max_tokens: int, max_tool_rounds: int, stream: bool = False) -> str:
    model, tokenizer = load(MODEL_ID)
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8") + _tool_prompt()
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    final_response = ""
    for _ in range(max_tool_rounds + 1):
        prompt = _render_prompt(messages, tokenizer)
        response = _generate_response(model, tokenizer, prompt, max_tokens, stream)
        final_response = response.strip()
        tool_calls = _extract_tool_calls(final_response)
        if not tool_calls:
            return final_response
        messages.append({"role": "assistant", "content": final_response})
        for call in tool_calls:
            result = _call_tool(call)
            messages.append({"role": "tool", "content": result})
    return final_response


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the story animation model with PROMPT.md tools.")
    parser.add_argument("prompt", nargs="*", help="User request. If omitted, stdin is used.")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--max-tool-rounds", type=int, default=6)
    args = parser.parse_args()

    user_prompt = " ".join(args.prompt).strip() or sys.stdin.read().strip()
    if not user_prompt:
        raise SystemExit("Provide a prompt argument or stdin input.")

    run_agent(user_prompt, args.max_tokens, args.max_tool_rounds, stream=True)
    print()


if __name__ == "__main__":
    main()
