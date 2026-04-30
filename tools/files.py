from __future__ import annotations

from pathlib import Path

from .common import WORKSPACE, json_result


def _resolve_workspace_path(path: str) -> Path:
    raw_path = path.strip()
    if not raw_path:
        raise ValueError("path is required")
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (WORKSPACE / candidate).resolve()
    workspace = WORKSPACE.resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise ValueError(f"path must be inside the workspace: {path}") from exc
    return resolved


def write_file(path: str, content: str, overwrite: bool = True) -> str:
    """Write a UTF-8 text file inside the workspace, creating parent directories."""
    target = _resolve_workspace_path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return json_result(
        f"Wrote {target}.",
        {"success": True, "path": str(target), "bytes": len(content.encode("utf-8"))},
    )
