from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

from rosetta_bridge.core.config import Settings


def get_engine(
    connection_string: str | None = None,
    settings: Settings | None = None,
) -> Engine:
    if connection_string is None:
        settings = settings or Settings()
        connection_string = settings.database_url

    if not connection_string:
        raise ValueError("DATABASE_URL must be set to connect to the database")

    return create_engine(connection_string)


def inspect_schema(table_name: str, engine: Engine) -> list[dict[str, Any]]:
    inspector = inspect(engine)
    if "." in table_name:
        schema, table = table_name.split(".", 1)
        return inspector.get_columns(table, schema=schema)
    return inspector.get_columns(table_name)
