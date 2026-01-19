# Technical Specification: Rosetta Bridge

**Version:** 1.0.0
**Status:** Approved for Development
**Author:** System Architect
**Target Platform:** Python 3.10+ (Managed by `uv`)

---

## 1. Executive Summary

**Rosetta Bridge** is a CLI-based build tool designed to bridge the "Execution Gap" between cryptic legacy SQL schemas (specifically Supabase/PostgreSQL) and modern AI Agents. It automates the semantic understanding of database structures using Google's Gemini models, generating type-safe Python code (Pydantic models) and "Safe-by-Design" function tools that Agents can utilize immediately.

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
| **LLM Orchestration** | `Google Gemini API` | Uses `gemini-1.5-flash` for high-speed, low-cost semantic reasoning. |
| **Code Generation** | `Jinja2` | Templating engine to produce clean Python code. |
| **CLI Framework** | `Typer` + `Rich` | Type-safe CLI builder with excellent UX/formatting. |
| **Testing** | `Pytest` | Standard unit testing framework. |

---

## 3. System Architecture

The system operates as a **unidirectional build pipeline**. It does not run as a persistent server.

### 3.1 High-Level Data Flow

1.  **Ingestion:** Connect to Supabase $\rightarrow$ Reflect Schema Metadata (Tables, Columns, Types).
2.  **Analysis:** Detect candidates for Enums (low cardinality) & flag PII (Regex heuristics).
3.  **Inference:** Send sanitized metadata to Gemini $\rightarrow$ Receive Semantic Descriptions.
4.  **Generation:** Hydrate Jinja2 templates $\rightarrow$ Write `.py` artifacts & Audit Log.

### 3.2 Output Artifacts

The tool generates a "Repository Pattern" structure in a `generated/` directory:

* **`_models.py`:** Pydantic models representing the tables (Locked file).
* **`_repos.py`:** Read-Only SQL access methods (Locked file).
* **`audit_log.md`:** A report of what was mapped and why.

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
  model: "gemini-1.5-flash"
  temperature: 0.0
privacy:
  sample_rows: bool      # If True, sends 3 rows of data to Gemini for context
  scrub_pii: bool        # If True, suppresses columns looking like SSN/Email

```

### 4.2 Metadata Objects

**`ColumnMetadata`**

* `original_name`: str (e.g., `FLG_STS`)
* `data_type`: str (e.g., `VARCHAR`)
* `is_primary_key`: bool
* `sample_values`: List[Any] (Optional)
* `detected_pii`: bool

**`EnrichedColumn` (Post-Gemini)**

* `semantic_name`: str (e.g., `status_flag`)
* `description`: str (e.g., "Indicates if the account is Active (A) or Closed (C)")
* `suggested_enum`: Optional[Dict[str, str]]

**`TableContext`**

* `table_name`: str
* `columns`: List[EnrichedColumn]
* `business_purpose`: str (Gemini inferred summary)

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

* **Input:** `--config rosetta_map.yaml`
* **Process:**
1. Reflect Schema via SQLAlchemy.
2. Call Gemini API for semantic enrichment.
3. Render Templates.
4. Format code (via `ruff` if available or internal logic).


* **Output:** Writes `./generated/` folder containing models, repos, and audit log.

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
* **Code Generation:** Render templates with mock data and verify the output is valid Python syntax.

### 7.2 Safety Validation

* **Regex Check:** A specific test case must scan all generated `_repos.py` files to ensure they do **not** contain the strings `.commit()`, `.execute("UPDATE`, or `.execute("DELETE`.

### 7.3 Integration Testing

* **Database:** Use a local Dockerized Postgres or a test Supabase project.
* **LLM:** Mock the Gemini API response to avoid costs during CI/CD.

---

## 8. Future Roadmap (Out of Scope for v1)

* **Multilingual Support:** Generating docstrings in other languages.
* **Self-Healing:** Auto-correction of Pydantic models if validation fails.
* **Vector Integration:** Generating embeddings for table descriptions.
