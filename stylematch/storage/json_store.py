"""Simple JSON persistence helper.

This module provides a small JSONStore class to read/write a single JSON file. It is intentionally minimal for the starter step.
"""
import json
from pathlib import Path
from typing import Any, Optional


class JSONStore:
    def __init__(self, path: str):
        self.path = Path(path)
        # ensure parent exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[Any]:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, obj: Any) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
