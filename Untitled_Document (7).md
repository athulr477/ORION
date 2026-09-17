# Orion: AI-Powered Requirements Traceability Matrix (RTM) Engine

```markdown
# ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE
A project report submitted in partial fulfillment of the requirement for the award of the degree of
MASTER OF COMPUTER APPLICATIONS
By
ATHUL RAJ A K (REG NO. [YOUR-REG-NO])
Under the guidance of
[GUIDE NAME], [DESIGNATION]

DEPARTMENT OF COMPUTER APPLICATIONS
ST. JOSEPH'S COLLEGE (AUTONOMOUS), DEVAGIRI, CALICUT
AFFILIATED TO THE UNIVERSITY OF CALICUT
MAY 2026

```

---

```markdown
## PRELIMINARY PAGES

### CERTIFICATE
This is to certify that the project report titled **ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE** submitted by **ATHUL RAJ A K** (Reg. No: [YOUR-REG-NO]) to St. Joseph's College (Autonomous), Devagiri, Calicut in partial fulfillment of the requirements for the award of degree of Master of Computer Applications affiliated to the University of Calicut during the academic year 2024–2026.

Internal Examiner: ____________________          External Examiner: ____________________

### DECLARATION
I hereby declare that the project entitled **ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE** has been undertaken by me for the award of the degree of Master of Computer Applications. I have completed this project under the guidance of [Guide Name], Department of Computer Applications, St. Joseph's College (Autonomous), Devagiri, Calicut.

Place: Calicut  
Date: ____________________                                    ATHUL RAJ A K

### ACKNOWLEDGEMENT
I express my sincere gratitude to Dr. Bobby Jose, Principal, St. Joseph's College (Autonomous), Devagiri, Calicut, for providing the necessary institutional facilities.
I am grateful to [HOD Name], Head of the Department, and [Guide Name], my project supervisor, for their constant technical guidance and review.
I also thank my peers, faculty members, and project collaborators for their support throughout this development.

### SYNOPSIS
Orion is an automated, AI-driven Requirements Traceability Matrix (RTM) governance platform engineered to eliminate silent specification drift between agile product backlogs and continuous integration (CI/CD) test suites[cite: 1]. Modern agile development pipelines suffer from divergence where code assertions fail to validate quantitative acceptance criteria defined in Jira issues. Traditional verification relies on manual audit reviews or rigid keyword matching that fail to identify subtle semantic and structural regressions[cite: 1].

Orion resolves this by implementing a dual-sided hybrid evaluation pipeline combining a 384-dimensional dense semantic embedding model (`BAAI/bge-small-en-v1.5`) running via ONNX Runtime with a deterministic Python Abstract Syntax Tree (AST) structural parser. The platform continuously synchronizes Atlassian Document Format (ADF) user stories from Jira Cloud, converts test files via AST extraction into structured assertion syntax, stores high-dimensional embeddings using PostgreSQL `pgvector`, and computes a composite compliance score[cite: 1]. 

When structural divergence or semantic degradation is identified, Orion generates natural language explanations using an on-premise Large Language Model (Meta Llama 3.1 8B via Ollama) and automatically registers GitHub Check Run annotations to block pull request merges. A real-time executive dashboard built with React and Vite visualizes the complete traceability matrix, surfaces sensitivity threshold controls, and enforces Role-Based Access Control (RBAC).

---

## TABLE OF CONTENTS

- CHAPTER I: INTRODUCTION
  - 1.1 An Overview
  - 1.2 Mission of the Project
  - 1.3 Background Study
    - 1.3.1 Study on Existing System
    - 1.3.2 Disadvantages of Existing System
- CHAPTER II: SYSTEM ANALYSIS
  - 2.1 Study on Proposed System
    - 2.1.1 Advantages of Proposed System
  - 2.2 User Requirement Specification
  - 2.3 Software Requirement Specification
  - 2.4 Feasibility Study
    - 2.4.1 Technical Feasibility
    - 2.4.2 Economic Feasibility
    - 2.4.3 Operational Feasibility
  - 2.5 System Specification
    - 2.5.1 Hardware Specification
    - 2.5.2 Software Specification
    - 2.5.3 Technology Used
  - 2.6 Cost Estimation and Scheduling
    - 2.6.1 Cost Estimation
    - 2.6.2 Scheduling (Gantt Summary)
- CHAPTER III: DESIGN AND DEVELOPMENT PROCESS
  - 3.1 Fundamental Design Concepts
  - 3.2 Design Notations
    - 3.2.1 Data Flow Diagrams (Context, Level 1, Level 1.1, Level 1.2)
    - 3.2.2 Use Case Diagrams
  - 3.3 Design Process
    - 3.3.1 Database Design
    - 3.3.2 Normalization (1NF, 2NF, 3NF)
    - 3.3.3 Input Design
    - 3.3.4 Output Design
  - 3.4 Development Approach (Agile Sprints)
- CHAPTER IV: CODING
  - 4.1 Frontend Architecture (React / Vite)
  - 4.2 Backend Architecture (FastAPI / SQLAlchemy / pgvector)
  - 4.3 AI & Parser Subsystems (BGE-Small ONNX / AST / Ollama Llama 3.1)
- CHAPTER V: TESTING AND IMPLEMENTATION
  - 5.1 Testing Methodologies
    - 5.1.1 Unit Testing
    - 5.1.2 Integration Testing
    - 5.1.3 Validation Testing (Front-End & Back-End)
    - 5.1.4 Test Cases and Results Chart
  - 5.2 Quality Assurance & Policies
    - 5.2.1 Generic Risk Analysis
  - 5.3 System Implementation
    - 5.3.1 Implementation Procedures
  - 5.4 System Maintenance
- CHAPTER VI: CONCLUSION
  - 6.1 Conclusion
  - 6.2 Scope for Further Enhancement
  - 6.3 Bibliography
- ANNEXURE - A: INPUT AND OUTPUT SCREENS
- ANNEXURE - B: ABBREVIATIONS

---

## CHAPTER I: INTRODUCTION

### 1.1 ORION - AN OVERVIEW
Orion is an automated software quality engineering and compliance platform designed to bridge the operational divide between agile product management tools and source code repositories[cite: 1]. By replacing manual spreadsheets with real-time semantic analysis and code AST inspection, Orion delivers an automated Requirements Traceability Matrix (RTM). The platform connects to Jira Cloud via webhook listeners and REST APIs to ingest user stories and acceptance criteria, while simultaneously monitoring GitHub repositories for pull request events modifying test suites.

### 1.2 MISSION OF THE PROJECT
The mission of Orion is to eliminate "silent specification drift"—an issue where unit and integration tests pass successfully in CI/CD pipelines while testing invalid, outdated, or altered performance constraints. 
Key objectives:
1. Parse unstructured and semi-structured acceptance criteria from Jira into machine-evaluable constraint representations.
2. Parse test source code directly using Abstract Syntax Trees (AST) to evaluate explicit assertion checks against requirement parameters without executing unsafe arbitrary test scripts.
3. Deliver a mathematically grounded, dual-sided scoring engine balancing semantic intent ($0.6$) and AST structural conformance ($0.4$).
4. Enforce automated pull request gating through native GitHub Check Runs with precise line-level code annotations.
5. Provide localized, privacy-preserving Explainable AI (XAI) root-cause analysis via an on-premise Meta Llama 3.1 8B model.

### 1.3 BACKGROUND STUDY
In conventional software engineering lifecycles, Requirements Traceability Matrices are constructed manually using documentation platforms or spreadsheets. As development velocity increases through CI/CD pipelines, these artifacts become desynchronized from the actual codebase within days of a release.

#### 1.3.1 Study on Existing System
1. **Atlassian Jira / Xray / Zephyr**: Relies on manual linking between tickets and test cases. Lacks automated inspection of actual assertions within test code.
2. **Static Analysis Linters (SonarQube, Ruff)**: Enforces syntax style, security flaws, and test coverage volume (lines covered), but cannot determine whether the logic asserted satisfies business rules.
3. **Pure LLM Evaluation Agents**: Prone to hallucinations, non-deterministic latency, and high cloud token costs when evaluating thousands of test code lines.

#### 1.3.2 Disadvantages of Existing System
* **High Manual Overhead**: Engineering teams expend significant billable hours manually compiling compliance reports before audits.
* **False Sense of Quality**: 100% test branch coverage can hide broken boundary logic (e.g., asserting `latency <= 200ms` when the requirement states `latency <= 100ms`).
* **Non-Deterministic Governance**: Relying on ad-hoc LLM evaluation prompts leads to inconsistent CI/CD builds.
* **Security & IP Leakage**: Cloud-hosted LLM validators expose proprietary codebases and internal Jira backlog tickets to third-party APIs.

---

## CHAPTER II: SYSTEM ANALYSIS

### 2.1 STUDY ON PROPOSED SYSTEM
The proposed Orion platform creates a real-time, closed-loop verification feedback architecture. It translates unstructured requirement criteria into vector embeddings and quantitative boundary objects, links them to test function AST nodes via `@traces("REQ-ID")` decorators, and persists the relational mappings in PostgreSQL `pgvector`.

#### 2.1.1 Advantages of Proposed System
1. **Deterministic AST Verification**: Structural assertions are validated with mathematical exactness.
2. **Local Edge Inference**: Zero cloud API dependencies; embeddings run on ONNX Runtime and XAI runs on local Ollama instances.
3. **Automated CI/CD Gating**: Directly fails PRs that break specification thresholds.
4. **Transparent Auditability**: Fully auditable relational tables tracking historical changes and overrides.

### 2.2 USER REQUIREMENT SPECIFICATION
The system is divided into two primary human actor modules and one automated system actor[cite: 1]:

#### 1. QA Lead / System Administrator
* **Authentication**: Authenticate via the enterprise role session gate.
* **Matrix Inspection**: View comprehensive traceability matrix across all active sprint tickets.
* **Policy Configuration**: Modify global sensitivity thresholds (`Covered Threshold`, `Drifted Threshold`).
* **Manual Override**: Authorize and document manual risk score overrides with audit logging.
* **Compliance Reporting**: Export verifiable audit trail reports for external certification bodies.

#### 2. Software Developer
* **Authentication**: Login under Developer role with restricted administrative actions.
* **Trace Annotation**: Decorate test functions with `@traces("REQ-KEY")` syntax.
* **Gated Feedback**: Receive line-level annotations and status reports inside GitHub Pull Requests.
* **Local Simulation**: Execute local webhook simulations to pre-validate PR changes against compliance baselines.

#### 3. System / CI Service Actor (Automated)
* Ingests webhooks from Jira Cloud and GitHub App.
* Executes background vector embeddings and AST comparisons.
* Posts Check Runs and updates Jira issue synchronization comments.

### 2.3 SOFTWARE REQUIREMENT SPECIFICATION
* **Operating System**: Linux (Ubuntu 22.04 LTS) / Windows 11 64-bit
* **Runtime Environments**: Python 3.11+ (Backend), Node.js v20+ (Frontend)
* **Backend Framework**: FastAPI (Asynchronous REST API)
* **Database Management System**: PostgreSQL 16 with `pgvector` extension
* **ORM & Migrations**: SQLAlchemy 2.0 with Alembic
* **Vector Model**: `BAAI/bge-small-en-v1.5` (384 dimensions, executed via ONNX Runtime)
* **Local LLM Engine**: Meta Llama 3.1 8B running via Ollama
* **Frontend Framework**: React 18 with Vite, Tailwind CSS, and Lucide-React
* **Testing Stack**: Pytest, Pytest-Asyncio, HTTPX

### 2.4 FEASIBILITY STUDY

#### 2.4.1 Technical Feasibility
Orion relies on production-ready, open-source technologies[cite: 1]. The local embedding model (`bge-small-en-v1.5`) requires ~130MB of RAM and runs inference in sub-30ms intervals on modern CPU threads. AST extraction is native to Python (`import ast`), requiring no external compilers. PostgreSQL with `pgvector` provides indexing via HNSW (Hierarchical Navigable Small World) for vector queries. Thus, the system is technically sound and operational on commodity developer hardware.

#### 2.4.2 Economic Feasibility
By utilizing local open-source models, Orion eliminates recurring API token costs (e.g., OpenAI or Anthropic API billing). Development and operational tooling are entirely open-source (PostgreSQL, FastAPI, React, Ollama, Docker). The hardware infrastructure utilizes existing on-premise developer workstations or internal CI runners, demonstrating economic feasibility.

#### 2.4.3 Operational Feasibility
Orion does not disrupt existing development workflows. Developers write unit and integration tests normally, adding only a lightweight `@traces` decorator. Pull request feedback is posted directly within GitHub Check Runs, allowing engineering teams to adopt the tool without needing to learn a secondary interface for everyday coding tasks.

### 2.5 SYSTEM SPECIFICATION

#### 2.5.1 Hardware Specification
* **Processor**: Intel Core i5 / AMD Ryzen 5 or above (8 physical/logical threads minimum)[cite: 1]
* **RAM**: 16 GB DDR4/DDR5 recommended (minimum 8 GB for lightweight mode)[cite: 1]
* **Storage**: 256 GB NVMe SSD (minimum 5 GB allocated for PostgreSQL vector storage and model weights)[cite: 1]
* **GPU**: Optional (NVIDIA RTX series with CUDA 12 support accelerates local Ollama XAI inference; fallback deterministic template engine operates on pure CPU)[cite: 1]

#### 2.5.2 Software Specification
* **Language/Platform**: Python 3.11, JavaScript (ES6+ / JSX)[cite: 1]
* **Web Server**: Uvicorn (ASGI)[cite: 1]
* **IDE**: Visual Studio Code[cite: 1]
* **Database Client**: pgAdmin 4 / psql[cite: 1]
* **VCS**: Git and GitHub Cloud[cite: 1]

#### 2.5.3 Technology Used
* **Frontend**: React, Vite, Tailwind CSS, Lucide Icons[cite: 1]
* **Backend**: FastAPI, Pydantic v2, SQLAlchemy, HTTPX (Async)[cite: 1]
* **AI & NLP**: Hugging Face Transformers, ONNX Runtime, BGE-Small Embeddings, Ollama (Llama 3.1 8B)[cite: 1]
* **Database**: PostgreSQL 16, pgvector (HNSW Indexing)[cite: 1]

### 2.6 COST ESTIMATION AND SCHEDULING

#### 2.6.1 Cost Estimation
* Hardware Infrastructure (Existing Workstation): ₹85,000[cite: 1]
* Software Tools & Licenses (Open Source): ₹0[cite: 1]
* Cloud API & Token Consumption Costs: ₹0[cite: 1]
* Domain & Webhook Staging Infrastructure: ₹3,500[cite: 1]
* **Total Estimated Cost**: ₹88,500[cite: 1]

#### 2.6.2 Scheduling
* Requirements Gathering & Jira API Integration: 3 Weeks[cite: 1]
* AST Code Parser & Python Grammar Analysis: 3 Weeks[cite: 1]
* Embedding Engine & pgvector Integration: 3 Weeks[cite: 1]
* Hybrid Risk Scoring & Mathematical Validation: 2 Weeks[cite: 1]
* Frontend Matrix Console & RBAC Implementation: 3 Weeks[cite: 1]
* Verification, Ruff Linting & Academic Testing: 2 Weeks[cite: 1]

---

## CHAPTER III: DESIGN AND DEVELOPMENT PROCESS

### 3.1 FUNDAMENTAL DESIGN CONCEPTS
1. **Abstraction**: Separates raw test syntax into abstracted relational assertion models[cite: 1].
2. **Modularity**: Individual modules (Jira Ingestion, AST Extractor, Vector Scorer, Gating Controller) operate as decoupled microservices or standalone Python packages[cite: 1].
3. **Information Hiding**: Database connections and GitHub App private keys (`.pem`) are encapsulated within isolated utility layers[cite: 1].
4. **Data Structure**: Standardized Pydantic schemas enforce schema validation across ingestion pipelines[cite: 1].

### 3.2 DESIGN NOTATIONS

#### 3.2.1 Data Flow Diagrams (Calicut University Academic Format)

##### Level 0: Context Level DFD

```

