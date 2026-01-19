from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}\b"
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def fetch_sample_rows(
    engine: Engine,
    table_name: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    statement = text(f'SELECT * FROM "{table_name}" LIMIT :limit')
    with engine.connect() as connection:
        result = connection.execute(statement, {"limit": limit})
        return list(result.mappings())


def detect_pii(values: list[Any]) -> bool:
    for value in values:
        if value is None:
            continue
        text_value = str(value)
        if not text_value:
            continue
        if _EMAIL_RE.search(text_value):
            return True
        if _PHONE_RE.search(text_value):
            return True
        if _SSN_RE.search(text_value):
            return True
    return False
