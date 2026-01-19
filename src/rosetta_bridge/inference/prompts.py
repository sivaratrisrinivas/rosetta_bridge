from __future__ import annotations

import json
from typing import Any

from rosetta_bridge.analyzer.sampler import detect_pii


def get_system_prompt() -> str:
    return (
        "You are a Data Architect. Given a database table and columns, "
        "infer business meaning, propose clear semantic names, and describe intent. "
        "Return concise, structured output."
    )


def build_user_prompt(
    table_name: str,
    columns: list[dict[str, Any]],
    scrub_pii: bool = True,
) -> str:
    sanitized_columns = []
    for column in columns:
        samples = list(column.get("samples", []))
        if scrub_pii and detect_pii(samples):
            samples = []
        sanitized_columns.append(
            {
                "name": column.get("name"),
                "type": column.get("type"),
                "samples": samples,
            }
        )

    payload = {
        "table": table_name,
        "columns": sanitized_columns,
    }

    return (
        "Use the following schema context to infer semantic names and descriptions.\n"
        + json.dumps(payload, indent=2)
    )
