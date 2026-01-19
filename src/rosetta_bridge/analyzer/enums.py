from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


_ENUM_TYPES = {
    "string",
    "str",
    "varchar",
    "text",
    "char",
    "character",
    "character varying",
    "int",
    "integer",
    "bigint",
    "smallint",
}


def detect_enum_values(
    engine: Engine,
    table_name: str,
    column_name: str,
    column_type: str,
    max_values: int = 20,
) -> list[Any] | None:
    normalized_type = column_type.strip().lower()
    if normalized_type not in _ENUM_TYPES:
        return None

    count_stmt = text(
        f'SELECT COUNT(DISTINCT "{column_name}") AS value_count FROM "{table_name}"'
    )
    values_stmt = text(
        f'SELECT DISTINCT "{column_name}" FROM "{table_name}" ORDER BY "{column_name}"'
    )

    with engine.connect() as connection:
        value_count = connection.execute(count_stmt, {}).scalar_one()
        if value_count >= max_values:
            return None
        values = connection.execute(values_stmt, {}).scalars().all()
        return list(values)
