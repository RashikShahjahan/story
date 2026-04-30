from __future__ import annotations

import re

from .common import ENTRY_SEPARATOR, WORKSPACE, json_result


MEMORY_DIR = WORKSPACE / ".opencode" / "memories"
MEMORY_TARGETS = {
    "memory": {"file": "MEMORY.md", "label": "MEMORY (agent notes)", "limit": 2200},
    "user": {"file": "USER.md", "label": "USER PROFILE", "limit": 1375},
}


def _memory_path(target: str):
    return MEMORY_DIR / MEMORY_TARGETS[target]["file"]


def _parse_target(value: str | None) -> str:
    target = (value or "memory").strip().lower()
    if target not in MEMORY_TARGETS:
        raise ValueError(f'target must be either "memory" or "user", got: {value}')
    return target


def _parse_entries(text: str) -> list[str]:
    return [entry.strip().replace("\r\n", "\n") for entry in re.split(rf"\s*{ENTRY_SEPARATOR}\s*", text) if entry.strip()]


def _read_entries(target: str) -> list[str]:
    path = _memory_path(target)
    if not path.exists():
        return []
    return _parse_entries(path.read_text(encoding="utf-8"))


def _write_entries(target: str, entries: list[str]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    normalized = [entry.strip().replace("\r\n", "\n") for entry in entries if entry.strip()]
    content = f"\n{ENTRY_SEPARATOR}\n".join(normalized)
    _memory_path(target).write_text(f"{content}\n" if content else "", encoding="utf-8")


def _usage(target: str, entries: list[str]) -> dict[str, int]:
    used = len(ENTRY_SEPARATOR.join(entries))
    limit = int(MEMORY_TARGETS[target]["limit"])
    return {"used": used, "limit": limit, "percent": round((used / limit) * 100)}


def _format_store(target: str, entries: list[str]) -> str:
    config = MEMORY_TARGETS[target]
    usage = _usage(target, entries)
    body = ENTRY_SEPARATOR.join(entries) if entries else "(empty)"
    return f"{config['label']} [{usage['percent']}% - {usage['used']}/{usage['limit']} chars]\n{body}"


def get_memories() -> str:
    """Read the session-start snapshot of bounded persistent memory stores."""
    stores = [_format_store(target, _read_entries(target)) for target in ("memory", "user")]
    return json_result("\n\n".join(stores))


def _assert_safe_memory(content: str) -> None:
    if ENTRY_SEPARATOR in content:
        raise ValueError(f"memory content cannot contain the {ENTRY_SEPARATOR} delimiter")
    blocked_patterns = [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|system|developer)",
        r"(reveal|print|dump|exfiltrate).{0,40}(system prompt|developer message|secrets?|credentials?)",
        r"(?:password|token|secret|api[_ -]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    ]
    if any(re.search(pattern, content, re.IGNORECASE) for pattern in blocked_patterns):
        raise ValueError("memory content matched a blocked injection or secret pattern")


def memory(action: str, target: str | None = None, content: str | None = None, old_text: str | None = None) -> str:
    """Manage bounded persistent memory stores with add, replace, and remove actions."""
    action = action.strip().lower()
    if action not in {"add", "replace", "remove"}:
        raise ValueError(f'action must be "add", "replace", or "remove", got: {action}')

    parsed_target = _parse_target(target)
    entries = _read_entries(parsed_target)

    def success(next_entries: list[str], message: str) -> str:
        return json_result(
            f"{message}\n{_format_store(parsed_target, next_entries)}",
            {"success": True, "action": action, "target": parsed_target, "usage": _usage(parsed_target, next_entries)},
        )

    if action == "add":
        new_content = (content or "").strip()
        if not new_content:
            raise ValueError("content is required for add and replace actions")
        _assert_safe_memory(new_content)
        if new_content in entries:
            return success(entries, f"Duplicate {parsed_target} memory not added.")
        next_entries = [*entries, new_content]
        if _usage(parsed_target, next_entries)["used"] > MEMORY_TARGETS[parsed_target]["limit"]:
            return json_result("Memory capacity would be exceeded.", {"success": False, "error": "capacity_exceeded"})
        _write_entries(parsed_target, next_entries)
        return success(next_entries, f"Added {parsed_target} memory.")

    needle = (old_text or "").strip()
    if not needle:
        raise ValueError("old_text must not be empty")
    matches = [(index, entry) for index, entry in enumerate(entries) if needle in entry]
    if len(matches) != 1:
        return json_result(
            f"Expected exactly one {parsed_target} memory entry matching old_text; found {len(matches)}.",
            {"success": False, "error": "not_found" if not matches else "ambiguous_match", "current_entries": entries},
        )

    index, old_entry = matches[0]
    if action == "remove":
        next_entries = [entry for entry_index, entry in enumerate(entries) if entry_index != index]
        _write_entries(parsed_target, next_entries)
        return success(next_entries, f"Removed {parsed_target} memory: {old_entry}")

    new_content = (content or "").strip()
    if not new_content:
        raise ValueError("content is required for add and replace actions")
    _assert_safe_memory(new_content)
    next_entries = [new_content if entry_index == index else entry for entry_index, entry in enumerate(entries)]
    if _usage(parsed_target, next_entries)["used"] > MEMORY_TARGETS[parsed_target]["limit"]:
        return json_result("Memory capacity would be exceeded.", {"success": False, "error": "capacity_exceeded"})
    _write_entries(parsed_target, next_entries)
    return success(next_entries, f"Replaced {parsed_target} memory.")
