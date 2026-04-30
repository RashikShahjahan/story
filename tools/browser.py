from __future__ import annotations

import re
import webbrowser
from pathlib import Path

from .common import WORKSPACE, json_result


def show_in_browser(target: str | None = None, targets: list[str] | None = None, secondsPerAnimation: float = 8) -> str:
    """Open one local HTML file/URL, or show multiple local animation files as a slideshow."""
    selected_targets = [item.strip() for item in (targets or []) if item.strip()]
    if selected_targets:
        generated_dir = WORKSPACE / "animations"
        generated_dir.mkdir(parents=True, exist_ok=True)
        slides = []
        for index, item in enumerate(selected_targets):
            path = Path(item) if Path(item).is_absolute() else WORKSPACE / item
            if not path.exists():
                raise FileNotFoundError(f"File does not exist: {path}")
            slides.append(f'<section class="slide{" active" if index == 0 else ""}"><iframe src="{path.resolve().as_uri()}"></iframe></section>')
        preview = generated_dir / "story-animations.html"
        preview.write_text(
            f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#050505}}.slide{{position:fixed;inset:0;opacity:0;transition:opacity .5s}}.active{{opacity:1}}iframe{{width:100%;height:100%;border:0}}</style></head><body>{''.join(slides)}<script>const s=[...document.querySelectorAll('.slide')];let i=0;setInterval(()=>{{s[i].classList.remove('active');i=(i+1)%s.length;s[i].classList.add('active')}},{max(1, secondsPerAnimation)*1000});</script></body></html>""",
            encoding="utf-8",
        )
        webbrowser.open(preview.resolve().as_uri())
        return json_result(f"Opened {len(selected_targets)} animations one by one in {preview}.", {"preview_path": str(preview)})

    item = (target or "").strip()
    if not item:
        raise ValueError("target or targets is required")
    if re.match(r"^https?://", item, re.IGNORECASE):
        webbrowser.open(item)
        return json_result(f"Opened {item} in the browser.")
    path = Path(item) if Path(item).is_absolute() else WORKSPACE / item
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    webbrowser.open(path.resolve().as_uri())
    return json_result(f"Opened {path} in the browser.", {"path": str(path)})
