# ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE
A PROJECT REPORT
Submitted in partial fulfillment of the requirement for the award of the degree of
MASTER OF COMPUTER APPLICATIONS
By
ATHUL RAJ A K (Reg. No: SJC24MCA015)
NAJVA C (Reg. No: SJC24MCA022)

Under the guidance of
Ms. DEEPA RAMACHANDRAN
Assistant Professor, Dept. of Computer Applications

DEPARTMENT OF COMPUTER APPLICATIONS
ST. JOSEPH'S COLLEGE (AUTONOMOUS), DEVAGIRI, CALICUT
AFFILIATED TO THE UNIVERSITY OF CALICUT
MAY 2026

================================================================================
ST. JOSEPH'S COLLEGE (AUTONOMOUS), DEVAGIRI, CALICUT
DEPARTMENT OF COMPUTER APPLICATIONS

CERTIFICATE - I (COLLEGE SUBMISSION)
This is to certify that the project report titled "ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE" is a bona fide record of project work done by ATHUL RAJ A K (Reg. No: SJC24MCA015) and NAJVA C (Reg. No: SJC24MCA022) during the academic year 2024–2026 in partial fulfillment of the requirements for the award of the degree of Master of Computer Applications affiliated to the University of Calicut.

Dr. Bobby Jose                      [HOD Name]                    Ms. Deepa Ramachandran
Principal                           Head of the Department        Project Guide
College Seal

================================================================================
CERTIFICATE - II (EXAMINATION ENDORSEMENT)
This is to certify that the project report titled "ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE" submitted by ATHUL RAJ A K and NAJVA C has been evaluated during the Viva-Voce examination held on _______________.

Internal Examiner: _______________________          External Examiner: _______________________

================================================================================
DECLARATION
We hereby declare that the project entitled "ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE" has been undertaken by us for the award of the degree of Master of Computer Applications. We have completed this project under the guidance of Ms. Deepa Ramachandran, Department of Computer Applications, St. Joseph's College (Autonomous), Devagiri, Calicut.

Place: Calicut
Date: _______________                                ATHUL RAJ A K (Reg. No: SJC24MCA015)
                                                    NAJVA C (Reg. No: SJC24MCA022)

================================================================================
CERTIFICATE - III (GUIDE APPROVAL)
This is to certify that the project report titled "ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE" is a record of project work done by ATHUL RAJ A K and NAJVA C during the academic year 2024–2026 under my guidance and supervision in partial fulfillment of the requirements for the degree of Master of Computer Applications.

Place: Devagiri, Calicut
Date: _______________                                Ms. Deepa Ramachandran (Project Guide)

================================================================================
ACKNOWLEDGEMENT
We wish to express our sincere gratitude to Dr. Bobby Jose, Principal, St. Joseph's College (Autonomous), Devagiri, Calicut for providing all necessary administrative and laboratory facilities for completing our project.
We are deeply thankful to [HOD Name], Head of the Department of Computer Applications, as well as Ms. Deepa Ramachandran, our internal supervisor, for continuous guidance, technical reviews, and constant encouragement.
We also express our indebtedness to our parents, family members, and friends for their enduring patience and support throughout our postgraduate studies.

ATHUL RAJ A K
NAJVA C

================================================================================
SYNOPSIS
Orion is an enterprise-grade automated software quality assurance and governance platform designed to eliminate silent specification drift between agile requirements management backlogs (Jira Cloud) and automated continuous integration test suites (GitHub / pytest). Modern software engineering workflows face a critical vulnerability: automated unit and integration tests often pass green in CI/CD builds even after business logic and quantitative performance boundaries have evolved in the backlog, leaving the production release exposed to silent non-compliance.

To resolve this challenge, Orion implements a dual-sided hybrid evaluation architecture. It combines a 384-dimensional dense semantic embedding engine (BAAI/bge-small-en-v1.5 executed locally via ONNX Runtime) with a deterministic Python Abstract Syntax Tree (AST) parser. The system ingests Atlassian Document Format (ADF) user stories and acceptance criteria via webhooks, parses test function assertions, maps them using `@traces("REQ-ID")` decorators, and persists relational data and dense vectors into PostgreSQL using the pgvector extension. 

Orion computes a composite risk index: S_hybrid = 0.6 · S_sem + 0.4 · S_struct. When structural mismatches or semantic degradation fall below configurable thresholds, Orion invokes an on-premise Large Language Model (Meta Llama 3.1 8B via Ollama) to synthesize plain-English root-cause explanations, and registers a GitHub Check Run on the developer's pull request to halt unauthorized merging. A modern React and Vite executive dashboard provides QA Leads and Developers with real-time visibility, dynamic sensitivity threshold calibration, and Role-Based Access Control (RBAC).

