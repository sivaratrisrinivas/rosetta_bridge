from pathlib import Path

import typer

from rosetta_bridge import __version__
from rosetta_bridge.analyzer.enums import detect_enum_values
from rosetta_bridge.analyzer.sampler import detect_pii, fetch_sample_rows
from rosetta_bridge.core.config import load_rosetta_map, write_default_rosetta_map
from rosetta_bridge.inspector.db import get_engine, inspect_schema

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


@app.command()
def inspect(
    config: Path = typer.Option(
        "rosetta_map.yaml",
        "--config",
        "-c",
        help="Path to rosetta_map.yaml",
    ),
) -> None:
    rosetta_map = load_rosetta_map(config)
    engine = get_engine(rosetta_map.database.connection_string)
    typer.echo("Connected to Supabase.")

    tables = rosetta_map.whitelist_tables
    typer.echo(f"Found {len(tables)} tables in whitelist.")

    for table in tables:
        columns = inspect_schema(table, engine)
        typer.echo(f"[!] Table {table} has {len(columns)} columns.")

        sample_rows = []
        if rosetta_map.privacy.sample_rows:
            sample_rows = fetch_sample_rows(engine, table, limit=3)

        samples_by_column: dict[str, list[object]] = {}
        for row in sample_rows:
            for name, value in row.items():
                samples_by_column.setdefault(name, []).append(value)

        enum_count = 0
        pii_count = 0
        for column in columns:
            name = column.get("name")
            column_type = str(column.get("type", "")).lower()
            if name and detect_enum_values(engine, table, name, column_type):
                enum_count += 1
            if name:
                values = samples_by_column.get(name, [])
                if values and detect_pii(values):
                    pii_count += 1

        if enum_count:
            typer.echo(f"[i] Detected {enum_count} potential Enums in {table}.")
        if pii_count:
            typer.echo(f"[i] Detected {pii_count} potential PII columns in {table}.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
