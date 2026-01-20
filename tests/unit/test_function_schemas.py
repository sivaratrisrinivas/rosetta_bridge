from __future__ import annotations

from rosetta_bridge.codegen.functions import render_function_schemas


def test_render_function_schemas_includes_columns() -> None:
    tables = [
        {
            "table_name": "public.users",
            "columns": [
                {"original_name": "id", "python_type": "int"},
                {"original_name": "status", "python_type": "str"},
            ],
        }
    ]

    schemas = render_function_schemas(tables)

    assert schemas[0]["name"] == "get_users"
    assert "id" in schemas[0]["parameters"]["properties"]
    assert schemas[0]["parameters"]["properties"]["id"]["type"] == "integer"
