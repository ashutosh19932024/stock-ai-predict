from __future__ import annotations

from typing import Any


def dedupe_records(records: list[dict[str, Any]], keys: tuple[str, ...] = ("title", "url")) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []

    for record in records:
        signature = tuple(record.get(key) for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        result.append(record)
    return result