+------------------+
|    Jira Cloud    |--------+
+------------------+        |
| (ADF Issue Payloads)
+------------------+        v
|   GitHub CI/CD   |<=============> (( 0.0 ORION RTM )) <===> [( PostgreSQL + pgvector )]
+------------------+   (PR Check Runs/       ENGINE
Diffs)
+------------------+        ^
|  QA Lead / Admin |--------+ (Configuration / Overrides)
+------------------+        |
|
+------------------+        |
|Software Developer|--------+ (PR Submissions / Inspections)
+------------------+

```

##### Level 1: System Level DFD
* **Process 1.0**: Requirement Ingestion (Jira Cloud $\rightarrow$ Plaintext/Constraints $\rightarrow$ `D1: requirements`)[cite: 1]
* **Process 2.0**: AST Code Extraction (GitHub Code $\rightarrow$ AST Tree $\rightarrow$ `D2: test_cases`)[cite: 1]
* **Process 3.0**: Dual-Sided Risk Engine (`D1` + `D2` $\rightarrow$ Composite Score $\rightarrow$ `D3: trace_links`)[cite: 1]
* **Process 4.0**: XAI Verbalization Engine (`D3` $\rightarrow$ Natural Language Summary $\rightarrow$ `D4: audit_logs`)[cite: 1]
* **Process 5.0**: CI/CD Gating & Visualization (`D3` + `D4` $\rightarrow$ React UI & GitHub Checks API)[cite: 1]

##### Level 1.1: QA Lead / Admin Decomposition
* **Actor**: `QA Lead / Admin`[cite: 1]
* **Processes**:
  * 1.1.1: Login / Role Session Gate[cite: 1]
  * 1.1.2: View Traceability Matrix[cite: 1]
  * 1.1.3: Update Sensitivity Thresholds[cite: 1]
  * 1.1.4: Execute Risk Override[cite: 1]
  * 1.1.5: View XAI Drift Audit Logs[cite: 1]
* **Data Stores**: `[ 1 | requirements ]`, `[ 2 | test_cases ]`, `[ 3 | trace_links ]`, `[ 4 | audit_logs ]`[cite: 1]

##### Level 1.2: Software Developer Decomposition
* **Actor**: `Software Developer`[cite: 1]
* **Processes**:
  * 1.2.1: Login / Role Session Gate[cite: 1]
  * 1.2.2: Inspect Line Annotations[cite: 1]
  * 1.2.3: View Matrix Status (Read-Only)[cite: 1]
  * 1.2.4: Trigger Webhook Simulation[cite: 1]
* **Data Stores**: `[ 2 | test_cases ]`, `[ 3 | trace_links ]`, `[ 4 | audit_logs ]`[cite: 1]

#### 3.2.2 Use Case Diagram
* **Actors**: QA Lead / Admin, Software Developer, Jira Service Actor, GitHub Service Actor[cite: 1].
* **Use Cases**:
  * `Authenticate Session`[cite: 1]
  * `Synchronize Jira Specifications`[cite: 1]
  * `Extract AST Assertions`[cite: 1]
  * `Compute Composite Risk Score`[cite: 1]
  * `Configure Sensitivity Thresholds` (QA Lead Only)[cite: 1]
  * `Override Traceability Link` (QA Lead Only)[cite: 1]
  * `View Natural Language XAI Evidence`[cite: 1]
  * `Post GitHub PR Check Run Annotations`[cite: 1]

### 3.3 DESIGN PROCESS

#### 3.3.1 Database Design
Orion uses a normalized relational schema with vector embeddings stored using PostgreSQL `pgvector`[cite: 1].

##### Table 3.1: `requirements` Table
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique requirement record identifier[cite: 1] |
| `external_key` | VARCHAR(50) | UNIQUE, NOT NULL | Jira Issue Key (e.g., `CORE-142`)[cite: 1] |
| `title` | VARCHAR(255) | NOT NULL | Requirement Summary / Title[cite: 1] |
| `description` | TEXT | NULLABLE | Parsed acceptance criteria body[cite: 1] |
| `extracted_constraints`| JSONB | NOT NULL | Quantitative constraint dictionary[cite: 1] |
| `embedding` | VECTOR(384) | NOT NULL | BGE-small dense embedding[cite: 1] |
| `created_at` | TIMESTAMP | NOT NULL | Record creation timestamp[cite: 1] |

##### Table 3.2: `test_cases` Table
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique test case identifier[cite: 1] |
| `file_path` | VARCHAR(255) | NOT NULL | Repository relative file path[cite: 1] |
| `function_name` | VARCHAR(128) | NOT NULL | Name of test function[cite: 1] |
| `target_requirement` | VARCHAR(50) | NOT NULL | Traced Jira key from `@traces`[cite: 1] |
| `assertions` | JSONB | NOT NULL | Extracted AST assertion rules[cite: 1] |
| `embedding` | VECTOR(384) | NOT NULL | BGE-small dense embedding[cite: 1] |
| `updated_at` | TIMESTAMP | NOT NULL | Last parsed timestamp[cite: 1] |

##### Table 3.3: `trace_links` (`traceability_matrix`) Table
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique link identifier[cite: 1] |
| `requirement_id` | UUID | FK -> `requirements.id` | Target requirement foreign key[cite: 1] |
| `test_case_id` | UUID | FK -> `test_cases.id` | Target test case foreign key[cite: 1] |
| `semantic_score` | FLOAT | NOT NULL | Cosine similarity score ($0.0 - 1.0$)[cite: 1] |
| `structural_score` | FLOAT | NOT NULL | AST comparator match ($0.0 - 1.0$)[cite: 1] |
| `risk_score` | FLOAT | NOT NULL | $0.6 \cdot \text{sem} + 0.4 \cdot \text{struct}$[cite: 1] |
| `status` | VARCHAR(20) | NOT NULL | `COVERED`, `PARTIAL`, `DRIFTED`[cite: 1] |
| `is_overridden` | BOOLEAN | DEFAULT FALSE | Administrative override flag[cite: 1] |

##### Table 3.4: `audit_logs` Table
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique log identifier[cite: 1] |
| `trace_link_id` | UUID | FK -> `trace_links.id` | Associated matrix link[cite: 1] |
| `actor` | VARCHAR(64) | NOT NULL | Responsible username or system service[cite: 1] |
| `action` | VARCHAR(64) | NOT NULL | Action executed[cite: 1] |
| `xai_explanation` | TEXT | NULLABLE | Ollama generated drift summary[cite: 1] |
| `created_at` | TIMESTAMP | NOT NULL | Timestamp of audit entry[cite: 1] |

#### 3.3.2 Normalization
The database schema is normalized to Third Normal Form (3NF)[cite: 1]:
* **1NF**: Every table column holds atomic values; vector embeddings are stored in native vector primitives without composite lists[cite: 1].
* **2NF**: All non-key attributes are fully functionally dependent on primary keys (`UUID`), removing partial dependencies[cite: 1].
* **3NF**: Transitive functional dependencies are eliminated by separating test extraction details and audit logs into foreign-key-linked tables[cite: 1].

### 3.4 DEVELOPMENT APPROACH (AGILE SPRINTS)
Orion was built using the Agile methodology across four distinct iterations[cite: 1]:
* **Sprint 1**: Backend API scaffolding, Jira webhook listener, and PostgreSQL `pgvector` configuration[cite: 1].
* **Sprint 2**: Python AST Parser construction and BGE-Small ONNX vector pipeline integration[cite: 1].
* **Sprint 3**: GitHub App Check Run integration, Ollama XAI synthesis, and risk engine tuning[cite: 1].
* **Sprint 4**: React frontend dashboard, RBAC session gating, Ruff linting, and verification suites[cite: 1].

---

## CHAPTER IV: CODING

### 4.1 FRONTEND ARCHITECTURE
The frontend is constructed using React and Vite, implementing modular state management and an enterprise dark theme[cite: 1].
* `App.jsx`: Root component hosting the active session state (`currentUser`) and coordinating view updates.
* `LoginModal.jsx`: Session modal enforcing RBAC role selection (`QA Lead` vs. `Developer`).
* `MatrixTable.jsx`: RTM table with search filtering, status badging, and role-locked override buttons.
* `StatsBar.jsx`: Executive statistics bar displaying live aggregate counts and average confidence scores.
* `SensitivitySliders.jsx`: Dual-range sliders allowing QA Leads to adjust classification boundaries dynamically.

### 4.2 BACKEND ARCHITECTURE
* `orion/app.py`: FastAPI initialization, CORS middleware registration, and top-level router mounting.
* `orion/github/webhook.py`: HMAC signature verification (`X-Hub-Signature-256`) and PR event handling.
* `orion/github/auth.py`: Asynchronous token exchange (`httpx.AsyncClient`) using GitHub App RSA private key credentials.
* `orion/ingestion/service.py`: Relational database operations managing atomic upserts of test suites and requirements.

### 4.3 AI & PARSER SUBSYSTEMS
* `orion/extraction/ast_parser.py`: Traverses Python test files using `ast.NodeVisitor` to extract `@traces` keys, assertion targets, operators, and expected values.
* `orion/extraction/embedding.py`: Loads `BAAI/bge-small-en-v1.5` via ONNX Runtime to generate normalized 384-dimensional dense vectors.
* `orion/scoring/engine.py`: Computes the composite compliance score:
  $$\text{Composite Risk} = 0.6 \cdot \text{CosineSimilarity} + 0.4 \cdot \text{StructuralAssertionMatch}$$
* `orion/xai/explainer.py`: Local Ollama interface prompting Llama 3.1 8B with structured diff contexts; includes deterministic fallback templates.

---

## CHAPTER V: TESTING AND IMPLEMENTATION

### 5.1 TESTING METHODOLOGY
The Orion platform underwent rigorous automated and manual test verification[cite: 1].

#### 5.1.1 Unit Testing
* Verified AST visitor logic on multiple syntax branches (comparison operators, membership operations, multi-assert blocks)[cite: 1].
* Verified cosine similarity calculations against known vector baselines[cite: 1].

#### 5.1.2 Integration Testing
* Verified end-to-end Jira webhook parsing, embedding generation, and `pgvector` persistence[cite: 1].
* Tested GitHub App JWT generation and authenticated Check Run creation[cite: 1].

#### 5.1.3 Validation Testing
* **Front-End Validation**: Input forms ensure valid search strings, numeric threshold boundaries ($0 \le \text{drift} < \text{covered} \le 100$), and role toggling[cite: 1].
* **Back-End Validation**: Pydantic models validate incoming webhook JSON payloads, rejecting malformed structures[cite: 1].

#### 5.1.4 Test Cases and Results Chart
| Test Case ID | Component / Module | Test Scenario | Input Data | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | RBAC Session | Developer Role Restriction | Role: `Software Developer` | Override buttons & sliders disabled | Controls locked with tooltip | PASS[cite: 1] |
| **TC-02** | AST Extraction | Extract `@traces` Decorator | `test_auth.py` with `@traces("CORE-142")` | Parsed requirement key: `CORE-142` | Extracted successfully | PASS[cite: 1] |
| **TC-03** | Risk Engine | Covered State Evaluation | Semantic: 0.78, Struct: 1.0 | Score $\ge 0.75$, Status: `COVERED` | Risk: 0.86, `COVERED` | PASS[cite: 1] |
| **TC-04** | Risk Engine | Drifted State Detection | SLA: 100ms, Assert: 200ms | Score $< 0.40$, Status: `DRIFTED` | Risk: 0.38, `DRIFTED` | PASS[cite: 1] |
| **TC-05** | CI/CD Gating | GitHub Check Run Posting | Status: `DRIFTED` | Check Run created with `failure` status | Merge blocked with annotation | PASS[cite: 1] |
| **TC-06** | XAI Engine | Ollama Llama 3.1 Fallback | Ollama daemon stopped | Fallback to deterministic template | Audit log populated cleanly | PASS[cite: 1] |

### 5.2 QUALITY ASSURANCE & POLICIES
Code quality across all Python modules was enforced via the Ruff linter against PEP 8 standards[cite: 1]. Zero blocking lint errors or unused imports were permitted in production code paths.

#### 5.2.1 Generic Risk Analysis
* **Schedule Risk**: Mitigated by prioritizing the four core enterprise test tickets (`CORE-142` to `CORE-145`)[cite: 1].
* **Technical Risk (Ollama Latency)**: Mitigated by implementing deterministic text templates when LLM execution exceeds timeout limits[cite: 1].
* **Security Risk (Webhook Forgery)**: Mitigated by validating GitHub HMAC SHA-256 signatures[cite: 1].

### 5.3 SYSTEM IMPLEMENTATION

#### 5.3.1 Implementation Procedures
* **Database Migration**: Applied via Alembic to PostgreSQL `orion_db`[cite: 1].
* **Backend Bootstrapping**: Executed via Uvicorn ASGI workers[cite: 1].
* **Frontend Bootstrapping**: Built and bundled via Vite[cite: 1].
* **Direct Conversion**: The automated pipeline was validated against historical manual spreadsheets, confirming matching compliance outputs[cite: 1].

### 5.4 SYSTEM MAINTENANCE
* **Corrective Maintenance**: Resolving AST parse errors for unhandled edge-case Python syntax[cite: 1].
* **Adaptive Maintenance**: Updating Jira REST API client to support Atlassian schema modifications[cite: 1].
* **Perfective Maintenance**: Adding multi-language AST support (e.g., JavaScript/Jest)[cite: 1].

---

## CHAPTER VI: CONCLUSION

### 6.1 CONCLUSION
The Orion platform demonstrates an automated approach to maintaining agile software compliance[cite: 1]. By replacing manual spreadsheets with an AST code inspection engine and local vector embeddings, the system eliminates silent specification drift within active CI/CD pipelines[cite: 1]. Empirical testing across enterprise test tickets confirmed sub-30ms parsing and classification times, while local Ollama XAI integration provided root-cause analysis without exposing code to cloud APIs[cite: 1]. The integration of role-based gating and GitHub Check Runs delivers a production-grade governance platform satisfying all MCA project objectives[cite: 1].

### 6.2 SCOPE FOR FURTHER ENHANCEMENT
1. **Multi-Language AST Support**: Expand the parser beyond Python to inspect TypeScript/Jest, Java/JUnit, and Go test suites[cite: 1].
2. **Distributed Redis Caching**: Migrate the in-memory GitHub App installation token cache to Redis for multi-worker deployments[cite: 1].
3. **Automated Assertion Synthesis**: Integrate local LLM agents to suggest code patches directly within GitHub PR reviews to resolve detected drifts[cite: 1].
4. **Bidirectional Constraint Syncing**: Allow updates in unit test constants to update Jira acceptance criteria when approved by QA Leads[cite: 1].

### 6.3 BIBLIOGRAPHY
1. Atlassian. (2024). *Atlassian Document Format (ADF) Specifications*. Atlassian Developer Documentation[cite: 1].
2. Python Software Foundation. (2024). *The AST Module: Abstract Syntax Trees*. Python 3 Documentation[cite: 1].
3. Xiao, S., Liu, Z., Zhang, P., & Muennighoff, N. (2023). *C-Pack: Packaged Resources to Advance General Chinese Embedding*. arXiv preprint arXiv:2309.07597 (BGE Models)[cite: 1].
4. AI @ Meta. (2024). *The Llama 3 Herd of Models*. Meta Research[cite: 1].
5. PostgreSQL Global Development Group. (2024). *pgvector: Open-source vector similarity search for PostgreSQL*[cite: 1].
6. Pressman, R. S., & Maxim, B. R. (2020). *Software Engineering: A Practitioner's Approach* (9th ed.). McGraw-Hill[cite: 1].

---

## ANNEXURE - A: INPUT AND OUTPUT DESIGN

### MAJOR INPUT SCREENS
1. **Authentication Session Modal**: Provides user role selection (`QA Lead / Administrator` or `Software Developer`) and username entry[cite: 1].
2. **Policy Configuration Controls**: Dual-range sliders for setting `Covered` and `Drifted` sensitivity percentage thresholds[cite: 1].
3. **Webhook Simulation Trigger**: Modal interface allowing engineers to test incoming GitHub pull request events[cite: 1].

### MAJOR OUTPUT SCREENS
1. **Traceability Matrix Heatmap**: Interactive data grid displaying requirement IDs, summary text, linked test functions, semantic similarity, structural match, composite risk score, and status badges (`COVERED`, `PARTIAL`, `DRIFTED`)[cite: 1].
2. **XAI Drift Diagnosis Modal**: Grounded natural language summary identifying discrepancies between Jira criteria and test assertions[cite: 1].
3. **GitHub Check Run Gating Summary**: Pull request interface showing passing or blocked merge status with line-level annotations[cite: 1].

---

## ANNEXURE - B: ABBREVIATIONS
* **ADF**: Atlassian Document Format[cite: 1]
* **AI**: Artificial Intelligence[cite: 1]
* **API**: Application Programming Interface[cite: 1]
* **AST**: Abstract Syntax Tree[cite: 1]
* **CI/CD**: Continuous Integration / Continuous Deployment[cite: 1]
* **DFD**: Data Flow Diagram[cite: 1]
* **FK**: Foreign Key[cite: 1]
* **HMAC**: Hash-based Message Authentication Code[cite: 1]
* **LLM**: Large Language Model[cite: 1]
* **ONNX**: Open Neural Network Exchange[cite: 1]
* **ORM**: Object Relational Mapping[cite: 1]
* **PK**: Primary Key[cite: 1]
* **PR**: Pull Request[cite: 1]
* **RBAC**: Role-Based Access Control[cite: 1]
* **REST**: Representational State Transfer[cite: 1]
* **RTM**: Requirements Traceability Matrix[cite: 1]
* **SLA**: Service Level Agreement[cite: 1]
* **SRS**: Software Requirement Specification[cite: 1]
* **UI**: User Interface[cite: 1]
* **UUID**: Universally Unique Identifier[cite: 1]
* **XAI**: Explainable Artificial Intelligence[cite: 1]

```

