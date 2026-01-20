from __future__ import annotations

import json
from typing import Any

from rosetta_bridge.analyzer.sampler import detect_pii


def get_system_prompt() -> str:
    return (
        "You are a Data Architect. Given a database table and columns, "
        "infer business meaning, propose clear semantic names, and describe intent. "
        "Return STRICT JSON only, with this shape:\n"
        '{ "columns": [ { "name": "...", "semantic_name": "...", "description": "..." } ] }'
    )


def build_user_prompt(
    table_name: str,
    columns: list[dict[str, Any]],
    scrub_pii: bool = True,
    table_comment: str | None = None,
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
                "comment": column.get("comment"),
                "samples": samples,
            }
        )

    payload = {
        "table": table_name,
        "table_comment": table_comment,
        "columns": sanitized_columns,
    }

    return (
        "Use the following schema context to infer semantic names and descriptions.\n"
        + json.dumps(payload, indent=2)
    )


def parse_gemini_response(response: str) -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        return {}

    columns = payload.get("columns", [])
    if not isinstance(columns, list):
        return {}

    parsed: dict[str, dict[str, str]] = {}
    for column in columns:
        if not isinstance(column, dict):
            continue
        name = column.get("name")
        semantic_name = column.get("semantic_name")
        description = column.get("description")
        if isinstance(name, str):
            entry: dict[str, str] = {}
            if isinstance(semantic_name, str):
                entry["semantic_name"] = semantic_name
            if isinstance(description, str):
                entry["description"] = description
            if entry:
                parsed[name] = entry
    return parsed
