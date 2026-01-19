from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from rosetta_bridge.main import app


def test_generate_command_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "rosetta_map.yaml"
    output_dir = tmp_path / "generated"
    config_path.write_text(
        "\n".join(
            [
                "project_name: demo",
                "database:",
                "  connection_string: postgresql://example/db",
                "whitelist_tables:",
                "  - public.users",
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

    class DummyGemini:
        def __init__(self, model_name):
            self.model_name = model_name

        def generate_description(self, prompt):
            return "ok"

    monkeypatch.setattr("rosetta_bridge.main.get_engine", fake_get_engine)
    monkeypatch.setattr("rosetta_bridge.main.inspect_schema", fake_inspect_schema)
    monkeypatch.setattr("rosetta_bridge.main.fetch_sample_rows", fake_fetch_sample_rows)
    monkeypatch.setattr("rosetta_bridge.main.detect_pii", fake_detect_pii)
    monkeypatch.setattr("rosetta_bridge.main.detect_enum_values", fake_detect_enum_values)
    monkeypatch.setattr("rosetta_bridge.main.GeminiClient", DummyGemini)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["generate", "--config", str(config_path), "--output-dir", str(output_dir)],
    )

    assert result.exit_code == 0
    assert (output_dir / "_models.py").exists()
    assert (output_dir / "_repos.py").exists()
    assert (output_dir / "audit_log.md").exists()

    repos_text = (output_dir / "_repos.py").read_text()
    assert "commit()" not in repos_text
    assert "UPDATE" not in repos_text
