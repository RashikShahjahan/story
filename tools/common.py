from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parent.parent
ENTRY_SEPARATOR = "§"
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


def openrouter_model(env_name: str, default: str = "nvidia/nemotron-3-super-120b-a12b:free") -> str:
    return os.environ.get(env_name, default)


def openrouter_chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str,
    max_tokens: int,
    temperature: float = 0.7,
) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required to call OpenRouter.")

    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.environ.get("OPENROUTER_SITE_URL", "http://localhost"),
        "X-Title": os.environ.get("OPENROUTER_APP_NAME", "story"),
    }
    request = urllib.request.Request(OPENROUTER_CHAT_COMPLETIONS_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter request failed with HTTP {error.code}: {details}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"OpenRouter request failed: {error.reason}") from error

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"OpenRouter returned an unexpected response: {data}") from error

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
    return str(content)



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
