from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parent.parent
ENTRY_SEPARATOR = "§"


def apply_chat_template(tokenizer: Any, messages: list[dict[str, Any]]) -> Any:
    return tokenizer.apply_chat_template(messages, add_generation_prompt=True, enable_thinking=True)



def json_result(output: str, metadata: dict[str, Any] = {}) -> str:
    return json.dumps({"output": output, "metadata": metadata}, ensure_ascii=False)


def clean_model_output(text: str) -> str:
    text = re.sub(r"<think\b[^>]*>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    text = re.sub(r"^\s*.*?</think>\s*", "", text, count=1, flags=re.DOTALL | re.IGNORECASE).strip()

    channel_markers = ("<channel|>", "<|channel>final")
    marker_positions = [(text.rfind(marker), marker) for marker in channel_markers]
    marker_position, marker = max(marker_positions, key=lambda item: item[0])
    if marker_position >= 0:
        text = text[marker_position + len(marker) :].strip()

    text = re.sub(r"^<\|channel\>\w+\s*", "", text).strip()
    return re.sub(r"(?:<\|im_end\|>|<\|endoftext\|>)\s*$", "", text).strip()
