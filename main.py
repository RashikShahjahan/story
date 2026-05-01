from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from mlx_lm import stream_generate
from mlx_lm.utils import _download, load_model, load_tokenizer

from tools import TOOL_SCHEMAS
from tools.tool_helper import (
    HiddenSpanCapture,
    ToolCallCapture,
    execute_tool_call,
    parse_tool_calls,
    tool_message,
)


MODEL_NAME = "mlx-community/gemma-4-e4b-it-OptiQ-4bit"
MAX_TOKENS = 128_000
MAX_TOOL_ROUNDS = 16
WORKSPACE = Path(__file__).resolve().parent


def load_model_and_tokenizer(model_name: str) -> tuple[Any, Any]:
    model_path = _download(model_name)
    # Gemma4 shared-KV checkpoints include unused K/V tensors for shared layers.
    model, config = load_model(model_path, strict=False)
    tokenizer = load_tokenizer(model_path, eos_token_ids=config.get("eos_token_id"))
    return model, tokenizer


def _load_system_prompt() -> str:
    return (WORKSPACE / "DIRECTOR.md").read_text(encoding="utf-8")


def _prompt_for(messages: list[dict[str, Any]], tokenizer: Any) -> str | list[int]:
    return tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tools=TOOL_SCHEMAS,
    )


def stream_events(
    model: Any,
    tokenizer: Any,
    messages: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    for _ in range(MAX_TOOL_ROUNDS + 1):
        thought_stream = HiddenSpanCapture("<|channel>thought", "<channel|>")
        stream = ToolCallCapture(tokenizer.tool_call_start, tokenizer.tool_call_end, hide_tool_calls=True)
        prompt = _prompt_for(messages, tokenizer)

        for chunk in stream_generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=MAX_TOKENS,
        ):
            visible = stream.push(thought_stream.push(chunk.text))
            if visible:
                yield {"type": "text_delta", "text": visible}

        visible = stream.push(thought_stream.finish()) + stream.finish()
        if visible:
            yield {"type": "text_delta", "text": visible}

        if not stream.tool_texts:
            yield {"type": "done"}
            return

        tool_calls = parse_tool_calls(tokenizer, stream.tool_texts, TOOL_SCHEMAS)
        messages.append(
            {
                "role": "assistant",
                "content": stream.visible_text,
                "tool_calls": tool_calls,
            }
        )

        for tool_call in tool_calls:
            name = tool_call["function"]["name"]
            yield {"type": "tool_call", "name": name, "tool_call": tool_call}
            yield {"type": "tool_start", "name": name, "tool_call": tool_call}
            result = execute_tool_call(tool_call)
            yield {
                "type": "tool_result",
                "name": name,
                "tool_call": tool_call,
                "result": result,
            }
            messages.append(tool_message(tool_call, result))

    raise RuntimeError(f"stopped after {MAX_TOOL_ROUNDS} tool rounds")


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
    model, tokenizer = load_model_and_tokenizer(MODEL_NAME)
    user_input = input("Enter your request: ")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _load_system_prompt()},
        {"role": "user", "content": user_input},
    ]

    render_events(stream_events(model, tokenizer, messages))


if __name__ == "__main__":
    main()