================================================================================
TABLE OF CONTENTS
CHAPTER I: INTRODUCTION ..................................................... 1
  1.1 An Overview ........................................................... 1
  1.2 Mission of the Project ................................................ 3
  1.3 Background Study ...................................................... 5
      1.3.1 Study on Existing Systems ....................................... 6
      1.3.2 Disadvantages of Existing Systems ............................... 8

CHAPTER II: SYSTEM ANALYSIS ................................................. 10
  2.1 Study on Proposed System .............................................. 10
      2.1.1 Advantages of Proposed System ................................... 11
  2.2 User Requirement Specification ........................................ 13
  2.3 Software Requirement Specification .................................... 16
  2.4 Feasibility Study ..................................................... 18
      2.4.1 Technical Feasibility ........................................... 18
      2.4.2 Economic Feasibility ............................................ 20
      2.4.3 Operational Feasibility ......................................... 21
  2.5 System Specification .................................................. 22
      2.5.1 Hardware Specification .......................................... 22
      2.5.2 Software Specification .......................................... 23
      2.5.3 Technology Used ................................................. 24
  2.6 Cost Estimation and Scheduling ........................................ 26
      2.6.1 Cost Estimation ................................................. 26
      2.6.2 Scheduling (Gantt Milestones) ................................... 27

CHAPTER III: DESIGN AND DEVELOPMENT PROCESS ................................. 29
  3.1 Fundamental Design Concepts ........................................... 29
  3.2 Design Notations & Diagrams ........................................... 32
      3.2.1 Data Flow Diagrams (Context, Level 1.1, Level 1.2) .............. 32
      3.2.2 Use Case Diagrams ............................................... 39
  3.3 Design Process ........................................................ 42
      3.3.1 Database Design (Full Tables 3.1 - 3.8) ......................... 43
      3.3.2 Normalization (1NF, 2NF, 3NF) ................................... 49
      3.3.3 Input Design .................................................... 51
      3.3.4 Output Design ................................................... 52
  3.4 Development Approach (Agile Sprints) .................................. 54

CHAPTER IV: CODING .......................................................... 57
  4.1 Frontend Architecture (React / Vite) .................................. 57
  4.2 Backend Architecture (FastAPI / SQLAlchemy / pgvector) ................ 60
  4.3 AI & Parser Subsystems (BGE-Small / AST / Ollama Llama 3.1) ........... 63

CHAPTER V: TESTING AND IMPLEMENTATION ....................................... 66
  5.1 Testing Methodologies ................................................. 66
      5.1.1 Manual Testing vs Automation Testing ............................ 66
      5.1.2 Unit, Integration & Validation Testing .......................... 69
      5.1.3 Comprehensive Test Chart ........................................ 72
  5.2 Quality Assurance & Policies .......................................... 74
      5.2.1 Generic Risks (Schedule, Budget, Operational, Tech, Programmatic) 75
  5.3 System Implementation ................................................. 78
      5.3.1 Implementation Procedures (Parallel, Direct, Pilot) ............. 78
  5.4 System Maintenance (Corrective, Adaptive, Perfective, Preventive) ..... 80

CHAPTER VI: CONCLUSION ...................................................... 83
  6.1 Conclusion ............................................................ 83
  6.2 Scope for Further Enhancement ......................................... 85
  6.3 Bibliography .......................................................... 88

ANNEXURE - A: INPUT AND OUTPUT DESIGN (FULL FIGURES) ........................ 91
ANNEXURE - B: TABLE OF ABBREVIATIONS ........................................ 98

================================================================================
CHAPTER I: INTRODUCTION

1.1 ORION – AN OVERVIEW
In the modern software development lifecycle, rapid iteration and continuous deployment are paramount. Agile methodologies encourage frequent requirement changes, user story refinements, and immediate code pushes. However, this high development velocity introduces a critical breakdown in software quality governance: Requirements Traceability Matrices (RTMs) are rarely maintained in real time. 

Traditionally, an RTM is a tabular artifact connecting high-level business specifications to the automated tests verifying them. When constructed manually using spreadsheets or static documentation wikis, the matrix rapidly becomes obsolete. Test suites in Continuous Integration (CI) continue to execute and pass green, despite no longer reflecting updated quantitative business parameters—a phenomenon termed "silent specification drift."

Orion is an automated, AI-driven Requirements Traceability and Verification Governance Engine developed to eliminate this gap. Operating as an event-driven intermediary between Jira Cloud and GitHub, Orion continuously ingests agile requirements, parses source code test assertions directly using Python Abstract Syntax Trees (AST), embeds specifications into 384-dimensional dense vector spaces, and calculates mathematically verified compliance risk scores. By integrating directly into pull requests via GitHub Check Runs, Orion prevents the merge of code that silently violates business constraints.

