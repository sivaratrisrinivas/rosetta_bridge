"""FastAPI web server for Rosetta Bridge UI."""

from __future__ import annotations

import json
from pathlib import Path
import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rosetta_bridge.analyzer.enums import detect_enum_values
from rosetta_bridge.analyzer.sampler import detect_pii, fetch_sample_rows
from rosetta_bridge.codegen.audit import render_audit_log
from rosetta_bridge.codegen.functions import render_function_schemas
from rosetta_bridge.codegen.renderer import render_models
from rosetta_bridge.codegen.repos import render_repositories
from rosetta_bridge.core.config import (
    DatabaseConfig,
    LLMConfig,
    PrivacyConfig,
    RosettaMap,
)
from rosetta_bridge.inference.client import GeminiClient
from rosetta_bridge.inference.prompts import (
    build_user_prompt,
    get_system_prompt,
    parse_gemini_response,
)
from rosetta_bridge.inspector.db import get_engine, get_table_comment, inspect_schema

app = FastAPI(
    title="Rosetta Bridge",
    description="Legacy-to-Agent Semantic Mapper",
    version="1.0.0",
)

logger = logging.getLogger("rosetta_bridge.web")
_DEMO_TABLE_LIMIT = 12
_DEMO_BLOCKLIST_TOKENS = {
    "tmp",
    "temp",
    "backup",
    "archive",
    "staging",
    "migrate",
    "migration",
    "schema_migrations",
    "seed",
    "test",
    "dev",
    "internal",
    "system",
}


def _is_demo_table(schema: str, table: str) -> bool:
    if schema != "public":
        return False
    lowered = table.lower()
    if lowered.startswith(("pg_", "sql_")):
        return False
    if any(token in lowered for token in _DEMO_BLOCKLIST_TOKENS):
        return False
    return True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionRequest(BaseModel):
    database_url: str


class GenerateRequest(BaseModel):
    database_url: str
    gemini_api_key: str
    tables: list[str]
    model: str = "gemini-3-flash-preview"
    sample_rows: bool = True
    scrub_pii: bool = True


class TableInfo(BaseModel):
    name: str
    column_count: int
    enum_count: int
    pii_count: int


def _map_python_type(type_name: str) -> str:
    normalized = type_name.strip().lower()
    if any(token in normalized for token in ["int", "bigint", "smallint"]):
        return "int"
    if any(token in normalized for token in ["bool"]):
        return "bool"
    if any(token in normalized for token in ["numeric", "decimal", "real", "float", "double"]):
        return "float"
    return "str"


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI."""
    static_dir = Path(__file__).parent / "static"
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return HTMLResponse(content=index_path.read_text())


@app.post("/api/connect")
async def connect(request: ConnectionRequest) -> JSONResponse:
    """Test database connection and list tables."""
    try:
        engine = get_engine(request.database_url)
        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(engine)
        schemas = inspector.get_schema_names()
        candidates: list[tuple[str, int]] = []
        for schema in schemas:
            if schema in ("information_schema", "pg_catalog", "pg_toast"):
                continue
            for table in inspector.get_table_names(schema=schema):
                if not _is_demo_table(schema, table):
                    continue
                columns = inspector.get_columns(table, schema=schema)
                if len(columns) < 3:
                    continue
                candidates.append((f"{schema}.{table}", len(columns)))

        candidates.sort(key=lambda item: (-item[1], item[0]))
        demo_tables = [name for name, _ in candidates[:_DEMO_TABLE_LIMIT]]
        return JSONResponse({"success": True, "tables": demo_tables})
    except Exception as e:
        logger.exception("connect failed: %s", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/inspect")
async def inspect_tables(request: ConnectionRequest, tables: list[str]) -> JSONResponse:
    """Inspect selected tables."""
    try:
        engine = get_engine(request.database_url)
        results: list[TableInfo] = []

        for table in tables:
            columns = inspect_schema(table, engine)
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

            results.append(
                TableInfo(
                    name=table,
                    column_count=len(columns),
                    enum_count=enum_count,
                    pii_count=pii_count,
                )
            )

        return JSONResponse({"success": True, "tables": [r.model_dump() for r in results]})
    except Exception as e:
        logger.exception("inspect failed: %s", str(e))
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/generate")
async def generate(request: GenerateRequest) -> JSONResponse:
    """Generate models, repos, audit log, and function schemas."""
    try:
        engine = get_engine(request.database_url)

        # Build config
        rosetta_map = RosettaMap(
            project_name="rosetta-bridge",
            database=DatabaseConfig(connection_string=request.database_url),
            whitelist_tables=request.tables,
            llm_config=LLMConfig(model=request.model),
            privacy=PrivacyConfig(sample_rows=request.sample_rows, scrub_pii=request.scrub_pii),
        )

        # Initialize Gemini client
        import os

        os.environ["GEMINI_API_KEY"] = request.gemini_api_key
        gemini = GeminiClient(model_name=rosetta_map.llm_config.model)
        system_prompt = get_system_prompt()

        rendered_tables: list[dict[str, Any]] = []
        audit_rows: list[tuple[str, str, str]] = []
        failed_tables: list[dict[str, str]] = []

        for table in request.tables:
            try:
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
                enriched_columns: list[dict[str, Any]] = []
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
            except Exception as e:
                logger.exception("generate failed for table=%s: %s", table, str(e))
                failed_tables.append({"table": table, "error": str(e)})

        if not rendered_tables:
            return JSONResponse(
                {
                    "success": False,
                    "error": "No tables could be processed.",
                    "failed_tables": failed_tables,
                },
                status_code=400,
            )

        models_code = render_models(rendered_tables)
        repos_code = render_repositories(rendered_tables)
        audit_log = render_audit_log(audit_rows)
        if failed_tables:
            audit_log += "\n\n## Skipped tables\n"
            for failure in failed_tables:
                table = failure.get("table", "unknown")
                error = failure.get("error", "unknown error")
                audit_log += f"- {table}: {error}\n"
        function_schemas = render_function_schemas(rendered_tables)

        return JSONResponse(
            {
                "success": True,
                "outputs": {
                    "models": models_code,
                    "repos": repos_code,
                    "audit_log": audit_log,
                    "functions": json.dumps(function_schemas, indent=2),
                },
                "failed_tables": failed_tables,
            }
        )
    except Exception as e:
        import traceback
        logger.exception("generate failed: %s", str(e))
        return JSONResponse(
            {"success": False, "error": str(e), "traceback": traceback.format_exc()},
            status_code=400,
        )


# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
