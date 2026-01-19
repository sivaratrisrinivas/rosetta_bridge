from __future__ import annotations

from typing import Any

import pytest

from rosetta_bridge.analyzer.sampler import detect_pii, fetch_sample_rows


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["alice@example.com"], True),
        (["+1 (415) 555-2671"], True),
        (["415-555-2671"], True),
        (["123-45-6789"], True),
        (["not pii", "still ok"], False),
        ([""], False),
        ([None], False),
        ([], False),
    ],
)
def test_detect_pii(values: list[Any], expected: bool) -> None:
    assert detect_pii(values) is expected


def test_fetch_sample_rows_uses_limit_and_returns_dicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class DummyResult:
        def mappings(self):
            return [
                {"id": 1, "email": "alice@example.com"},
                {"id": 2, "email": "bob@example.com"},
            ]

    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement, params):
            captured["statement"] = str(statement)
            captured["params"] = params
            return DummyResult()

    class DummyEngine:
        def connect(self):
            return DummyConnection()

    rows = fetch_sample_rows(DummyEngine(), "users", limit=2)

    assert rows == [
        {"id": 1, "email": "alice@example.com"},
        {"id": 2, "email": "bob@example.com"},
    ]
    assert "LIMIT :limit" in captured["statement"]
    assert captured["params"]["limit"] == 2
