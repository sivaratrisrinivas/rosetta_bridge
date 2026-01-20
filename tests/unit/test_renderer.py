from __future__ import annotations

from rosetta_bridge.codegen.renderer import render_models


def test_render_models_outputs_python_code(tmp_path) -> None:
    tables = [
        {
            "table_name": "user_accounts",
            "columns": [
                {
                    "original_name": "id",
                    "python_type": "int",
                    "description": "Primary key",
                },
                {
                    "original_name": "email",
                    "python_type": "str",
                    "semantic_name": "email_address",
                },
            ],
        }
    ]

    output = render_models(tables)

    assert "class UserAccounts" in output
    assert "id: int" in output
    assert "email_address: str" in output


def test_render_models_sanitizes_schema_names() -> None:
    tables = [
        {
            "table_name": "public.users",
            "columns": [
                {
                    "original_name": "id",
                    "python_type": "int",
                }
            ],
        }
    ]

    output = render_models(tables)

    assert "class PublicUsers" in output
