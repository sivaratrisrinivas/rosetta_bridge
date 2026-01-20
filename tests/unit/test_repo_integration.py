from __future__ import annotations

import types

from sqlalchemy import create_engine, text

from rosetta_bridge.codegen.repos import render_repositories


def test_generated_repository_fetches_data_and_is_read_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
        connection.execute(text("INSERT INTO users (name) VALUES ('Ada')"))

    code = render_repositories(
        [{"table_name": "users", "columns": [{"original_name": "name"}]}]
    )
    assert "UPDATE" not in code
    assert "DELETE" not in code
    assert "commit()" not in code

    module = types.ModuleType("generated_repos")
    exec(code, module.__dict__)

    repo = module.UsersRepository(engine)
    rows = repo.fetch_all()

    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["name"] == "Ada"

    malicious = "'; DROP TABLE users; --"
    assert repo.fetch_by(name=malicious) == []
    assert repo.fetch_all()[0]["name"] == "Ada"
