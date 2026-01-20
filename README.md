# Rosetta Bridge 🌉

## What
CLI + Web UI that turns a Supabase/Postgres schema into read-only Python models, read-only repos, and an audit log.

## Status
Core objective complete. Gemini-powered semantic inference applied to outputs. Web UI available.

## How it works

At a high level, Rosetta Bridge does three things:

1. **Reflect**  
   - Connects to your database via SQLAlchemy using `DATABASE_URL` or `rosetta_map.yaml.database.connection_string`.  
   - Inspects only the `whitelist_tables` you specify.  
   - Optionally pulls a few sample rows per table and runs simple heuristics for **Enums** (low-cardinality columns) and **PII** (email/phone/ID-like values).

2. **Reason (Gemini)**  
   - Builds a JSON payload per table that includes: table name, column names/types, comments, enum candidates, and **scrubbed** samples (if `privacy.scrub_pii` is true, raw PII values are *not* sent).  
   - Sends that payload to Gemini with a system prompt that asks for:  
     - a better, semantic field name, and  
     - a short business-level description.  
   - Merges Gemini’s response back into an internal `ColumnSpec`/`TableSpec` structure.

3. **Generate**  
   - Renders `templates/models.py.j2` into `_models.py` (Pydantic models with `Field` aliases + descriptions when needed).  
   - Renders `templates/repos.py.j2` into `_repos.py` (read-only repositories – no `UPDATE`, `DELETE`, `DROP`, or `commit()` calls).  
   - Writes `audit_log.md` summarizing inferred meanings per column (original name vs semantic name).  
   - Emits `functions.json` with JSON schemas suitable for tool-calling / function-calling in agent frameworks.

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

## Use (CLI)
```
uv run rosetta-bridge init
uv run rosetta-bridge inspect --config rosetta_map.yaml
uv run rosetta-bridge generate --config rosetta_map.yaml --output-dir generated --format
```

## Use (Web UI)
```
uv run rosetta-bridge serve
```
Then open http://127.0.0.1:8000 in your browser.

![Web UI](https://via.placeholder.com/800x400?text=Rosetta+Bridge+Web+UI)

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