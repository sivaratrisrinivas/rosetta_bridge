from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader

from rosetta_bridge.codegen.renderer import TableSpec, to_pascal


def _normalize_tables(tables: Iterable[dict[str, Any]]) -> list[TableSpec]:
    normalized = []
    for table in tables:
        columns = table.get("columns", [])
        normalized.append(
            TableSpec(
                table_name=table["table_name"],
                columns=columns,
            )
        )
    return normalized


def render_repositories(
    tables: Iterable[dict[str, Any]],
    template_dir: Path | None = None,
    template_name: str = "repos.py.j2",
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
