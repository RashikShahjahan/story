from __future__ import annotations

import json
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parent.parent
ENTRY_SEPARATOR = "§"


def json_result(output: str, metadata: dict[str, Any] = {}) -> str:
    return json.dumps({"output": output, "metadata": metadata}, ensure_ascii=False)