1.2 MISSION OF THE PROJECT
The mission of Orion is to democratize and automate continuous software compliance across enterprise engineering teams. By transforming static documentation into active CI/CD governance gates, Orion achieves five core missions:
1. Automated Requirement Normalization: Ingest semi-structured Jira Atlassian Document Format (ADF) user stories and extract formal quantitative boundary rules (e.g., latency limits, error codes, payload sizes).
2. Deterministic AST Verification: Inspect test logic directly from code syntax trees without running unsafe code, extracting exact assertion operators and target literals.
3. Dual-Sided Hybrid Risk Scoring: Overcome the blind spots of dense semantic embeddings by pairing cosine similarity (0.6) with deterministic structural overlap (0.4).
4. Explainable Local AI Feedback: Employ an on-premise Large Language Model (Meta Llama 3.1 8B via Ollama) to translate complex AST-requirement diffs into plain-English root-cause explanations without cloud data leakage.
5. Continuous Enforcement & Visibility: Enforce pull request gating via the GitHub Checks API and present an executive real-time matrix heatmap on a React/Vite dashboard.

1.3 BACKGROUND STUDY
Software compliance and verification are formalized under international standards such as ISO/IEC/IEEE 29148:2018. While safety-critical systems (aerospace, automotive, medical devices) mandate strict traceability, commercial agile development teams struggle with manual overhead.

1.3.1 Study on Existing Systems
1. Manual Test Management Tools (e.g., Xray, Zephyr, TestRail): Require QA engineers to manually associate Jira ticket keys with test IDs. They track execution status (Pass/Fail) but cannot verify whether the test assertion validates the actual criteria.
2. Code Coverage Profilers (e.g., SonarQube, Coverage.py): Measure the percentage of source code lines executed during test runs. However, high code coverage can be misleading; a test asserting `latency <= 500ms` achieves 100% statement coverage even when the Jira ticket requires `latency <= 100ms`.
3. Cloud-Hosted Generative AI Reviewers: Tools relying on public cloud LLM APIs incur per-token operational costs, introduce non-deterministic review latency, and present major intellectual property and data-privacy risks for proprietary codebases.

1.3.2 Disadvantages of Existing Systems
• Laborious Manual Maintenance: Engineers spend dozens of hours manually assembling RTM spreadsheets before release audits.
• Blindness to Assertion Drift: Existing linters and test runners cannot detect when an assertion boundary has been loosened.
• Cloud Data Exposure: Sending internal requirements and proprietary source code to external AI APIs violates enterprise security guidelines.
• Lack of Real-Time Enforcement: Audits occur weeks after code has already been deployed to production environments.

================================================================================
CHAPTER II: SYSTEM ANALYSIS

2.1 STUDY ON PROPOSED SYSTEM
Orion is engineered as an automated, non-invasive traceability and compliance platform. It introduces zero disruption to developer habits: developers write tests normally, tagging functions with `@traces("REQ-ID")`. When code is pushed, Orion intercepts the webhook, parses the AST structure, computes semantic embeddings via ONNX Runtime, and evaluates the composite score in sub-30ms execution windows.

2.1.1 Advantages of Proposed System
1. Real-Time Drift Detection: Identifies quantitative discrepancies at the exact moment a pull request is submitted.
2. Zero Cloud Dependency & Cost: Utilizes local embedding models (`bge-small-en-v1.5`) and local LLM runtimes (Ollama).
3. Non-Invasive AST Parsing: Extracts verification logic without executing untrusted test code or setting up execution sandboxes.
4. Objective Verification: The hybrid formula prevents semantic models from being tricked by contradictory sentences that share similar vocabulary.
5. Role-Based Governance: Establishes clear separation of concerns between QA Leads (policy adjustment, manual override) and Developers (code inspection).

2.2 USER REQUIREMENT SPECIFICATION
The functional requirements of Orion are segmented across three system actors:
1. QA Lead / Administrator
• Authenticate through the role-gated session interface.
• Inspect the holistic Requirements Traceability Matrix and real-time confidence scores.
• Adjust global sensitivity thresholds dynamically via dashboard sliders.
• Execute manual risk overrides with mandatory audit justification logging.
• Export certified audit reports for external regulatory compliance.
2. Software Developer
• Authenticate in Developer mode with restricted administrative capabilities.
• Trace unit tests to user stories using the `@traces("REQ-ID")` decorator.
• View GitHub Check Run status, failure annotations, and line-level assertion errors.
• Review natural-language XAI explanations detailing why a test drifted from acceptance criteria.
• Trigger simulated pull request webhooks for local pre-flight compliance checks.
3. System / CI Service Actor (Automated)
• Ingest Jira Cloud webhooks and extract ADF criteria into PostgreSQL.
• Ingest GitHub pull request webhooks, retrieve code diffs, and construct ASTs.
• Execute the hybrid scoring formula and update the `traceability_matrix` database table.
• Dispatch pass/fail conclusions to the GitHub Checks API and post audit comments to Jira.

