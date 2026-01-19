from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from rosetta_bridge.main import app


def test_inspect_command_reports_summary(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "rosetta_map.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project_name: demo",
                "database:",
                "  connection_string: postgresql://example/db",
                "whitelist_tables:",
                "  - users",
                "privacy:",
                "  sample_rows: true",
                "  scrub_pii: true",
            ]
        )
    )

    def fake_get_engine(connection_string):
        return "engine"

    def fake_inspect_schema(table, engine):
        return [
            {"name": "email", "type": "varchar"},
            {"name": "status", "type": "varchar"},
        ]

    def fake_fetch_sample_rows(engine, table, limit=3):
        return [{"email": "a@example.com", "status": "active"}]

    def fake_detect_pii(values):
        return "@" in str(values[0])

    def fake_detect_enum_values(engine, table, column_name, column_type, max_values=20):
        if column_name == "status":
            return ["active", "closed"]
        return None

    monkeypatch.setattr("rosetta_bridge.main.get_engine", fake_get_engine)
    monkeypatch.setattr("rosetta_bridge.main.inspect_schema", fake_inspect_schema)
    monkeypatch.setattr("rosetta_bridge.main.fetch_sample_rows", fake_fetch_sample_rows)
    monkeypatch.setattr("rosetta_bridge.main.detect_pii", fake_detect_pii)
    monkeypatch.setattr("rosetta_bridge.main.detect_enum_values", fake_detect_enum_values)

    runner = CliRunner()
    result = runner.invoke(app, ["inspect", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Connected to Supabase." in result.output
    assert "Found 1 tables in whitelist." in result.output
    assert "Table users has 2 columns." in result.output
    assert "Detected 1 potential Enums in users." in result.output
    assert "Detected 1 potential PII columns in users." in result.output
