# Technical Specification: Rosetta Bridge

**Version:** 1.0.0
**Status:** Approved for Development
**Author:** System Architect
**Target Platform:** Python 3.10+ (Managed by `uv`)

---

## 1. Executive Summary

**Rosetta Bridge** is a CLI-based build tool designed to bridge the "Execution Gap" between cryptic legacy SQL schemas (specifically Supabase/PostgreSQL) and modern AI Agents. It automates schema inspection, applies safety heuristics, and invokes Gemini for semantic enrichment. It generates type-safe Python code (Pydantic models), function schemas for tool calling, and "Safe-by-Design" read-only repositories that Agents can use immediately.

### 1.1 Core Objectives
1.  **Accelerate Time-to-Value:** Reduce the "schema onboarding" phase from weeks to minutes by automating the mapping of tables to business logic.
2.  **Enforce Safety (ReadOnly):** Generate database access layers that are physically incapable of executing `UPDATE`, `DELETE`, or `DROP` commands.
3.  **Auditability:** Produce human-readable audit logs (`audit_log.md`) documenting every AI inference to ensure compliance.

---

## 2. Technical Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Standard for AI/Data engineering. |
| **Package Manager** | `uv` | Fast, modern dependency and environment management. |
| **Database Reflection** | `SQLAlchemy` + `psycopg2` | Robust introspection for Supabase (PostgreSQL). |
| **Data Validation** | `Pydantic v2` | High-performance serialization/validation. |
| **LLM Orchestration** | `google-genai` (Gemini API) | Uses `gemini-3-flash-preview` for fast semantic prompts. |
| **Code Generation** | `Jinja2` | Templating engine to produce clean Python code. |
| **CLI Framework** | `Typer` + `Rich` | Type-safe CLI builder with excellent UX/formatting. |
| **Testing** | `Pytest` | Standard unit testing framework. |

---

## 3. System Architecture

The system operates as a **unidirectional build pipeline** exposed via a CLI, with an optional lightweight Web UI served by FastAPI/Starlette for interactive runs. The web server is intended for local/operator use rather than as a long-lived multi-tenant service.

### 3.1 High-Level Data Flow

1.  **Ingestion:** Connect to Supabase/Postgres (or any SQLAlchemy-compatible DB) $\rightarrow$ Reflect Schema Metadata (Tables, Columns, Types, Comments).
2.  **Analysis:** Detect candidates for Enums (low cardinality) & flag PII (Regex heuristics).
3.  **Inference:** Send sanitized metadata to Gemini $\rightarrow$ Receive semantic descriptions (JSON).
4.  **Generation:** Hydrate Jinja2 templates $\rightarrow$ Write `.py` artifacts & Audit Log.

### 3.2 Output Artifacts

The tool generates a "Repository Pattern" structure in a `generated/` directory:

* **`_models.py`:** Pydantic models representing the tables (Locked file).
* **`_repos.py`:** Read-Only SQL access methods with safe filters (Locked file, no mutations/`commit()`).
* **`audit_log.md`:** A report of what was mapped and why.
* **`functions.json`:** OpenAI-style function schemas.

---

## 4. Data Models (Internal Schema)

These models define the internal state of the application during the build process.

### 4.1 Configuration (`rosetta_map.yaml`)

```yaml
project_name: str
database:
  connection_string: str  # SQLAlchemy URL, can reference ${DATABASE_URL}
whitelist_tables: List[str] # Mandatory list of tables to process
llm_config:
  model: "gemini-3-flash-preview"
  temperature: 0.0
privacy:
  sample_rows: bool      # If True, sends 3 rows of data to Gemini for context
  scrub_pii: bool        # If True, suppresses columns looking like SSN/Email

```

### 4.2 Render Payloads

**`ColumnSpec`**

* `original_name`: str (e.g., `status`)
* `python_type`: str (e.g., `str`, `int`)
* `semantic_name`: str | None (Gemini-inferred when available)
* `description`: str | None (Gemini description and enum hints)
* `field_name`: str (sanitized Python identifier)
* `alias`: str | None (original column name for Field alias)

**`TableSpec`**

* `table_name`: str
* `columns`: List[ColumnSpec]

---

## 5. Interface Definitions (CLI)

### 5.1 Command: `init`

Initializes the project structure.

* **Input:** None.
* **Output:** Generates default `rosetta_map.yaml` and `.env` template.

### 5.2 Command: `inspect`

Runs a "Dry Run" to verify connectivity and schema readability.

* **Input:** `--config rosetta_map.yaml`
* **Output (Console):**
```text
> Connected to Supabase.
> Found 5 tables in whitelist.
> [!] Table T001 has 15 columns.
> [i] Detected 2 potential Enums in T001.

```


### 5.3 Command: `generate`

The core execution command.

* **Input:** `--config rosetta_map.yaml`, optional `--output-dir generated`, optional `--format`
* **Process:**
1. Reflect Schema via SQLAlchemy.
2. Sample rows (optional) and scrub PII (optional).
3. Call Gemini API for semantic enrichment (response parsed as JSON).
4. Render Templates.
5. Emit `functions.json`.
6. Format code with `ruff` if `--format` is set.


* **Output:** Writes `./generated/` folder containing models, repos, audit log, and `functions.json`.

### 5.4 Command: `serve`

Starts the local Web UI backed by the same pipeline.

* **Input:** Optional `--host`, `--port`, `--reload`.
* **Process:**
  1. Import FastAPI app from `rosetta_bridge.web.app:app`.
  2. Start `uvicorn` with the given host/port.
* **Output:** Serves a minimal UI at `http://<host>:<port>` that can call the underlying inspect/generate endpoints.

---

## 6. Directory Structure

```text
rosetta_bridge/
├── src/
│   └── rosetta_bridge/
│       ├── analyzer/           # Heuristics for Enum/PII detection
│       ├── codegen/            # Jinja2 templates and rendering logic
│       ├── core/               # Configuration and Type definitions
│       ├── inference/          # Gemini Interaction layer
│       ├── inspector/          # SQLAlchemy Reflection logic
│       └── main.py             # CLI Entry point
├── templates/                  # Jinja2 files (.py.j2)
├── tests/
│   ├── fixtures/               # SQL dumps for testing
│   └── unit/                   # Pytest suites
├── rosetta_map.yaml            # User configuration
├── pyproject.toml              # uv manifest
└── spec.md                     # This file

```

---

## 7. Testing Strategy

### 7.1 Unit Testing

* **Schema Parsing:** Test that PostgreSQL types are correctly mapped to Python types.
* **Code Generation:** Render templates with mock data and verify outputs exist.

### 7.2 Safety Validation

* **Regex Check:** Unit test scans generated `_repos.py` for "commit()" and "UPDATE".

### 7.3 Integration Testing

* **Database:** Use a local Dockerized Postgres or a test Supabase project.
* **LLM:** Mock the Gemini API response to avoid costs during CI/CD.

---

## 8. Future Roadmap (Out of Scope for v1)

* **Multilingual Support:** Generating docstrings in other languages.
* **Self-Healing:** Auto-correction of Pydantic models if validation fails.
* **Vector Integration:** Generating embeddings for table descriptions.
