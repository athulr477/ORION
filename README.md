# ORION — AI-Augmented Requirements Traceability Matrix Engine

> Automatically link PRD specifications to implementation code and test coverage using semantic embeddings, structural AST analysis, and a local LLM — with a live React dashboard.

![ORION System](./Level_1_DFD_ORION_Corrected.png)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [AI & Scoring Pipeline](#ai--scoring-pipeline)
4. [API Reference](#api-reference)
5. [Data Model](#data-model)
6. [Project Structure](#project-structure)
7. [Getting Started](#getting-started)
8. [Environment Variables](#environment-variables)
9. [Running Migrations](#running-migrations)
10. [Frontend](#frontend)
11. [Integrations](#integrations)
12. [Evaluation & Benchmark](#evaluation--benchmark)
13. [Tech Stack](#tech-stack)

---

## Overview

ORION is a backend-first system that automates Requirements Traceability Matrix (RTM) generation. It ingests requirements from **Jira** (via REST API or webhook), ingests test cases from **GitHub** (via App webhook on pull requests), and classifies each requirement-test pair with a **hybrid risk score** derived from two independent signals:

- **Semantic score** — cosine similarity between BGE-small-en-v1.5 ONNX embeddings of the requirement description and the test function body.
- **Structural score** — AST-level matching between constraint predicates extracted from the requirement text and assertion patterns extracted from test source code.

The combined risk score drives a three-class status label — **Covered / Partial / Drifted** — persisted to PostgreSQL (with pgvector) and surfaced in a React dashboard. For Partial and Drifted pairs, an Ollama-hosted Llama 3.1 8B model generates a one-sentence, evidence-grounded audit summary.

The system is **multi-tenant**: every resource (requirements, test cases, matrix entries) is scoped to a `workspace_id`, and the auth layer issues JWT tokens that carry both user identity and workspace context.

---

## Architecture

```
                    +---------------------------------------------+
                    |           React Frontend (Vite)             |
                    |  Dashboard . Heatmap . Simulate . Settings  |
                    +--------------------+------------------------+
                                         |  HTTP / REST
                    +--------------------v------------------------+
                    |        FastAPI Application Server           |
                    |  (Uvicorn, async, embedded task worker)     |
                    |                                             |
                    |  /api/v1/auth         JWT, workspaces       |
                    |  /api/v1/webhooks     Jira / GitHub ingest  |
                    |  /api/v1/dashboard    RTM table, stats, XAI |
                    |  /api/v1/github       GitHub App events     |
                    |  /api/v1/jira         Jira REST sync        |
                    |  /api/v1/tasks        Background task queue |
                    |  /api/v1/integrations Connection status     |
                    +------+-------------+---------------+--------+
                           |             |               |
          +----------------v--+  +-------v------+  +----v--------------+
          |  PostgreSQL 16 +  |  |  BGE-small   |  |  Ollama           |
          |  pgvector         |  |  ONNX (CPU)  |  |  llama3.1:8b      |
          |  requirements     |  |  384-dim     |  |  temp=0.0         |
          |  test_cases       |  |  embeddings  |  |  audit summaries  |
          |  traceability_    |  +--------------+  +-------------------+
          |  matrix           |
          |  task_jobs        |
          |  workspaces       |
          +-------------------+
```

### Request lifecycle — GitHub PR event

1. `POST /api/v1/github/events` — HMAC-SHA256 signature verified against `GITHUB_WEBHOOK_SECRET`.
2. Orion fetches changed test files from GitHub using an **Installation Access Token** minted from the GitHub App private key (RS256 JWT).
3. Each test file is parsed with **Tree-sitter** (Python / JS / TS / Java / Go) to extract `@traces("REQ-xxx")` decorators and assertion AST nodes.
4. The requirement `REQ-xxx` is looked up in Postgres; its embedding was pre-computed on ingest.
5. A new 384-dim embedding is computed for the test function body (BGE-small ONNX, CPU).
6. Structural constraints (from the requirement) and assertions (from the test) are matched by the `structural_matcher`.
7. `risk_engine.classify()` computes the hybrid score and status.
8. For Partial/Drifted pairs, the verbalization service builds a deterministic `EvidenceTuple` and sends it to Ollama to produce the audit summary.
9. Results are written to `traceability_matrix` and a **GitHub Check Run** is posted back to the PR with a markdown report table.

---

## AI & Scoring Pipeline

### Embedding — `orion/embedding/engine.py`

| Property | Value |
|---|---|
| Model | `BAAI/bge-small-en-v1.5` |
| Runtime | ONNX Runtime `CPUExecutionProvider` (no PyTorch dependency) |
| ONNX source | `xenova/bge-small-en-v1.5` on HuggingFace Hub (auto-downloaded) |
| Output dimensions | 384 |
| Pooling | Mean pooling over token embeddings, attention-mask weighted |
| Normalization | L2 normalization — dot product equals cosine similarity |
| Storage | `pgvector` `Vector(384)` column on `requirements` and `test_cases` |

Embeddings are computed once at ingest and stored. Retrieval is a single Postgres lookup, not a live model call.

### Structural Extraction — `orion/extraction/`

- **Requirements** (`requirement_extractor.py`) — parses the requirement description with regex-based NLP to extract constraints: comparison operators (`<`, `>`, `<=`, `>=`, `==`, `!=`), numeric thresholds, boolean conditions, and domain keywords. Output stored as JSONB in `requirements.constraints_extracted`.
- **Test code** (`code_extractor.py` + `tree_sitter_engine.py`) — uses Tree-sitter grammars for Python, JavaScript, TypeScript, Java, and Go to extract `assert` statements and test framework assertion calls. Output stored as JSONB in `test_cases.assertions_extracted`.

### Hybrid Risk Scoring — `orion/analysis/risk_engine.py`

```
alignment  = 0.6 x semantic_score + 0.4 x structural_score
risk_score = 1.0 - alignment
```

| risk\_score | Status |
|---|---|
| < 0.25 | **Covered** |
| 0.25 to 0.60 | **Partial** |
| > 0.60 | **Drifted** |

Confidence is computed as normalized distance from the nearest classification boundary. A `has_drift` flag (triggered by a detected requirement delta) forces the status to Drifted with `risk_score >= 0.85`.

### LLM Verbalization — `orion/verbalization/`

The LLM is used **only** to phrase audit summaries for Partial/Drifted pairs. It plays no role in scoring, classification, or data retrieval. The `EvidenceTuple` fed to the model is assembled deterministically from database fields; the model is instructed to produce exactly one sentence without inventing claims.

```
System prompt: "You are a requirements traceability auditor. Write exactly
               one concise sentence based ONLY on the evidence provided."

Temperature: 0.0    Max tokens: 200
```

If Ollama is unavailable, the system falls back to a deterministic template sentence. No external API calls are made; the LLM runs entirely locally.

### Requirement Delta Tracking — `orion/analysis/delta_parser.py`

When a Jira issue is updated, `delta_parser` diffs the old and new requirement content (title, description, constraints). The structured diff is stored in `traceability_matrix.requirement_delta` (JSONB). Detected semantic drift re-triggers full analysis for all linked test cases.

---

## API Reference

All routes are prefixed `/api/v1`. The OpenAPI spec is available at `/docs` when the server is running.

### Authentication — `/auth`

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/token` | OAuth2 password flow — returns JWT bearer token |
| `GET` | `/auth/workspaces` | List workspaces the authenticated user belongs to |

Tokens are HS256-signed using `SECRET_KEY`. Default expiry: 60 minutes.

### Webhook Ingestion — `/webhooks`

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhooks/jira` | Receive Jira `issue_created` / `issue_updated` events. Verifies HMAC-SHA256 (`JIRA_WEBHOOK_SECRET`). Upserts requirement, computes embedding, extracts constraints. |
| `POST` | `/webhooks/github` | Receive GitHub push payload (simulate mode). Parses `@traces` decorators, upserts test cases, links to requirements. Verifies HMAC-SHA256 (`GITHUB_WEBHOOK_SECRET`). |

### Dashboard — `/dashboard`

| Method | Path | Description |
|---|---|---|
| `GET` | `/dashboard/matrix` | Paginated RTM table. Query params: `status`, `search`, `sort`, `order`, `page`, `page_size`. |
| `POST` | `/dashboard/matrix/reclassify` | Live threshold preview — re-classify all entries with custom covered/drifted thresholds without persisting. Used by the sensitivity slider. |
| `GET` | `/dashboard/matrix/{entry_id}/heatmap` | XAI evidence for a single matrix entry: constraint-assertion match details, keyword overlap, per-component scores. |
| `GET` | `/dashboard/stats` | Aggregate summary: counts by status, averages, total requirements and test cases. |
| `POST` | `/dashboard/simulate` | Enqueue a full end-to-end simulation run as a background task. |
| `POST` | `/dashboard/matrix/{entry_id}/override` | QA Lead manual status override with audit log entry. Requires `qa_lead` role. |

### GitHub App — `/github`

| Method | Path | Description |
|---|---|---|
| `POST` | `/github/events` | Receive GitHub App `pull_request` events. Runs full hybrid analysis on changed test files and posts a Check Run back to the PR. |
| `GET` | `/github/repos` | List repositories accessible to the configured GitHub App installation. |
| `GET` | `/github/repos/{owner}/{repo}/pulls` | List open PRs for a repository. |
| `GET` | `/github/repos/{owner}/{repo}/pulls/{pull_number}/files` | List changed files for a PR. |

### Jira REST Sync — `/jira`

| Method | Path | Description |
|---|---|---|
| `POST` | `/jira/sync` | Bulk-import all issues from the configured Jira project via JQL search. Computes embeddings and extracts constraints. |
| `POST` | `/jira/sync/{issue_key}` | On-demand single-ticket refresh. |
| `POST` | `/jira/report-drift` | Post drift-alert comments back to Jira for Partial/Drifted pairs. Includes a duplicate-comment guard. |

### Task Queue — `/tasks`

| Method | Path | Description |
|---|---|---|
| `GET` | `/tasks` | List recent background tasks for the current workspace (status, progress, step). |
| `GET` | `/tasks/{task_id}` | Detailed status for a specific task, including payload and result. |

### Integrations — `/integrations`

| Method | Path | Description |
|---|---|---|
| `GET` | `/integrations/status` | Current configuration status for Jira, GitHub App, and Ollama. API tokens are masked in the response. |
| `POST` | `/integrations/jira/test` | Test Jira connectivity and verify project permissions. |
| `POST` | `/integrations/github/test` | Verify GitHub App PEM and mint a test RS256 JWT. |

### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check: `{"status": "healthy", "service": "orion"}` |

---

## Data Model

Core tables, all scoped by `workspace_id`:

```
workspaces
  id UUID PK . name . created_at

workspace_members
  workspace_id FK . user_id FK . role

users
  id UUID PK . username . hashed_password . role (viewer | qa_lead | admin)

requirements
  id UUID PK . workspace_id FK . external_id . title . description
  source . raw_payload JSONB . constraints_extracted JSONB
  embedding Vector(384)        <- pgvector
  created_at . updated_at

test_cases
  id UUID PK . workspace_id FK . requirement_id FK (nullable)
  function_name . file_path . source_code . source_language
  assertions_extracted JSONB . embedding Vector(384)
  created_at . updated_at

traceability_matrix
  id UUID PK . workspace_id FK . requirement_id FK . test_case_id FK
  semantic_score Float . structural_score Float
  risk_score Float             <- 1 - (0.6 x sem + 0.4 x struct)
  confidence Float
  status (Covered | Partial | Drifted)
  requirement_delta JSONB      <- structured diff on requirement change
  audit_summary Text           <- LLM-generated one-sentence explanation
  is_manually_overridden Bool
  created_at . updated_at

audit_log
  id . user_id FK . workspace_id FK . traceability_matrix_id FK
  previous_status . new_status . rationale . created_at

task_jobs
  id UUID PK . workspace_id FK . task_type . status . progress
  current_step . payload JSONB . result JSONB . error_message
  created_at . started_at . completed_at
```

Database migrations are managed with Alembic:

| Revision | Purpose |
|---|---|
| `001_enable_pgvector` | Enables the `vector` extension |
| `002_create_core_tables` | requirements, test\_cases, traceability\_matrix |
| `43a81871df64` | Multi-tenant workspaces, workspace\_members, FK scoping |

---

## Project Structure

```
ORION/
+-- Level_1_DFD_ORION_Corrected.png   Architecture diagram
+-- evaluation_report.md              Benchmark results (30-pair)
+-- orion_50_realworld_requirements.csv  50-requirement dataset
+-- diagnose_actual_runs.py           Evaluation diagnostic script
+-- draw_level1_dfd.py                DFD diagram generation
|
+-- backend/
|   +-- pyproject.toml                Python project metadata & dependencies
|   +-- alembic.ini                   Alembic migration configuration
|   +-- docker-compose.yml            PostgreSQL + pgvector (Docker)
|   +-- .env.example                  Environment variable template
|   +-- migrations/
|   |   +-- versions/                 Alembic revision files
|   +-- orion/
|       +-- app.py                    FastAPI app entry point & lifespan
|       +-- config.py                 Pydantic settings (reads .env)
|       +-- database.py               SQLAlchemy async engine & session
|       +-- auth/                     JWT auth, OAuth2 flow, RBAC
|       +-- models/                   SQLAlchemy ORM models
|       |   +-- requirement.py
|       |   +-- test_case.py
|       |   +-- traceability_matrix.py
|       |   +-- workspace.py
|       |   +-- user.py
|       |   +-- audit_log.py
|       |   +-- task_job.py
|       +-- ingestion/                Webhook parsers, upsert logic, HMAC verification
|       +-- extraction/               AST extraction via Tree-sitter (5 languages)
|       |   +-- tree_sitter_engine.py Multi-language parser setup
|       |   +-- code_extractor.py     Test assertion extraction
|       |   +-- requirement_extractor.py  Constraint NLP extraction
|       +-- embedding/                BGE-small ONNX inference
|       |   +-- engine.py             embed_text(), semantic_similarity()
|       |   +-- text_builder.py       Text normalization for embedding
|       +-- analysis/                 Core scoring pipeline
|       |   +-- risk_engine.py        Hybrid risk formula + classification
|       |   +-- structural_matcher.py Constraint-assertion matching
|       |   +-- delta_parser.py       Requirement change diff
|       |   +-- delta_service.py      Drift detection orchestration
|       +-- verbalization/            LLM audit summary generation
|       |   +-- llm_client.py         Ollama HTTP client wrapper
|       |   +-- evidence.py           Deterministic EvidenceTuple builder
|       |   +-- service.py            Verbalization orchestration
|       +-- dashboard/                RTM dashboard API routes & schemas
|       +-- github/                   GitHub App: auth, Check Runs, PR analysis
|       +-- jira/                     Jira REST: sync, ADF rendering, drift comments
|       +-- integrations/             Connection status & test endpoints
|       +-- queue/                    Embedded async task queue (broker + worker)
|       +-- evaluation/               Benchmark evaluator & 30-pair dataset
|
+-- frontend/
|   +-- package.json                  React 19 + Vite 8 + lucide-react
|   +-- vite.config.js
|   +-- index.html
|   +-- src/
|       +-- App.jsx                   Main app shell & routing
|       +-- index.css                 Global styles
|       +-- api/client.js             Fetch wrapper
|       +-- contexts/WorkspaceContext.jsx
|       +-- components/
|           +-- LoginModal.jsx
|           +-- MatrixTable.jsx       Paginated RTM table
|           +-- HeatmapModal.jsx      XAI evidence modal
|           +-- SensitivitySlider.jsx Live reclassification slider
|           +-- OverrideModal.jsx     QA Lead manual override
|           +-- SimulateModal.jsx     End-to-end demo trigger
|           +-- StatsBar.jsx          Dashboard header cards
|           +-- StatusBadge.jsx       Covered/Partial/Drifted pill
|           +-- TaskQueueDrawer.jsx   Background task status drawer
|           +-- IntegrationsModal.jsx Jira/GitHub/Ollama config status
|           +-- UserNav.jsx           Auth controls
|
+-- docs/
|   +-- diagrams/                     DFD levels 0-2, use case, activity
|   +-- report/                       MCA final project report (DOCX)
|
+-- tests/
    +-- test_core.py
```

---

## Getting Started

### Prerequisites

| Dependency | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker (or local PostgreSQL 16) | — |
| Ollama (optional, for LLM summaries) | 0.4+ |

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/ORION.git
cd ORION
```

### 2. Start PostgreSQL with pgvector

```bash
cd backend
docker compose up -d
```

This pulls `pgvector/pgvector:pg16` and starts a container on `localhost:5432` with:
- User: `orion`
- Password: `orion_secret` _(change this in production)_
- Database: `orion_db`

To use an existing Postgres instance, ensure the `vector` extension is available and update your `.env` connection strings.

### 3. Backend setup (PowerShell)

```powershell
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install the package and all runtime + dev dependencies
pip install -e ".[dev]"
```

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
notepad .env
```

At minimum, set `SECRET_KEY`. Everything else has working defaults for local development. See the [Environment Variables](#environment-variables) table for full details.

```powershell
# Generate a SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run database migrations

```powershell
# From backend/ with the venv active
alembic upgrade head
```

### 6. Start the backend server

```powershell
uvicorn orion.app:app --reload --host 0.0.0.0 --port 8000
```

The embedded task worker starts automatically via `asyncio.create_task`. No separate worker process is needed.

API docs: **http://localhost:8000/docs**

### 7. Pull the Ollama model (optional)

```bash
ollama pull llama3.1:8b
```

If Ollama is not running, audit summaries fall back to deterministic template sentences. All scoring and classification work without Ollama.

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://orion:orion_secret@localhost:5432/orion_db` | Async connection string (asyncpg driver). |
| `DATABASE_URL_SYNC` | Yes | `postgresql://orion:orion_secret@localhost:5432/orion_db` | Sync connection string for Alembic. |
| `SECRET_KEY` | **Required** | _(empty — server will not start)_ | HMAC-HS256 JWT signing key. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JIRA_WEBHOOK_SECRET` | Webhooks | _(empty)_ | HMAC-SHA256 secret for Jira webhook verification. |
| `GITHUB_WEBHOOK_SECRET` | Webhooks | _(empty)_ | HMAC-SHA256 secret for GitHub App webhook verification. |
| `GITHUB_APP_ID` | GitHub App | `0` | Numeric App ID from your GitHub App settings. |
| `GITHUB_APP_INSTALLATION_ID` | GitHub App | `0` | Installation ID from the App installed on your org/repo. |
| `GITHUB_APP_PRIVATE_KEY_PATH` | GitHub App | _(empty)_ | Path to the `.pem` private key downloaded from GitHub App settings. Store outside the repo (e.g. `./secrets/github-app.pem`). |
| `JIRA_BASE_URL` | Jira sync | _(empty)_ | Atlassian domain, e.g. `https://your-org.atlassian.net`. |
| `JIRA_USER_EMAIL` | Jira sync | _(empty)_ | Email associated with the Jira API token. |
| `JIRA_API_TOKEN` | Jira sync | _(empty)_ | Token from [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens). |
| `JIRA_PROJECT_KEY` | Jira sync | `SCRUM` | Jira project key to import issues from. |
| `OLLAMA_BASE_URL` | Optional | `http://localhost:11434` | Ollama server URL. |
| `OLLAMA_MODEL` | Optional | `llama3.1:8b` | Ollama model tag for verbalization. |
| `SENTRY_DSN` | Optional | _(empty)_ | Sentry DSN for error tracking. Leave blank to disable. |

> **Note on secrets**: `.env`, `*.pem`, and the `secrets/` directory are all excluded by `.gitignore`. Never commit credential files to version control.

---

## Running Migrations

```powershell
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Roll back one revision
alembic downgrade -1
```

Migration files live in `backend/migrations/versions/`.

---

## Frontend

The dashboard is a React 19 SPA, bundled with Vite 8.

### Setup

```bash
cd frontend
npm install
npm run dev
```

Dev server: **http://localhost:5173**

### Production build

```bash
npm run build
# Static output in frontend/dist/
```

### Key dependencies

| Package | Purpose |
|---|---|
| `react` 19 | UI library |
| `react-dom` 19 | DOM renderer |
| `lucide-react` | Icon set |
| `vite` 8 | Build tool & dev server |
| `oxlint` | JavaScript linter |

---

## Integrations

### Jira

1. Create an API token at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Set `JIRA_BASE_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN`, and `JIRA_PROJECT_KEY` in `.env`.
3. Bulk-import existing tickets: `POST /api/v1/jira/sync`.
4. For real-time updates, configure a Jira webhook pointing to `POST /api/v1/webhooks/jira` and set a shared secret in both Jira and `JIRA_WEBHOOK_SECRET`.

### GitHub App

1. Create a GitHub App at [github.com/settings/apps](https://github.com/settings/apps).
2. Webhook URL: `https://<your-host>/api/v1/github/events`. Set a webhook secret.
3. Required permissions: `Contents: Read`, `Checks: Write`, `Pull requests: Read`.
4. Install the App on your repository and note the Installation ID.
5. Download the private key `.pem`. Store it outside the repo and set `GITHUB_APP_PRIVATE_KEY_PATH`.
6. Set `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, and `GITHUB_WEBHOOK_SECRET` in `.env`.

**Test decorator convention** — annotate test functions to declare coverage:

```python
@traces("REQ-123")
def test_login_rate_limit():
    ...
```

Tree-sitter parses this during both webhook ingestion and PR Check Run analysis.

### Ollama

```bash
# Install from https://ollama.com
ollama pull llama3.1:8b
# Default: listens on localhost:11434
```

Verify the connection at `GET /api/v1/integrations/status`.

---

## Evaluation & Benchmark

### 30-Pair Benchmark

A curated dataset of 30 requirement-test pairs (10 each: Covered, Partial, Drifted) was used to compare the hybrid engine against a cosine-only baseline. Full per-pair scores, confusion matrices, and per-class F1 are in [`evaluation_report.md`](./evaluation_report.md).

| Engine | Macro Precision | Macro Recall | Macro F1 | Accuracy |
|---|---|---|---|---|
| **Orion Hybrid** | **0.726** | 0.567 | **0.559** | 0.567 |
| Cosine Baseline | 0.426 | 0.600 | 0.493 | 0.600 |

The structural signal improves precision significantly (+0.300 macro), particularly for Partial vs Drifted pairs where the test body uses correct domain vocabulary but wrong assertion values. The cosine baseline systematically misclassifies these as Partial because semantic similarity stays moderate.

### 50-Requirement Real-World Dataset

[`orion_50_realworld_requirements.csv`](./orion_50_realworld_requirements.csv) contains 50 real-world-style requirements for extended evaluation covering: numeric thresholds, boolean conditions, response time bounds, error rate limits, and data integrity constraints across authentication, performance, and storage domains.

### Running the evaluator

```powershell
# From backend/ with the venv active
python -m orion.evaluation.evaluator
```

Outputs: per-pair scores, confusion matrix, macro F1/precision/recall for both engines.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI 0.115+ (async) |
| ASGI server | Uvicorn (standard extras) |
| ORM | SQLAlchemy 2.0 (async, mapped\_column API) |
| Database | PostgreSQL 16 + pgvector 0.3+ |
| Migrations | Alembic 1.13+ |
| Async driver | asyncpg 0.29+ |
| Embeddings | BAAI/bge-small-en-v1.5 via ONNX Runtime (CPU) |
| AST parsing | Tree-sitter 0.22+ (Python, JS, TS, Java, Go) |
| LLM | Ollama SDK 0.4+ — Llama 3.1 8B (local, offline) |
| Auth | PyJWT HS256 + passlib/bcrypt |
| Settings | pydantic-settings 2 (reads `.env`) |
| HTTP client | httpx 0.27+ |
| Error tracking | Sentry SDK (optional) |
| Frontend | React 19 + Vite 8 |
| Icons | lucide-react |
| Python linting | Ruff 0.5+ |
| JavaScript linting | oxlint |
| Testing | pytest + pytest-asyncio |

---

## License

[MIT](./LICENSE)
