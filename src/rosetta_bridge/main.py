from pathlib import Path

import typer

from rosetta_bridge import __version__
from rosetta_bridge.core.config import write_default_rosetta_map

app = typer.Typer(add_completion=False)


@app.callback()
def _root() -> None:
    """Root command group."""


@app.command()
def version() -> None:
    typer.echo(f"rosetta-bridge {__version__}")


@app.command()
def init(
    config: Path = typer.Option(
        "rosetta_map.yaml",
        "--config",
        "-c",
        help="Path to write the default rosetta_map.yaml",
    ),
) -> None:
    if config.exists():
        raise typer.BadParameter(f"{config} already exists")
    write_default_rosetta_map(config)
    typer.echo(f"Wrote {config}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