---

## Antigravity Document Generation Prompt

Run this in Antigravity using **Gemini 3.8 Flash (High)** so it creates your report file without modifying any backend or frontend code:

```markdown
Task: Autonomously compile a complete, publication-ready Word Document (.docx) of the MCA Final Project Report for the "Orion" project, adhering strictly to the Calicut University / Stokiee format guidelines.

Execution Rules & Boundaries:
1. Output Location: Save the output document in a dedicated documentation directory: `docs/report/Orion_MCA_Final_Project_Report.docx`.
2. Do NOT alter, refactor, or delete any source code inside `orion/`, `frontend/`, `tests/`, or `scripts/`.
3. Report Structure & Formatting:
   - Paper Size: A4 with standard margins (Left: 1.5 inches, Right/Top/Bottom: 1.0 inch).
   - Typography: Times New Roman (Body text: 12pt, 1.5 line spacing, Justified; Headings: 14pt/16pt Bold).
   - Preliminary Pages: Cover Page, Certificate, Declaration, Acknowledgement, Synopsis, Table of Contents.
   - Chapter Breakdown:
     * Chapter I: Introduction (Overview, Mission, Background Study, Existing vs. Proposed System).
     * Chapter II: System Analysis (Proposed Advantages, User & Software Specs, Feasibility Study, Hardware/Software Specs, Cost Estimation & Gantt Scheduling).
     * Chapter III: Design and Development Process (Fundamental Concepts, Data Flow Diagrams from Level 0 to Level 1.2, Use Case Diagram, Database Schema Tables with 3NF Normalization, Input/Output Design, Agile Development Approach).
     * Chapter IV: Coding (Frontend Architecture, Backend Architecture, AI & AST Parsing Subsystems).
     * Chapter V: Testing and Implementation (Unit, Integration, Validation Testing, Test Chart, Generic Risks, Implementation & Maintenance Procedures).
     * Chapter VI: Conclusion (System Evaluation, Scope for Further Enhancement, Formal Academic Bibliography).
     * Annexure A & B: Input/Output Design Descriptions & Complete Abbreviations Table.
4. Diagram & Screenshot Embedding:
   - Pull the generated vector DFD diagrams from `docs/diagrams/dfd/` and embed them into Chapter III (Figures 3.1 through 3.6).
   - Reference the dashboard UI screens for Annexure-A.
5. Content Source:
   - Use the complete technical markdown specification provided in the workspace context, ensuring all mathematical formulas (e.g., Convex Risk Combination formula), database tables, and architecture profiles are formatted cleanly.

Please generate the `.docx` report file now.

```