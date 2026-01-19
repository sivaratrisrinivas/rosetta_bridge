from __future__ import annotations

from rosetta_bridge.analyzer.enums import detect_enum_values


def test_detect_enum_values_returns_none_for_non_textual_column() -> None:
    assert detect_enum_values(engine=None, table_name="t", column_name="c", column_type="jsonb") is None


def test_detect_enum_values_returns_values_for_low_cardinality() -> None:
    calls = []

    class DummyResult:
        def __init__(self, rows):
            self._rows = rows

        def scalar_one(self):
            return self._rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement, params):
            calls.append((str(statement), params))
            if "COUNT" in str(statement):
                return DummyResult(3)
            return DummyResult(["new", "active", "closed"])

    class DummyEngine:
        def connect(self):
            return DummyConnection()

    values = detect_enum_values(
        engine=DummyEngine(),
        table_name="accounts",
        column_name="status",
        column_type="varchar",
        max_values=20,
    )

    assert values == ["new", "active", "closed"]
    assert any("COUNT" in stmt for stmt, _ in calls)


def test_detect_enum_values_returns_none_for_high_cardinality() -> None:
    class DummyResult:
        def scalar_one(self):
            return 50

    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement, params):
            return DummyResult()

    class DummyEngine:
        def connect(self):
            return DummyConnection()

    values = detect_enum_values(
        engine=DummyEngine(),
        table_name="accounts",
        column_name="status",
        column_type="text",
        max_values=20,
    )

    assert values is None