2.3 SOFTWARE REQUIREMENT SPECIFICATION
• Operating System: Windows 11 (64-bit) / Linux Ubuntu 22.04 LTS
• Web Server & API Framework: FastAPI 0.115+ running on Uvicorn ASGI
• Database Management System: PostgreSQL 16 with `pgvector` extension
• Object Relational Mapper (ORM): SQLAlchemy 2.0 with Alembic schema migrations
• Local Embedding Engine: BAAI/bge-small-en-v1.5 via ONNX Runtime (384-dimensional dense vectors)
• Local Explainable AI Engine: Meta Llama 3.1 8B executed via Ollama local daemon
• Frontend Development: React 18, Vite build tool, Tailwind CSS, Lucide Icons
• Python Testing Framework: Pytest, HTTPX AsyncClient

2.4 FEASIBILITY STUDY
2.4.1 Technical Feasibility
The technologies selected for Orion are mature and fully production-ready. The AST module is native to Python's standard library. ONNX Runtime provides optimized CPU inference for `bge-small`, taking only ~26ms per pair and consuming less than 150MB of system RAM. PostgreSQL `pgvector` efficiently handles vector indexing via HNSW algorithms. The system is completely feasible on standard developer hardware.
2.4.2 Economic Feasibility
By adopting open-source runtimes and local edge models, Orion incurs zero cloud API subscription costs. The required infrastructure utilizes existing development workstations and internal servers, resulting in minimal capital expenditure.
2.4.3 Operational Feasibility
Developers continue using standard Git workflows and pytest frameworks without altering their daily routines. QA Leads interact with a clean web interface that automates spreadsheet generation. Operational acceptance is exceptionally high due to the reduction of manual administrative burdens.

2.5 SYSTEM SPECIFICATION
2.5.1 Hardware Specification
• Processor: Intel Core i5 / AMD Ryzen 5 or above (8 physical/logical threads minimum)
• RAM: 16 GB DDR4/DDR5 recommended (8 GB minimum)
• Hard Disk: 256 GB NVMe SSD (minimum 5 GB dedicated for pgvector storage and model weights)
• Graphics Card (Optional): NVIDIA GeForce RTX GPU with CUDA 12 support (accelerates Ollama inference)
2.5.2 Software Specification
• Operating System: Windows 11 / Ubuntu Linux
• Programming Languages: Python 3.11, JavaScript (ES6+ / React JSX)
• Integrated Development Environment: Visual Studio Code
• Database Management Tool: pgAdmin 4 / psql CLI
• Version Control System: Git and GitHub Cloud
2.5.3 Technology Used
A detailed breakdown of all libraries and frameworks powering the frontend, backend, database, and machine learning subsystems is provided in Chapter IV.

2.6 COST ESTIMATION AND SCHEDULING
2.6.1 Cost Estimation
• Developer Workstation Hardware: ₹85,000
• Software Tools & Licenses (Open Source): ₹0
• Cloud API & Token Consumption Fees: ₹0
• Webhook Tunneling & Staging Infrastructure: ₹3,500
• Total Estimated Expenditure: ₹88,500
2.6.2 Scheduling (Agile Iterations)
• Sprint 1 (Weeks 1–4): Scaffolding, Jira Webhooks, PostgreSQL & pgvector setup.
• Sprint 2 (Weeks 5–8): Python AST Parser implementation and BGE-Small ONNX vector pipeline.
• Sprint 3 (Weeks 9–12): GitHub App Check Run integration, Ollama XAI synthesis, hybrid risk engine.
• Sprint 4 (Weeks 13–16): React executive dashboard, RBAC session gating, evaluation, and documentation.

================================================================================
CHAPTER III: DESIGN AND DEVELOPMENT PROCESS

3.1 FUNDAMENTAL DESIGN CONCEPTS
1. Abstraction: Converting complex code syntax trees and unstructured textual criteria into standardized, machine-comparable constraint objects.
2. Refinement: Stepwise functional decomposition from high-level webhook events down to line-level AST token comparisons.
3. Modularity: Decoupling the ingestion, parsing, scoring, verbalization, and visualization layers into independently testable Python modules.
4. Software Architecture: An event-driven, micro-modular architecture built around asynchronous REST APIs and relational vector databases.
5. Structural Partitioning: Horizontal partitioning across ingestion and presentation tiers; vertical partitioning across security and database layers.
6. Information Hiding: Strict encapsulation of database sessions, GitHub App private keys (`.pem`), and internal webhook secrets.

