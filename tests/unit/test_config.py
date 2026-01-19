import os
from pathlib import Path

import yaml
from typer.testing import CliRunner

from rosetta_bridge.core.config import load_rosetta_map
from rosetta_bridge.main import app


def test_load_rosetta_map_expands_env_and_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "rosetta_map.yaml"
    config_path.write_text(
        "\n".join(
            [
                "project_name: demo",
                "database:",
                "  connection_string: ${DATABASE_URL}",
                "whitelist_tables:",
                "  - users",
            ]
        )
    )

    os.environ["DATABASE_URL"] = "postgresql://example/db"
    config = load_rosetta_map(config_path)

    assert config.database.connection_string == "postgresql://example/db"
    assert config.llm_config.model == "gemini-1.5-flash"
    assert config.llm_config.temperature == 0.0
    assert config.privacy.sample_rows is False
    assert config.privacy.scrub_pii is True


def test_init_command_writes_default_config(tmp_path: Path) -> None:
    config_path = tmp_path / "rosetta_map.yaml"
    runner = CliRunner()

    result = runner.invoke(app, ["init", "--config", str(config_path)])

    assert result.exit_code == 0
    assert config_path.exists()

    data = yaml.safe_load(config_path.read_text())
    assert data["project_name"] == "rosetta-bridge"
    assert data["database"]["connection_string"] == "${DATABASE_URL}"
    assert data["whitelist_tables"] == []
    assert data["llm_config"]["model"] == "gemini-1.5-flash"
    assert data["llm_config"]["temperature"] == 0.0
    assert data["privacy"]["sample_rows"] is False
    assert data["privacy"]["scrub_pii"] is True
