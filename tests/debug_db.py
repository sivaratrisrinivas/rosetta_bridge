import os
import sys

from rosetta_bridge.inspector.db import get_engine, inspect_schema


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python tests/debug_db.py <table_name>")
        return 1

    table_name = sys.argv[1]
    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL is not set")
        return 1

    engine = get_engine()
    columns = inspect_schema(table_name, engine)
    for column in columns:
        print(f"{column['name']}: {column['type']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