3.2 DESIGN NOTATIONS & DIAGRAMS
3.2.1 Data Flow Diagrams
The data flow within Orion is modeled using standard Gane & Sarson / Calicut University academic notations:
• Process: Represented by an oval, indicating an activity transforming incoming data into outgoing data.
• Data Store: Represented by open parallel horizontal lines with a numbered identifier, representing data at rest.
• External Entity: Represented by a rectangle, indicating external producers or consumers of system data.
• Direction of Flow: Represented by directed arrows showing data movement.

[INSERT FIGURE 3.1: Context Level Data Flow Diagram (Level 0 DFD)]
Description: Shows Process 0.0 (Orion Governance Engine) interacting with Jira Cloud, GitHub CI/CD, Developer, and QA Lead/Auditor, backed by PostgreSQL.

[INSERT FIGURE 3.2: Level 1.1 Data Flow Diagram (QA Lead / Admin Module)]
Description: Depicts the QA Lead actor fanning out into 6 core processes: Login/Session Gate, View Traceability Matrix, Adjust Sensitivity Thresholds, Execute Risk Override, Inspect XAI Evidence, and Export Compliance Report, connected to data stores D1 (Requirements), D2 (Test Cases), D3 (Trace Matrix), and D4 (Audit Logs).

[INSERT FIGURE 3.3: Level 1.2 Data Flow Diagram (Software Developer Module)]
Description: Depicts the Developer actor fanning out into 5 core processes: Login, Submit Test PR, View Check Run Annotations, Inspect AST Assertion Details, and Review Drift Diagnostics, connected to data stores D2, D3, and D4.

3.2.2 Use Case Diagrams
[INSERT FIGURE 3.4: Use Case Diagram for QA Lead / Administrator]
Description: Details the administrative interactions including threshold configuration, manual link override, and audit report generation.

[INSERT FIGURE 3.5: Use Case Diagram for Software Developer & CI Service]
Description: Details code tagging, webhook triggers, automated AST parsing, and GitHub Check Run review.

3.3 DESIGN PROCESS
3.3.1 Database Design (Full Schema Tables)

Table 3.1: LOGIN_ROLES Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | INT | Primary Key | Unique user role identifier
2 | username | VARCHAR(50) | Not Null, Unique | System login handle
3 | role_type | VARCHAR(20) | Not Null | 'QA_LEAD' or 'DEVELOPER'
4 | last_login | TIMESTAMP | Nullable | Last active timestamp

Table 3.2: REQUIREMENTS Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | UUID | Primary Key | Unique requirement ID
2 | external_key | VARCHAR(50) | Not Null, Unique | Jira Issue Key (e.g. CORE-142)
3 | title | VARCHAR(255) | Not Null | Summary of user story
4 | description | TEXT | Nullable | Full acceptance criteria text
5 | extracted_constraints | JSONB | Not Null | Structured boundary dictionary
6 | embedding | VECTOR(384) | Not Null | Dense semantic vector
7 | created_at | TIMESTAMP | Not Null | Ingestion timestamp

Table 3.3: TEST_CASES Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | UUID | Primary Key | Unique test case ID
2 | file_path | VARCHAR(255) | Not Null | Path to test file in repo
3 | function_name | VARCHAR(128) | Not Null | Function identifier
4 | target_requirement | VARCHAR(50) | Not Null | Traced Jira key from @traces
5 | assertions | JSONB | Not Null | AST-extracted assertion rules
6 | embedding | VECTOR(384) | Not Null | Dense semantic vector
7 | updated_at | TIMESTAMP | Not Null | Extraction timestamp

Table 3.4: TRACEABILITY_MATRIX Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | UUID | Primary Key | Unique trace link identifier
2 | requirement_id | UUID | Foreign Key (requirements.id) | Linked requirement
3 | test_case_id | UUID | Foreign Key (test_cases.id) | Linked test case
4 | semantic_score | FLOAT | Not Null | Cosine similarity (0.0 - 1.0)
5 | structural_score | FLOAT | Not Null | AST assertion match (0.0 - 1.0)
6 | risk_score | FLOAT | Not Null | Composite compliance index
7 | confidence | FLOAT | Not Null | Signal agreement metric
8 | status | VARCHAR(20) | Not Null | COVERED, PARTIAL, DRIFTED
9 | is_overridden | BOOLEAN | Default False | Manual override status

Table 3.5: AUDIT_LOGS Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | UUID | Primary Key | Unique audit entry ID
2 | trace_link_id | UUID | Foreign Key (traceability_matrix.id) | Target matrix link
3 | actor | VARCHAR(64) | Not Null | User handle or service name
4 | action | VARCHAR(64) | Not Null | 'OVERRIDE', 'EVALUATE'
5 | xai_explanation | TEXT | Nullable | Plain-English drift summary
6 | created_at | TIMESTAMP | Not Null | Audit timestamp

