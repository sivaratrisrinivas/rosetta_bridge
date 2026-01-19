from __future__ import annotations

from pathlib import Path
import subprocess


def write_python_file(
    target_path: Path,
    content: str,
    format_with_ruff: bool = False,
) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content)

    if format_with_ruff:
        subprocess.run(
            ["uv", "run", "ruff", "format", str(target_path)],
            check=False,
        )

    return target_path
