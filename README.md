# Rosetta Bridge 🌉

## What
CLI that turns a Supabase/Postgres schema into read-only Python models, read-only repos, and an audit log.

## Status
End-to-end generate pipeline is wired. Gemini responses are parsed (when JSON) to apply semantic names/descriptions.

## Setup
```
uv sync
cp .env.example .env
```

Set in `.env`:
- `DATABASE_URL` (Supabase/Postgres SQLAlchemy URL)
- `GEMINI_API_KEY`

## Config
`rosetta_map.yaml` controls tables, model, and privacy rules.

```yaml
project_name: rosetta-bridge
database:
  connection_string: ${DATABASE_URL}
whitelist_tables:
  - public.users
llm_config:
  model: gemini-3-flash-preview
  temperature: 0.0
privacy:
  sample_rows: false
  scrub_pii: true
```

## Use
```
uv run rosetta-bridge init
uv run rosetta-bridge inspect --config rosetta_map.yaml
uv run rosetta-bridge generate --config rosetta_map.yaml --output-dir generated --format
```

## Output
```
generated/
  _models.py
  _repos.py
  audit_log.md
  functions.json
```

## Verify Core Objective
```
time uv run rosetta-bridge generate --config rosetta_map.yaml --output-dir generated
rg -n "commit\\(\\)|UPDATE|DELETE|DROP|INSERT" generated/_repos.py
python -m py_compile generated/_models.py generated/_repos.py
rg -n "flg_act_y|c_sts|amt_tot_c|flg_frd" generated/audit_log.md
```

## Prove Gemini Call
```
GEMINI_API_KEY=your_key_here uv run python tests/debug_gemini.py
```

## Tests
```
uv run pytest
```

## Notes
- Connection string supports `${DATABASE_URL}` expansion.
- PII samples are scrubbed when `privacy.scrub_pii` is true.
- Low-cardinality columns are treated as enums for descriptions.