Table 3.6: THRESHOLD_CONFIG Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | INT | Primary Key | Configuration record ID
2 | covered_threshold | FLOAT | Not Null | Min score for COVERED status
3 | drifted_threshold | FLOAT | Not Null | Threshold for DRIFTED status
4 | updated_by | VARCHAR(50) | Not Null | Admin who set policy
5 | updated_at | TIMESTAMP | Not Null | Policy update timestamp

Table 3.7: WEBHOOK_LOGS Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | UUID | Primary Key | Webhook transaction ID
2 | source_platform | VARCHAR(20) | Not Null | 'JIRA' or 'GITHUB'
3 | event_type | VARCHAR(50) | Not Null | Webhook event header
4 | delivery_status | VARCHAR(20) | Not Null | 'SUCCESS' or 'REJECTED'
5 | received_at | TIMESTAMP | Not Null | Delivery timestamp

Table 3.8: JIRA_SYNC_COMMENTS Table
SL NO | FIELD NAME | DATA TYPE | CONSTRAINT | DESCRIPTION
1 | id | UUID | Primary Key | Unique sync record ID
2 | requirement_id | UUID | Foreign Key (requirements.id) | Target ticket
3 | comment_body | TEXT | Not Null | Synchronized audit text
4 | posted_at | TIMESTAMP | Not Null | Jira API post timestamp

3.3.2 Normalization Database
The database has been designed and normalized up to the Third Normal Form (3NF):
• First Normal Form (1NF): Each column contains atomic values; multi-dimensional vector embeddings are stored using native pgvector primitives.
• Second Normal Form (2NF): All non-key attributes are fully functionally dependent on the primary key (UUIDs), eliminating any partial dependencies.
• Third Normal Form (3NF): Transitive dependencies have been eliminated by separating user authentication, requirement details, test extractions, and audit logs into independent, foreign-key-linked tables.

3.3.3 Input Design
The input design ensures secure, validated data collection. Major input screens include the RBAC Authentication Session Modal, Dynamic Sensitivity Sliders, Webhook Simulation Trigger, and Manual Override Justification Dialog.

3.3.4 Output Design
The output design focuses on clarity, rapid decision-making, and audit compliance. Major output screens include the Interactive Traceability Heatmap Table, XAI Drift Explanation Modal, and the GitHub Check Run Pull Request interface.

3.4 DEVELOPMENT APPROACH (AGILE SPRINTS)
Orion was engineered using an Agile development lifecycle consisting of four 4-week iterative sprints: Requirement Gathering & Scaffolding, Core AST & Embedding Engine, CI/CD Integration & XAI Verbalization, and UI Dashboard & Final Validation.

================================================================================
CHAPTER IV: CODING

4.1 FRONTEND ARCHITECTURE
Built using React 18, Vite, and custom CSS design tokens:
• `App.jsx`: Master container maintaining user session state and coordinating REST data fetches.
• `LoginModal.jsx`: Enforces the Role-Based Access Control gate, allowing session switching between QA Lead and Developer.
• `MatrixTable.jsx`: Renders the central traceability matrix with live search, status chips, and role-locked override triggers.
• `SensitivitySliders.jsx`: Dual-range sliders enabling real-time recalibration of classification thresholds.
• `StatsBar.jsx`: Top-level metrics bar displaying aggregate counts of Covered, Partial, Drifted, and Uncovered requirements.

4.2 BACKEND ARCHITECTURE
Built using FastAPI and asynchronous Python runtimes:
• `orion/app.py`: Application entry point, initializing CORS middleware and mounting routers.
• `orion/github/webhook.py`: Validates incoming HMAC-SHA256 signatures before processing pull request events.
• `orion/github/auth.py`: Asynchronously exchanges GitHub App private key credentials for temporary installation tokens using `httpx.AsyncClient`.
• `orion/jira/adf.py`: Recursively parses Jira Atlassian Document Format JSON trees with depth protection to prevent stack overflows.
• `orion/ingestion/service.py`: Executes atomic database upserts for test cases and requirements.

4.3 AI & PARSER SUBSYSTEMS
• `orion/extraction/ast_parser.py`: Traverses Python source files using `ast.NodeVisitor` to extract `@traces` keys, assertion comparators, and literal values without executing code.
• `orion/extraction/embedding.py`: Loads `bge-small-en-v1.5` via ONNX Runtime to produce normalized 384-dimensional dense vectors.
• `orion/scoring/engine.py`: Implements the composite risk calculation:
  S_hybrid = 0.6 · S_sem(Req, Test) + 0.4 · S_struct(Req, Test)
• `orion/xai/explainer.py`: Interfaces with the local Ollama Llama 3.1 8B instance using structured evidence prompts, falling back to deterministic templates if offline.

================================================================================
CHAPTER V: TESTING AND IMPLEMENTATION

