import pytest

from rosetta_bridge.inspector import db as db_inspector


def test_get_engine_uses_explicit_connection_string(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_create_engine(connection_string: str):
        captured["connection_string"] = connection_string
        return "engine"

    monkeypatch.setattr(db_inspector, "create_engine", fake_create_engine)

    engine = db_inspector.get_engine("postgresql://example/db")

    assert engine == "engine"
    assert captured["connection_string"] == "postgresql://example/db"


def test_get_engine_errors_when_missing_connection_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        db_inspector.get_engine(settings=db_inspector.Settings(_env_file=None))


def test_inspect_schema_returns_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyInspector:
        def get_columns(self, table_name: str, schema: str | None = None):
            assert table_name == "users"
            assert schema is None
            return [{"name": "id", "type": "INTEGER"}]

    def fake_inspect(engine: object):
        assert engine == "engine"
        return DummyInspector()

    monkeypatch.setattr(db_inspector, "inspect", fake_inspect)

    columns = db_inspector.inspect_schema("users", engine="engine")

    assert columns == [{"name": "id", "type": "INTEGER"}]


def test_inspect_schema_handles_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyInspector:
        def get_columns(self, table_name: str, schema: str | None = None):
            assert table_name == "users"
            assert schema == "public"
            return [{"name": "id", "type": "INTEGER"}]

    def fake_inspect(engine: object):
        return DummyInspector()

    monkeypatch.setattr(db_inspector, "inspect", fake_inspect)

    columns = db_inspector.inspect_schema("public.users", engine="engine")

    assert columns == [{"name": "id", "type": "INTEGER"}]
