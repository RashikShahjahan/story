from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from mlx_lm import stream_generate
from mlx_lm.utils import _download, load_model, load_tokenizer

from ..common import WORKSPACE, json_result

MODEL_NAME = "mlx-community/Qwen3.5-9B-OptiQ-4bit"
MAX_TOKENS = 128000


def _load_model_and_tokenizer(model_name: str) -> tuple[Any, Any]:
    model_path = _download(model_name)
    model, config = load_model(model_path, strict=False)
    tokenizer = load_tokenizer(model_path, eos_token_ids=config.get("eos_token_id"))
    return model, tokenizer


def _safe_file_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-.")
    return slug[:80] or time.strftime("animation-%Y-%m-%dT%H-%M-%S")


def _resolve_output_path(output_path: str | None, title: str | None, script: str) -> Path:
    if output_path is not None and output_path.strip():
        path = Path(output_path.strip())
        target = path if path.is_absolute() else WORKSPACE / path
    else:
        source = title.strip() if title and title.strip() else script[:48]
        target = WORKSPACE / "animations" / f"{_safe_file_name(source)}.html"
    return target.with_suffix(".html")


def _strip_code_fence(text: str) -> str:
    match = re.fullmatch(r"\s*```(?:html)?\s*(.*?)\s*```\s*", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def animator(script: str, title: str | None = None, outputPath: str | None = None) -> str:
    """Create a self-contained p5.js HTML animation from a script or scene description."""
    model, tokenizer = _load_model_and_tokenizer(MODEL_NAME)
    animator_prompt = (Path(__file__).resolve().parent / "ANIMATOR.md").read_text(encoding="utf-8")
    output_path = _resolve_output_path(outputPath, title, script)
    title_line = f"Title: {title.strip()}\n\n" if title and title.strip() else ""
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                animator_prompt
                + "\n\nReturn only the complete HTML document. Do not wrap it in Markdown. "
                + "Use only inline JavaScript/CSS and CDN scripts. "
                + "If audio files or soundtrack URLs are not provided in the script, create the visual animation without audio."
            ),
        },
        {"role": "user", "content": f"{title_line}Script or scene description:\n{script.strip()}"},
    ]
    chat_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
    html = _strip_code_fence(
        "".join(
            chunk.text
            for chunk in stream_generate(
                model,
                tokenizer,
                prompt=chat_prompt,
                max_tokens=MAX_TOKENS,
            )
        )
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return json_result(
        f"Created animation at {output_path}.",
        {"success": True, "path": str(output_path), "bytes": len(html.encode("utf-8"))},
    )