5.1 TESTING
Testing is the vital verification and validation activity ensuring the software performs reliably and satisfies all academic and operational specifications.

5.1.1 Testing Methodologies
• Manual Testing: Manual walkthroughs were conducted from both QA Lead and Developer perspectives to verify user interface responsiveness, modal triggers, and role-based control locking.
• Automation Testing: Automated test suites were executed using Pytest and HTTPX to validate endpoint routing, AST node parsing, vector calculations, and database operations.

5.1.2 Different Testing
1. Unit Testing: Each module was tested in isolation. The AST parser was tested across varied Python comparison syntax; the embedding pipeline was tested for vector normalization.
2. Integration Testing: Tested the end-to-end integration between incoming webhooks, database transactions, and outbound API calls.
   - Top-Down Integration: Validated top-level FastAPI routes downward into mocked database repositories.
   - Bottom-Up Integration: Validated low-level AST visitor routines upward into the composite scoring engine.
3. Validation Testing:
   - Front-End Validation: Ensured numeric sliders enforce valid boundaries (0 <= tau_struct < tau_sem <= 1.0) and disabled controls for non-privileged users.
   - Back-End Validation: Pydantic v2 schemas validated all incoming JSON payloads, rejecting malformed webhooks.
4. Output Testing: Output formats (Jira comments, GitHub annotations, matrix exports) were reviewed with QA stakeholders to verify clarity.

5.1.3 Test Chart
| Test Case ID | Test Name | Description | Inputs | Expected Output | Actual Output | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TC-01 | RBAC Session Gate | Verify role restriction | Role: 'Developer' | Override button locked | Disabled with tooltip | PASS |
| TC-02 | AST Extraction | Extract @traces decorator | Python test file | Target key 'CORE-142' | Extracted 'CORE-142' | PASS |
| TC-03 | Ingestion Invariance | Idempotent upsert | Repeated webhook | Single database record | Updated, no duplicate | PASS |
| TC-04 | Hybrid Scoring | Covered state evaluation | S_sem=0.78, S_struct=1.0 | Score >= 0.75 (COVERED) | S_hybrid=0.86 (COVERED) | PASS |
| TC-05 | Drift Detection | Catch assertion drift | SLA: 100ms, Assert: 200ms | Score < 0.40 (DRIFTED) | S_hybrid=0.38 (DRIFTED) | PASS |
| TC-06 | GitHub Gating | Post Check Run result | DRIFTED status | Check Run: Failure | Merge blocked on PR | PASS |
| TC-07 | XAI Fallback | Local LLM offline test | Ollama daemon stopped | Template explanation | Deterministic text logged| PASS |

5.2 QUALITY ASSURANCE & POLICIES
Software Quality Assurance (SQA) monitored development practices to ensure high reliability and maintainability. Code quality was strictly verified using the Ruff linter, achieving zero blocking errors across all production modules.

5.2.1 Generic Risks
1. Schedule Risk: Mitigated through Agile sprint planning and prioritizing the four core enterprise tickets (`CORE-142` to `CORE-145`).
2. Budget Risk: Completely eliminated by adopting open-source runtimes and local edge AI models.
3. Operational Risk: Addressed by integrating directly into GitHub pull requests, eliminating workflow friction for developers.
4. Technical Risk: Mitigated by implementing deterministic AST parsing and fallback templates for local LLM inference.
5. Programmatic Risk: Shielded from external cloud API policy changes by maintaining an on-premise execution architecture.

5.3 SYSTEM IMPLEMENTATION
Implementation transforms design abstractions into operational software.
5.3.1 Implementation Procedures
• Parallel Conversion: Orion was operated alongside existing manual traceability spreadsheets, proving superior detection of specification drift without disrupting ongoing sprints.
• Direct Conversion: Applied to local test execution branches to evaluate pull requests directly.
• Pilot Conversion: Deployed on a single microservice repository before extending across multiple development repositories.

5.4 SYSTEM MAINTENANCE
Maintenance ensures the system remains operational throughout its software lifecycle:
• Corrective Maintenance: Repairing syntax visitor edge cases when encountering uncommon Python assertions.
• Adaptive Maintenance: Updating Jira REST API bindings to accommodate Atlassian Cloud schema evolutions.
• Perfective Maintenance: Refactoring frontend styling tokens to improve UI contrast and performance.
• Preventive Maintenance: Updating Python dependencies and scanning packages for security vulnerabilities.

================================================================================
CHAPTER VI: CONCLUSION

6.1 CONCLUSION
The development of Orion represents a successful convergence of software quality engineering, Abstract Syntax Tree parsing, and local Explainable AI. By replacing static, manually maintained spreadsheets with an automated CI/CD governance engine, Orion solves the persistent industry challenge of silent specification drift. 

