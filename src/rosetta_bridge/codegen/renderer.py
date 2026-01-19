from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader


@dataclass(frozen=True)
class ColumnSpec:
    original_name: str
    python_type: str
    semantic_name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class TableSpec:
    table_name: str
    columns: list[ColumnSpec]


def to_pascal(value: str) -> str:
    parts = [p for p in value.replace("-", "_").split("_") if p]
    return "".join(part.capitalize() for part in parts) or "Model"


def _normalize_tables(tables: Iterable[dict[str, Any]]) -> list[TableSpec]:
    normalized = []
    for table in tables:
        columns = [
            ColumnSpec(
                original_name=column["original_name"],
                python_type=column["python_type"],
                semantic_name=column.get("semantic_name"),
                description=column.get("description"),
            )
            for column in table["columns"]
        ]
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
