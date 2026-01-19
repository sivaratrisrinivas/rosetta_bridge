from __future__ import annotations

from rosetta_bridge.codegen.repos import render_repositories


def test_render_repositories_is_read_only() -> None:
    tables = [{"table_name": "users", "columns": []}]
    output = render_repositories(tables)

    assert "SELECT" in output
    assert "commit()" not in output
    assert "UPDATE" not in output
    assert "DELETE" not in output
