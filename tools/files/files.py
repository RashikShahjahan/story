from __future__ import annotations

from ..common import WORKSPACE, json_result


def write_file(path: str, content: str) -> str:
    """Write a UTF-8 text file inside the workspace, creating parent directories."""
    target = (WORKSPACE / path.strip()).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return json_result(f"Wrote {target}.", {"path": str(target)})