Empirical validation demonstrated sub-30ms processing times per requirement-test pair, while the hybrid scoring model (0.6 * Semantic + 0.4 * Structural) effectively identified numeric-boundary drifts that pure semantic embeddings failed to catch. Local inference via ONNX Runtime and Ollama guarantees complete data privacy and zero recurring cloud costs. With its role-based dashboard and automated GitHub Check Run gating, Orion delivers an enterprise-ready compliance solution fulfilling all requirements for the Master of Computer Applications degree.

6.2 SCOPE FOR FURTHER ENHANCEMENT
1. Multi-Language AST Support: Expanding the AST parsing engine to support JavaScript/TypeScript (Jest/Vitest), Java (JUnit), and Go.
2. Distributed Redis Caching: Migrating the in-memory GitHub App installation token cache to Redis for multi-worker production deployments.
3. Automated Patch Generation: Enabling the local LLM to propose automated GitHub pull request code patches to correct drifted assertions.
4. Bidirectional Syncing: Allowing approved test-side assertion updates to automatically update Jira acceptance criteria when authorized by QA Leads.
5. Multi-Tenant Enterprise Clustering: Adding multi-organization tenancy with OAuth 2.0 (3LO) authentication for large enterprise deployments.

6.3 BIBLIOGRAPHY
1. Atlassian. (2024). Atlassian Document Format (ADF) Specifications. Atlassian Developer Documentation.
2. Python Software Foundation. (2024). The ast module: Abstract Syntax Trees. Python 3 Documentation.
3. Xiao, S., Liu, Z., Zhang, P., & Muennighoff, N. (2023). C-Pack: Packaged Resources to Advance General Chinese Embedding. arXiv preprint arXiv:2309.07597.
4. AI @ Meta. (2024). The Llama 3 Herd of Models. Meta AI Research Technical Report.
5. PostgreSQL Global Development Group. (2024). pgvector: Open-source vector similarity search for PostgreSQL.
6. Pressman, R. S., & Maxim, B. R. (2020). Software Engineering: A Practitioner's Approach (9th ed.). McGraw-Hill Education.
7. ISO/IEC/IEEE. (2018). Systems and software engineering — Life cycle processes — Requirements engineering (ISO/IEC/IEEE Standard No. 29148:2018).

================================================================================
ANNEXURE - A: INPUT AND OUTPUT DESIGN

[INSERT FIGURE A.1: Major Input Screen - Authentication Session Gate (LoginModal.jsx)]
Description: The role-selection modal allowing users to authenticate under QA Lead or Developer privileges.

[INSERT FIGURE A.2: Major Input Screen - Sensitivity Configuration Sliders (SensitivitySliders.jsx)]
Description: Real-time dual-slider controls allowing QA Leads to adjust Covered and Drifted classification thresholds.

[INSERT FIGURE A.3: Major Input Screen - Manual Override Justification Modal (MatrixTable.jsx)]
Description: Modal requiring QA Leads to enter mandatory justification text before overriding a risk classification.

[INSERT FIGURE A.4: Major Output Screen - Requirements Traceability Matrix Heatmap (MatrixTable.jsx)]
Description: The primary executive dashboard showing color-coded status badges, requirement summaries, linked test functions, and hybrid risk scores.

[INSERT FIGURE A.5: Major Output Screen - XAI Drift Explanation Modal]
Description: The diagnostic modal presenting plain-English root-cause explanations generated by the local Llama 3.1 8B model.

[INSERT FIGURE A.6: Major Output Screen - GitHub Check Run PR Gating Summary]
Description: The GitHub pull request interface showing Orion's automated Check Run blocking a merge due to specification drift.

================================================================================
ANNEXURE - B: TABLE OF ABBREVIATIONS
ABBREVIATION | EXPANDED DESCRIPTION
ADF | Atlassian Document Format
AI | Artificial Intelligence
API | Application Programming Interface
ASGI | Asynchronous Server Gateway Interface
AST | Abstract Syntax Tree
CI/CD | Continuous Integration / Continuous Deployment
DFD | Data Flow Diagram
FK | Foreign Key
HMAC | Hash-based Message Authentication Code
HNSW | Hierarchical Navigable Small World
IDE | Integrated Development Environment
JSON | JavaScript Object Notation
LLM | Large Language Model
MCA | Master of Computer Applications
ONNX | Open Neural Network Exchange
ORM | Object Relational Mapping
PK | Primary Key
PR | Pull Request
RBAC | Role-Based Access Control
REST | Representational State Transfer
RTM | Requirements Traceability Matrix
SLA | Service Level Agreement
SRS | Software Requirement Specification
UI | User Interface
UUID | Universally Unique Identifier
VCS | Version Control System
XAI | Explainable Artificial Intelligence
