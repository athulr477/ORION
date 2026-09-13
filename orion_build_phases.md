# Orion — Phase-by-Phase Build Instructions for Opus

Hand these to Opus **one phase at a time**. Do not start Phase N+1 until Phase N runs and passes its verification step. Each phase includes what to build, the decisions already locked in (so Opus doesn't improvise them), and how to confirm it's done before moving on.

---

## Pre-Phase 0 — Decisions to lock in before any code (do this first, not in Opus)

Write these three things down literally, and paste them into Phase 1's prompt as fixed constraints:

1. **Requirement↔test link syntax.** Example: a decorator `@traces("REQ-123")` on the test function, parsed at ingestion. Pick one convention and state it exactly.
2. **Risk formula and starting thresholds.**
   Example: `risk_score = 0.6 × semantic_score + 0.4 × structural_score`
   `risk_score > 0.75` → Covered, `0.4–0.75` → Partial, `< 0.4` → Drifted.
   These are placeholders to be tuned in Phase 10 — but they must exist before Phase 5.
3. **Requirement-side constraint patterns.** A short list of what counts as an extractable constraint from requirement text (e.g. comparison operators — "greater than," "at least," "no longer than"; numeric thresholds; boolean conditions like "must," "must not"). This is a rule list, not a model.

Also: start hand-labeling the 30-pair evaluation dataset (10 Covered / 10 Partial / 10 Drifted) now, in parallel with Phase 1. You know the schema already — you don't need the pipeline built to do this.

---

## Phase 1 — Database & Schema

**Build:**
- Enable the `pgvector` extension.
- Create `requirements`, `test_cases`, `traceability_matrix` tables.
- `test_cases` includes a `requirement_id` foreign key (or a join table, per your Pre-Phase 0 link decision) — **do not skip this**, it's the fix for the original blocking gap.
- `traceability_matrix` columns: `semantic_score`, `structural_score`, `risk_score`, `confidence`, `status` (enum: Covered/Partial/Drifted), `requirement_delta`, `audit_summary`.
- Write the migration.

**Verify before moving on:** migration runs clean on a fresh DB; you can manually insert one requirement + one test row with a link between them and query the join.

---

## Phase 2 — Ingestion Layer

**Build:**
- FastAPI webhook endpoints: Jira (requirement + changelog payloads), GitHub (test file pushes).
- **Webhook signature verification on both endpoints** — this was missing from the original plan; add it now, not later.
- Parse the requirement↔test link (per your Pre-Phase 0 convention) at ingestion time and populate the FK/join table.
- Upsert into `requirements` and `test_cases`.

**Verify before moving on:** send a mock Jira payload and mock GitHub push (use the dashboard's future simulate-webhook shape, or plain curl for now) and confirm rows land correctly linked in the DB, and that a payload with a bad/missing signature is rejected.

---

## Phase 3 — Structural Extraction (two-sided)

**Build — code side (as originally scoped):**
- Parse test files with Python's `ast` module: assertion comparisons, operators, literal values, function-call targets, `pytest.raises` exception types.
- Fallback to docstring-only on parse failure.

**Build — requirement side (the fix, new in this phase):**
- Apply the Pre-Phase 0 constraint-pattern rules to requirement text to extract structured constraints (conditions, thresholds, comparison operators) mentioned in plain English.
- This is what Phase 5's structural matcher will actually compare against — without it there's nothing on the requirement side to match.

**Verify before moving on:** run against 3–5 real test files and 3–5 real requirement texts; manually check the extracted structure matches what a human would read out of each.

---

## Phase 4 — Semantic Vector Engine

**Build:**
- Load BGE-small-en-v1.5 once at startup (CPU).
- Embed requirement text and test text.
- **Embedding-input fallback (the fix):** when a test has no docstring, embed `function name + assertion literals` instead of an empty/near-empty string.
- Compute cosine similarity via pgvector's `<=>` operator → `semantic_score`.

**Verify before moving on:** embed a requirement and its correctly-linked test, confirm `semantic_score` is meaningfully higher than for a requirement paired with an unrelated test. Specifically test one docstring-less test case to confirm the fallback produces a non-degenerate score.

---

## Phase 5 — Structural Matcher & Hybrid Risk Engine

**Build:**
- Match requirement-side constraints (Phase 3) against code-side assertions (Phase 3) → `structural_score`.
- Combine `semantic_score` + `structural_score` into `risk_score` + `confidence` using the **exact formula and thresholds fixed in Pre-Phase 0** — don't let Opus invent numbers here.
- Classify Covered / Partial / Drifted using the two thresholds.

**Verify before moving on:** run against your 30-pair labeled dataset (curated in parallel since Phase 1) and check raw precision/recall by eye — doesn't need to be good yet, just needs to produce sane, non-random classifications. This is your first real signal on whether the formula needs adjusting before you build four more phases on top of it.

---

## Phase 6 — Requirement-Diff Tracking

**Build:**
- Parse Jira changelogs into structured deltas: added/removed conditions, changed thresholds, changed literals.
- Store as `requirement_delta` when a requirement changes and its linked test hasn't been touched since.
- Keep this rule-based/regex, not LLM-based — consistent with the "no LLM in the decision path" architectural claim.

**Verify before moving on:** simulate a requirement edit (e.g. change a threshold value in the mock changelog) and confirm `requirement_delta` captures the change accurately in structured form.

---

## Phase 7 — Evidence-Grounded LLM Verbalization

**Build:**
- Build the deterministic evidence tuple: `(requirement_delta, test_implementation_summary, status)` from Phases 5–6 output.
- Prompt Llama 3.1 8B (temperature=0.0) to verbalize it into one audit sentence.
- Only run this for Partial/Drifted results — Covered results don't need an explanation.

**Verify before moving on:** feed it 3–5 real Drifted/Partial cases from your labeled set, read the generated sentences, confirm they accurately describe the evidence tuple and don't invent claims not present in it.

---

## Phase 8 — Dashboard (Frontend)

**Build:**
- React + Vite: RTM table with status badges + scores.
- XAI heatmap modal (keyword overlap).
- Sensitivity slider — adjusts both thresholds live, re-queries classification.
- Simulate-webhook button for offline demos.

**Verify before moving on:** load real data from Phases 1–7, confirm the table renders correctly, the slider actually changes displayed statuses live, and the simulate button produces a working end-to-end demo without needing real Jira/GitHub access.

---

## Phase 9 — GitHub App Integration

**Build:**
- Installation-token auth.
- Post `risk_score` / `status` / `audit_summary` as a Check Run on PRs touching linked test files.

**Verify before moving on:** open a test PR against a linked test file in a sandbox repo, confirm the Check Run appears with correct data.

---

## Phase 10 — Evaluation Framework (final pass)

**Build:**
- Run cosine-only baseline vs. full hybrid engine against your (by-now fully labeled and already-used-once-in-Phase-5) 30-pair dataset.
- Output precision, recall, macro-F1 for both.

**Verify before moving on:** this is the finish line — confirm the hybrid engine actually beats the cosine-only baseline on the labeled set. If it doesn't, that's real signal to go back and retune the Phase 5 formula/thresholds before calling the build done.

---

## Running note for Opus across all phases

At the start of each phase's prompt, remind Opus:
- The requirement↔test link convention (Pre-Phase 0 decision #1)
- The risk formula and thresholds (Pre-Phase 0 decision #2) — don't let it re-derive these
- "No LLM in the decision path" — only Phase 7 touches an LLM, and only for phrasing, never for scoring or classification
