from __future__ import annotations

from dataclasses import dataclass
import keyword
import re
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader


@dataclass(frozen=True)
class ColumnSpec:
    original_name: str
    python_type: str
    semantic_name: str | None = None
    description: str | None = None
    field_name: str | None = None
    alias: str | None = None
    use_field: bool = False


@dataclass(frozen=True)
class TableSpec:
    table_name: str
    columns: list[ColumnSpec]


_NON_IDENTIFIER = re.compile(r"[^a-zA-Z0-9_]+")


def _sanitize_identifier(value: str) -> str:
    normalized = _NON_IDENTIFIER.sub("_", value.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        return "field"
    if normalized[0].isdigit():
        normalized = f"field_{normalized}"
    if keyword.iskeyword(normalized):
        normalized = f"{normalized}_"
    return normalized


def to_pascal(value: str) -> str:
    base = _sanitize_identifier(value.replace(".", "_"))
    parts = [p for p in base.replace("-", "_").split("_") if p]
    return "".join(part.capitalize() for part in parts) or "Model"


def to_field_name(value: str) -> str:
    return _sanitize_identifier(value).lower()


def _normalize_tables(tables: Iterable[dict[str, Any]]) -> list[TableSpec]:
    normalized = []
    for table in tables:
        columns = []
        for column in table["columns"]:
            original_name = column["original_name"]
            semantic_name = column.get("semantic_name")
            description = column.get("description")
            field_name = to_field_name(semantic_name or original_name)
            use_field = field_name != original_name or bool(description)
            alias = original_name if use_field else None
            columns.append(
                ColumnSpec(
                    original_name=original_name,
                    python_type=column["python_type"],
                    semantic_name=semantic_name,
                    description=description,
                    field_name=field_name,
                    alias=alias,
                    use_field=use_field,
                )
            )
        normalized.append(TableSpec(table_name=table["table_name"], columns=columns))
    return normalized


def render_models(
    tables: Iterable[dict[str, Any]],
    template_dir: Path | None = None,
    template_name: str = "models.py.j2",
) -> str:
    root_dir = Path(__file__).resolve().parents[3]
    template_dir = template_dir or root_dir / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    return template.render(tables=_normalize_tables(tables), to_pascal=to_pascal)
