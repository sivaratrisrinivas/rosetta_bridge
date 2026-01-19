# Rosetta Bridge 🌉

## What
Turn a Supabase/Postgres database into clean, safe Python code: data models, read-only queries, and an audit log.

## Why
Legacy schemas are hard to understand and easy to misuse. This tool:
- gives human-friendly meanings to tables/columns
- prevents write operations by design
- leaves a clear audit trail of what was inferred

## How
1. Read the schema
2. Sample small rows and scrub sensitive data
3. Ask Gemini for plain-English meaning
4. Generate Python models + read-only repos + audit log

## Setup
```
uv sync
cp .env.example .env
```

Set in `.env`:
- `DATABASE_URL` (Supabase/Postgres connection string)
- `GEMINI_API_KEY`

## Use
```
uv run rosetta-bridge init
uv run rosetta-bridge inspect
uv run rosetta-bridge generate
```

## Config
`rosetta_map.yaml` controls tables, model, and privacy rules.

## Output
```
generated/
  _models.py
  _repos.py
  audit_log.md
```

## Notes
- Connection string is a SQLAlchemy URL in `DATABASE_URL`.
- `detect_pii` flags emails/phones/SSNs and is used to scrub samples.
- Low-cardinality columns (e.g., status) are treated as enums.