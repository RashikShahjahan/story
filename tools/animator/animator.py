from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..common import WORKSPACE, clean_model_output, json_result, openrouter_chat_completion, openrouter_model

MODEL_NAME = openrouter_model("OPENROUTER_ANIMATOR_MODEL")
MAX_TOKENS = 32768


def _safe_file_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-.")
    return slug[:80] or "animation"


def _resolve_output_path(output_path: str | None, title: str | None, script: str) -> Path:
    animations_dir = WORKSPACE / "animations"
    if output_path and output_path.strip():
        path = Path(output_path.strip()).expanduser()
        return (path if path.is_absolute() else WORKSPACE / path).with_suffix(".html")

    source = title.strip() if title and title.strip() else script[:48]
    return animations_dir / f"{_safe_file_name(source)}.html"


def _strip_code_fence(text: str) -> str:
    match = re.search(r"```(?:html)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def _clean_html_response(text: str) -> str:
    html = _strip_code_fence(clean_model_output(text))
    html_start = re.search(r"<!doctype\s+html\b|<html\b", html, re.IGNORECASE)
    if not html_start:
        raise ValueError("Animator model did not return an HTML document.")
    return html[html_start.start() :].strip()


def _messages(animator_prompt: str, script: str, title: str | None) -> list[dict[str, Any]]:
    title_line = f"Title: {title.strip()}\n\n" if title and title.strip() else ""
    return [
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


def _generate_animation_files(items: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    animator_prompt = (Path(__file__).resolve().parent / "ANIMATOR.md").read_text(encoding="utf-8")
    results = []
    for item in items:
        script = item["script"] or ""
        output_path = _resolve_output_path(item.get("outputPath"), item.get("title"), script)
        text = openrouter_chat_completion(
            _messages(animator_prompt, script, item.get("title")),
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
        )
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
