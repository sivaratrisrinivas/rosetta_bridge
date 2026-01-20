from pathlib import Path
import json

import typer

from rosetta_bridge import __version__
from rosetta_bridge.analyzer.enums import detect_enum_values
from rosetta_bridge.analyzer.sampler import detect_pii, fetch_sample_rows
from rosetta_bridge.codegen.audit import render_audit_log
from rosetta_bridge.codegen.functions import render_function_schemas
from rosetta_bridge.codegen.renderer import render_models
from rosetta_bridge.codegen.repos import render_repositories
from rosetta_bridge.codegen.writer import write_python_file
from rosetta_bridge.core.config import load_rosetta_map, write_default_rosetta_map
from rosetta_bridge.inference.client import GeminiClient
from rosetta_bridge.inference.prompts import (
    build_user_prompt,
    get_system_prompt,
    parse_gemini_response,
)
from rosetta_bridge.inspector.db import get_engine, get_table_comment, inspect_schema

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


def _map_python_type(type_name: str) -> str:
    normalized = type_name.strip().lower()
    if any(token in normalized for token in ["int", "bigint", "smallint"]):
        return "int"
    if any(token in normalized for token in ["bool"]):
        return "bool"
    if any(token in normalized for token in ["numeric", "decimal", "real", "float", "double"]):
        return "float"
    return "str"


@app.command()
def generate(
    config: Path = typer.Option(
        "rosetta_map.yaml",
        "--config",
        "-c",
        help="Path to rosetta_map.yaml",
    ),
    output_dir: Path = typer.Option(
        "generated",
        "--output-dir",
        "-o",
        help="Directory to write generated files",
    ),
    format_with_ruff: bool = typer.Option(
        False,
        "--format",
        help="Format generated files with ruff",
    ),
) -> None:
    rosetta_map = load_rosetta_map(config)
    engine = get_engine(rosetta_map.database.connection_string)
    tables = rosetta_map.whitelist_tables
    if not tables:
        typer.echo("No tables in whitelist.")
        return

    gemini = GeminiClient(model_name=rosetta_map.llm_config.model)
    system_prompt = get_system_prompt()

    rendered_tables = []
    audit_rows: list[tuple[str, str, str]] = []

    for table in tables:
        columns = inspect_schema(table, engine)
        table_comment = get_table_comment(table, engine)
        sample_rows = []
        if rosetta_map.privacy.sample_rows:
            sample_rows = fetch_sample_rows(engine, table, limit=3)

        samples_by_column: dict[str, list[object]] = {}
        for row in sample_rows:
            for name, value in row.items():
                samples_by_column.setdefault(name, []).append(value)

        prompt_columns = []
        enriched_columns = []
        for column in columns:
            name = column.get("name")
            if not name:
                continue
            column_type = str(column.get("type", ""))
            samples = samples_by_column.get(name, [])
            scrub_pii = rosetta_map.privacy.scrub_pii and detect_pii(samples)
            prompt_columns.append(
                {
                    "name": name,
                    "type": column_type,
                    "comment": column.get("comment"),
                    "samples": [] if scrub_pii else samples,
                }
            )
            python_type = _map_python_type(column_type)
            semantic_name = name
            enum_values = detect_enum_values(engine, table, name, column_type)
            description = None
            if enum_values:
                description = f"Allowed values: {', '.join(map(str, enum_values))}"

            enriched_columns.append(
                {
                    "original_name": name,
                    "python_type": python_type,
                    "semantic_name": semantic_name,
                    "description": description,
                }
            )

        user_prompt = build_user_prompt(
            table,
            prompt_columns,
            scrub_pii=rosetta_map.privacy.scrub_pii,
            table_comment=table_comment,
        )
        gemini_response = gemini.generate_description(f"{system_prompt}\n\n{user_prompt}")
        inferred = parse_gemini_response(gemini_response)

        for column in enriched_columns:
            name = column["original_name"]
            inference = inferred.get(name, {})
            semantic_name = inference.get("semantic_name") or name
            description = inference.get("description") or column.get("description")
            if column.get("description") and inference.get("description"):
                description = f"{inference.get('description')} {column.get('description')}"
            column["semantic_name"] = semantic_name
            column["description"] = description

            audit_value = semantic_name
            if semantic_name != name:
                audit_value = f"{semantic_name} (Inferred)"
            audit_rows.append((table, name, audit_value))

        rendered_tables.append(
            {
                "table_name": table,
                "columns": enriched_columns,
            }
        )

    models_code = render_models(rendered_tables)
    repos_code = render_repositories(rendered_tables)
    write_python_file(output_dir / "_models.py", models_code, format_with_ruff)
    write_python_file(output_dir / "_repos.py", repos_code, format_with_ruff)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "audit_log.md").write_text(render_audit_log(audit_rows))
    (output_dir / "functions.json").write_text(
        json.dumps(render_function_schemas(rendered_tables), indent=2)
    )

    typer.echo(f"Wrote {output_dir}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
) -> None:
    """Start the web UI server."""
    try:
        import uvicorn
    except ImportError:
        typer.echo("Error: uvicorn not installed. Run: uv add uvicorn fastapi")
        raise typer.Exit(1)

    typer.echo(f"Starting Rosetta Bridge UI at http://{host}:{port}")
    uvicorn.run(
        "rosetta_bridge.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
