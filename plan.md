# Implementation Plan: Rosetta Bridge (Supabase + Gemini + uv)

## Phase 1: Foundation & Connectivity
- [x] **Step 1: Project Scaffolding (uv)**
  - Initialize project using `uv init --app --name rosetta_bridge`.
  - Add runtime dependencies: `sqlalchemy`, `psycopg2-binary`, `pydantic`, `pydantic-settings`, `google-generativeai`, `typer`, `jinja2`, `python-dotenv`, `rich`.
  - Add dev dependencies: `pytest`.
  - Configure `pyproject.toml` with `[project.scripts]` and `[tool.uv] package = true`.
  - Create directory structure (`src/rosetta_bridge/...`, `templates/`, `tests/`).
  - Create `.env.example` with `DATABASE_URL` and `GEMINI_API_KEY`.
  - *Verification:* Run `uv sync` and `uv run rosetta-bridge version`.

- [x] **Step 2: Configuration Loader**
  - Create `src/rosetta_bridge/core/config.py`.
  - Implement Pydantic `Settings` model to load env vars and `rosetta_map.yaml`.
  - Update `src/rosetta_bridge/main.py` to add an `init` command that generates a default `rosetta_map.yaml` file.
  - *Verification:* Run `uv run rosetta-bridge init` and verify `rosetta_map.yaml` is created with correct defaults.

- [ ] **Step 3: Database Inspector (Supabase/Postgres)**
  - Create `src/rosetta_bridge/inspector/db.py`.
  - Implement `get_engine()` using SQLAlchemy.
  - Implement `inspect_schema(table_name)` to pull columns using SQLAlchemy reflection or `information_schema`.
  - *Verification:* Create a script `tests/debug_db.py` that connects to Supabase and prints the schema of a real table.

## Phase 2: Analysis & Heuristics
- [ ] **Step 4: Sampling & PII Detection**
  - Create `src/rosetta_bridge/analyzer/sampler.py`.
  - Implement `fetch_sample_rows` (Query Supabase with `LIMIT 3`).
  - Implement `detect_pii` using regex (email, phone, ssn patterns).
  - *Verification:* Create a unit test `tests/unit/test_sampler.py` with mock data to verify PII flagging works.

- [ ] **Step 5: Enum Detection Logic**
  - Create `src/rosetta_bridge/analyzer/enums.py`.
  - Logic: Check if column is String/Int -> Run `SELECT DISTINCT` -> If count < 20, return values.
  - *Verification:* Run against a specific "Status" or "Type" column in your Supabase DB.

## Phase 3: The Intelligence Layer (Gemini)
- [ ] **Step 6: Gemini Client Wrapper**
  - Create `src/rosetta_bridge/inference/client.py`.
  - Initialize `genai.GenerativeModel('gemini-1.5-flash')`.
  - Implement `generate_description(table_context)`.
  - *Verification:* Create `tests/debug_gemini.py` to send a "Hello World" prompt to Gemini and print the response.

- [ ] **Step 7: Prompt Engineering**
  - Create `src/rosetta_bridge/inference/prompts.py`.
  - Construct the System Prompt ("You are a Data Architect...") and User Prompt (Inject schema + samples).
  - Ensure logic exists to *exclude* PII sample values from the prompt payload.
  - *Verification:* Print the generated prompt string to console and visually confirm PII is scrubbed.

## Phase 4: Code Generation
- [ ] **Step 8: Jinja Template - Models**
  - Create `templates/models.py.j2`.
  - Create `src/rosetta_bridge/codegen/renderer.py` to render Pydantic models.
  - *Verification:* Pass a dummy dictionary of enriched columns to the renderer and check if valid Python code is printed.

- [ ] **Step 9: Jinja Template - Repositories (Safety)**
  - Create `templates/repos.py.j2`.
  - Write template for `Repository` classes containing ONLY `select` statements (Safety by Design).
  - *Verification:* Render the template and verify the string "commit()" or "update" does NOT exist in the output.

- [ ] **Step 10: File Writer & Formatting**
  - Create `src/rosetta_bridge/codegen/writer.py`.
  - Implement logic to write strings to `.py` files.
  - (Optional) Use `subprocess` to run `uv run ruff format` on the generated files.
  - *Verification:* Generate valid `.py` files in a `generated/` folder.

## Phase 5: Interface & Audit
- [ ] **Step 11: Audit Log Generation**
  - Create `src/rosetta_bridge/codegen/audit.py`.
  - Generate a simple Markdown table: `| Table | Original Column | Inferred Meaning |`.
  - *Verification:* Generate the log and check file content.

- [ ] **Step 12: CLI 'Inspect' Command**
  - Wire up `rosetta-bridge inspect` in `main.py`.
  - Should run Phase 1 & 2 (Connectivity + Analysis) and print a summary table to the console.
  - *Verification:* Run `uv run rosetta-bridge inspect --config rosetta_map.yaml` against Supabase.

- [ ] **Step 13: CLI 'Generate' Command**
  - Wire up `rosetta-bridge generate` in `main.py`.
  - Wire up full pipeline: Inspect -> Analyze -> Infer -> Generate -> Audit.
  - *Verification:* End-to-end run producing usable code.

- [ ] **Step 14: Safety Integration Test**
  - Create a test that attempts to call a generated repository method.
  - *Verification:* Ensure it fetches data correctly but fails if you try to inject an UPDATE (proving ReadOnly safety).