from __future__ import annotations

import re
from typing import Any, Iterable


_NON_IDENTIFIER = re.compile(r"[^a-zA-Z0-9_]+")


def _to_snake(value: str) -> str:
    base = value.split(".")[-1]
    normalized = _NON_IDENTIFIER.sub("_", base.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized.lower() or "table"


def _json_type(python_type: str) -> str:
    normalized = python_type.strip().lower()
    if normalized == "int":
        return "integer"
    if normalized == "float":
        return "number"
    if normalized == "bool":
        return "boolean"
    return "string"


def render_function_schemas(tables: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    for table in tables:
        table_name = table["table_name"]
        columns = table.get("columns", [])
        properties = {}
        for column in columns:
            name = column.get("original_name")
            if not name:
                continue
            properties[name] = {
                "type": _json_type(column.get("python_type", "string")),
            }
            description = column.get("description")
            if isinstance(description, str):
                properties[name]["description"] = description

        schemas.append(
            {
                "name": f"get_{_to_snake(table_name)}",
                "description": f"Fetch rows from {table_name}",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": [],
                    "additionalProperties": False,
                },
            }
        )
    return schemas
