from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonRepository:
    def __init__(self, file_path: str = "data/watchlist.json") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text(json.dumps({"watchlist": ["AAPL", "TSLA", "NVDA"]}, indent=2))

    def read(self) -> dict[str, Any]:
        return json.loads(self.file_path.read_text())

    def write(self, payload: dict[str, Any]) -> None:
        self.file_path.write_text(json.dumps(payload, indent=2))
