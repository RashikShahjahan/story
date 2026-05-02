from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from mlx_lm import batch_generate
from mlx_lm.utils import _download, load_model, load_tokenizer

from ..common import WORKSPACE, json_result

MODEL_NAME = "mlx-community/Qwen3.5-4B-OptiQ-4bit"
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
    animations_dir = WORKSPACE / "animations"
    if output_path is not None and output_path.strip():
        path = Path(output_path.strip()).expanduser()
        if path.is_absolute():
            target = path if path.is_relative_to(animations_dir) else animations_dir / path.name
        elif path.parts and path.parts[0] == "animations":
            target = WORKSPACE / path
        else:
            target = animations_dir / path
    else:
        source = title.strip() if title and title.strip() else script[:48]
        target = animations_dir / f"{_safe_file_name(source)}.html"
    return target.with_suffix(".html")


def _strip_code_fence(text: str) -> str:
    match = re.search(r"```(?:html)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def _strip_thinking(text: str) -> str:
    text = re.sub(r"<think\b[^>]*>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"^\s*.*?</think>\s*", "", text, count=1, flags=re.DOTALL | re.IGNORECASE).strip()


def _clean_html_response(text: str) -> str:
    html = _strip_code_fence(_strip_thinking(text))
    html_start = re.search(r"<!doctype\s+html\b|<html\b", html, re.IGNORECASE)
    return html[html_start.start() :].strip() if html_start else html


def _chat_prompt(tokenizer: Any, animator_prompt: str, script: str, title: str | None) -> list[int]:
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
    return tokenizer.apply_chat_template(messages, add_generation_prompt=True)


def _generate_animation_files(items: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    if not items:
        return []

    model, tokenizer = _load_model_and_tokenizer(MODEL_NAME)
    animator_prompt = (Path(__file__).resolve().parent / "ANIMATOR.md").read_text(encoding="utf-8")
    output_paths = [
        _resolve_output_path(item.get("outputPath"), item.get("title"), item["script"] or "")
        for item in items
    ]
    prompts = [
        _chat_prompt(tokenizer, animator_prompt, item["script"] or "", item.get("title"))
        for item in items
    ]
    response = batch_generate(
        model,
        tokenizer,
        prompts=prompts,
        max_tokens=MAX_TOKENS,
    )

    results = []
    for output_path, text in zip(output_paths, response.texts, strict=True):
        html = _clean_html_response(text)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        results.append({"path": str(output_path), "bytes": len(html.encode("utf-8"))})
    return results


def batch_animator(animations: list[dict[str, str | None]]) -> str:
    """Create self-contained p5.js HTML animations from multiple script or scene descriptions."""
    results = _generate_animation_files(animations)
    return json_result(
        f"Created {len(results)} animations.",
        {
            "success": True,
            "animations": results,
            "paths": [item["path"] for item in results],
        },
    )


def animator(script: str, title: str | None = None, outputPath: str | None = None) -> str:
    """Create a self-contained p5.js HTML animation from a script or scene description."""
    results = _generate_animation_files([{"script": script, "title": title, "outputPath": outputPath}])
    result = results[0]
    return json_result(
        f"Created animation at {result['path']}.",
        {"success": True, "path": result["path"], "bytes": result["bytes"]},
    )
