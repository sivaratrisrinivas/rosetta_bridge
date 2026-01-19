from __future__ import annotations

from typing import Iterable


def render_audit_log(rows: Iterable[tuple[str, str, str]]) -> str:
    lines = [
        "| Table | Original Column | Inferred Meaning |",
        "| --- | --- | --- |",
    ]
    for table, original, inferred in rows:
        lines.append(f"| {table} | {original} | {inferred} |")
    return "\n".join(lines) + "\n"
