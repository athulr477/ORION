# Orion — AI-Powered Requirements Traceability Matrix (RTM) Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![React + Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb.svg)](https://vitejs.dev/)
[![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL-pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![GitHub App](https://img.shields.io/badge/GitHub-App%20Integration-181717.svg)](https://docs.github.com/en/apps)
[![Atlassian Jira](https://img.shields.io/badge/Jira-Cloud%20REST%20API%20v3-0052CC.svg)](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Orion is an automated, AI-augmented **Requirements Traceability Matrix (RTM) Engine** designed to eliminate **silent specification drift** between agile requirement specifications (Jira) and automated software test suites (pytest on GitHub).

Unlike conventional semantic retrieval approaches that evaluate traceability solely via embedding proximity—and consequently overlook critical numerical boundary and assertion changes—Orion pairs a **Dual-Sided Structural Extractor** with a **Semantic Vector Engine**. Its deterministic hybrid risk engine blocks drifted Pull Requests in GitHub CI/CD, writes audit alerts back to Jira, and provides an interactive real-time dashboard.

---

## 🌟 Key Features

* **Bi-Directional Jira Cloud Integration:** Syncs issues via JQL (`project = "YOUR_PROJECT_KEY"`), recursively decodes complex Atlassian Document Format (ADF) payloads into plain text, and posts automated drift audit comments back onto tickets with duplicate suppression.
* **Native GitHub App Check Runs:** Authenticates using RS256 JWTs and installation access tokens to intercept Pull Request webhooks, evaluate traceability, and post native GitHub Check Runs with pass/neutral/fail statuses and line annotations.
* **Dual-Sided Structural Extraction:**
  * **Requirement Constraints:** Regex & NLP extract quantitative boundaries (`<= 100ms`, `== 200`, `timeout > 5s`).
  * **Test Assertions:** Python AST (Abstract Syntax Tree) parses actual Python comparison operators, targets, and expected values from functions decorated with `@traces("REQ-xxx")`.
* **Hybrid Risk Engine ($0.6 \cdot \text{sem} + 0.4 \cdot \text{struct}$):** Combines dense vector cosine similarity (local `bge-small-en-v1.5` ONNX embeddings) with discrete structural constraint matching to classify pairs into **Covered** ($\ge 0.70$), **Partial** ($0.45 - 0.70$), or **Drifted** ($< 0.45$).
* **Evidence-Grounded LLM Verbalization:** Prompts a local LLM (Ollama Llama 3.1 8B) strictly with extracted AST evidence and constraint diffs to generate human-readable audit summaries without hallucinations (falling back to a deterministic template if offline).
* **Interactive Dashboard (React + Vite):** Real-time matrix view, dynamic risk threshold sliders, and component-level drift heatmaps.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion
        J[Jira Cloud v3 REST API] -->|ADF Parser & JQL Sync| DB[(PostgreSQL + pgvector)]
        GH[GitHub App Webhook] -->|PR Opened / Sync| WH[Orion Webhook Router]
    end

    subgraph Processing Pipeline
        WH --> BG[FastAPI BackgroundTasks]
        BG --> AST[AST Test Code Parser]
        DB --> REQ[Requirement Extractor]
        
        AST --> EXT[Dual-Sided Structural Matcher]
        REQ --> EXT
        
        AST --> ONNX[BGE-Small ONNX Vectorizer]
        REQ --> ONNX
        
        EXT --> HRE[Hybrid Risk Engine\n0.6*Semantic + 0.4*Structural]
        ONNX --> HRE
    end

    subgraph Decision & Feedback Loop
        HRE --> CLASSIFY{Classification}
        CLASSIFY -->|>= 0.70| COV[Covered]
        CLASSIFY -->|0.45 - 0.70| PAR[Partial]
        CLASSIFY -->|< 0.45| DRIFT[Drifted]
        
        DRIFT --> LLM[Ollama Llama 3.1 Verbalizer]
        PAR --> LLM
        
        LLM --> GHC[GitHub Check Run API\nNeutral / Failure + Annotations]
        LLM --> JIRAC[Jira Comment API\nAudit Drift Warning]
        HRE --> DASH[React + Vite Dashboard]
    end
```

---

## 📊 Empirical Benchmark Evaluation

In a controlled benchmark on a 30-pair ground-truth dataset (10 Covered, 10 Partial, 10 Drifted), Orion's **Hybrid Engine** was evaluated against a standard **Cosine-Only Semantic Baseline**:

| Metric | Cosine-Only Baseline | Orion Hybrid Engine | Improvement ($\Delta$) |
|---|:---:|:---:|:---:|
| **Accuracy** | 50.0% | **60.0%** | **+10.0%** |
| **Macro Precision** | 0.472 | **0.573** | **+0.101** |
| **Macro Recall** | 0.500 | **0.600** | **+0.100** |
| **Macro F1-Score** | 0.409 | **0.569** | **+0.160** |
| **Drifted F1-Score** | 0.000 (0/10 caught) | **0.750 (8/10 caught)** | **+0.750** |
| **Mean Pipeline Latency** | 22.4 ms | 26.2 ms | +3.8 ms |

> **Key Finding:** Dense semantic embeddings assign high cosine similarity ($\sim 0.88$) to numerically contradictory statements (e.g., `latency <= 200ms` vs `latency <= 100ms`). Orion's structural AST matcher exposes this drift, achieving a **0.750 F1-score on Drifted pairs** where pure embeddings failed completely. *(Full results in [`evaluation_report.md`](evaluation_report.md)).*

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Core** | Python 3.11, FastAPI, Pydantic v2, Uvicorn |
| **Database & Vector** | PostgreSQL 16, pgvector, SQLAlchemy 2.0 (Async), Alembic |
| **Code Extraction** | Python `ast` module, regular expression constraint extractors |
| **Embeddings** | HuggingFace BAAI/bge-small-en-v1.5 running via ONNX Runtime |
| **LLM Verbalization** | Ollama (Llama 3.1 8B) with deterministic template fallback |
| **Integrations** | GitHub Apps API (PyJWT, RS256), Atlassian Jira Cloud REST API v3 |
| **Frontend** | React 18, Vite, Lucide Icons, Vanilla CSS Design System |

---

## 🚀 Getting Started

### 1. Prerequisites
* [Docker Desktop](https://www.docker.com/) (for PostgreSQL + pgvector)
* [Python 3.11+](https://www.python.org/)
* [Node.js 18+](https://nodejs.org/) (for frontend)
* *(Optional)* [Ollama](https://ollama.ai/) with `llama3.1:8b` pulled

### 2. Installation & Environment Setup

Clone the repository and install backend dependencies:

```powershell
git clone https://github.com/your-username/orion.git
cd orion

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install package in editable mode
pip install -e .
```

Copy the example environment configuration and fill in your credentials:

```powershell
cp .env.example .env
```

Your `.env` should contain (see `.env.example` for a full template):
```env
DATABASE_URL=postgresql+asyncpg://orion:your_password@localhost:5432/orion_db
DATABASE_URL_SYNC=postgresql://orion:your_password@localhost:5432/orion_db

# Webhook secrets (HMAC-SHA256)
JIRA_WEBHOOK_SECRET=your-jira-webhook-secret
GITHUB_WEBHOOK_SECRET=your-github-webhook-secret

# GitHub App Integration
# Create a GitHub App at github.com/settings/apps and install it on your repo.
GITHUB_APP_ID=your_app_id
GITHUB_APP_INSTALLATION_ID=your_installation_id
GITHUB_APP_PRIVATE_KEY_PATH=./secrets/github-app.pem

# Jira Cloud Integration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=your_email@domain.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=YOUR_PROJECT_KEY

# LLM Verbalization (optional — falls back to deterministic template)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### 3. Start Database & Run Migrations

```powershell
# Start PostgreSQL with pgvector
docker-compose up -d

# Run database migrations
alembic upgrade head
```

### 4. Run the Verification Test Suites

Verify that all subsystems are operational:

```powershell
# Run individual phase verifications
python scripts/verify_phase1.py     # Database schema & pgvector
python scripts/verify_phase3.py     # AST & constraint extraction
python scripts/verify_phase5.py     # Hybrid risk engine
python scripts/verify_phase7.py     # LLM verbalization
python scripts/verify_phase9.py     # GitHub App Check Runs
python scripts/verify_phase10.py    # 30-Pair Benchmark Evaluation
python scripts/verify_jira_sync.py  # Jira Cloud sync & ADF parser
```

### 5. Start the Application

**Terminal 1 — Backend API:**
```powershell
uvicorn orion.app:app --reload --port 8000
```
API Documentation will be available at `http://localhost:8000/docs`.

**Terminal 2 — Frontend Dashboard:**
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` to access the interactive RTM dashboard.

---

## 📁 Project Structure

```
ORION/
├── orion/                     # Core application package
│   ├── app.py                 # FastAPI application factory & routes
│   ├── database.py            # Async engine, session, & pgvector setup
│   ├── models.py              # SQLAlchemy ORM models (Requirement, Test, Link)
│   ├── extraction/            # Dual-sided AST & constraint parsers
│   ├── embeddings/            # BGE-small ONNX embedding client
│   ├── matcher/               # Hybrid risk engine (0.6*sem + 0.4*struct)
│   ├── verbalizer/            # LLM audit summarizer (Ollama + fallback)
│   ├── github/                # GitHub App auth, client, & webhook router
│   ├── jira/                  # Jira REST v3 client & recursive ADF parser
│   └── evaluation/            # 30-pair benchmark dataset & evaluation harness
├── frontend/                  # React + Vite dashboard application
├── migrations/                # Alembic database migrations
├── scripts/                   # Phase verification & benchmarking scripts
├── evaluation_report.md       # Full benchmark report (Chapter V deliverable)
├── pyproject.toml             # Project build configuration & dependencies
└── docker-compose.yml         # Container definitions (PostgreSQL + pgvector)
```

---

## 🔭 Limitations & Future Scope

While Orion successfully proves the viability of hybrid structural-semantic drift detection, several architectural enhancements are planned:
1. **Polyglot AST Support:** Universal parsing via Tree-sitter for TypeScript (Jest), Java (JUnit), and Go.
2. **Multi-Tenant Enterprise Architecture:** Multi-workspace schema with OAuth 2.0 (3LO) authentication.
3. **Distributed Task Queue:** Asynchronous event processing via Celery with Redis/RabbitMQ.
4. **Automated Fix PRs:** AI coding agents that propose Pull Requests to auto-update drifted assertions.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
