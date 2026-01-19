from __future__ import annotations

from pathlib import Path

from rosetta_bridge.codegen.writer import write_python_file


def test_write_python_file_writes_content(tmp_path: Path) -> None:
    target = tmp_path / "generated" / "models.py"
    write_python_file(target, "print('ok')\n")

    assert target.exists()
    assert target.read_text() == "print('ok')\n"


def test_write_python_file_runs_ruff_when_enabled(
    tmp_path: Path, monkeypatch
) -> None:
    calls = []

    def fake_run(args, check=False):
        calls.append((args, check))

    monkeypatch.setattr("rosetta_bridge.codegen.writer.subprocess.run", fake_run)

    target = tmp_path / "generated" / "models.py"
    write_python_file(target, "print('ok')\n", format_with_ruff=True)

    assert calls
    assert calls[0][0][:3] == ["uv", "run", "ruff"]
