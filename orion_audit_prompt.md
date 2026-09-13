You are auditing an existing codebase called Orion (FastAPI + PostgreSQL/pgvector + React, a requirements-traceability drift detector). Do not redesign anything or add new features. Your job is to check four specific things against the actual code, report what you find, and fix only what's actually broken. Go one item at a time, in order — confirm each before moving to the next.

---

## Item 1 — Is `confidence` actually computed?

The DB schema (`orion/models.py` or equivalent) has a `confidence` column on the traceability results table. Check:

1. Search the codebase for every place `confidence` is written to (not just read).
2. If nothing ever writes to it: it's dead. Implement it as an explicit formula — e.g. `confidence = 1 - abs(semantic_score - structural_score)` (higher when both signals agree) or an evidence-completeness measure (e.g. fraction of expected fields — assertion, constraint, literal — that were successfully extracted on both sides). Pick whichever is simpler given what's already computed in `matcher/`, implement it, and make sure it's actually persisted to the DB row.
3. If it IS computed somewhere: just report where, and report whether it's ever surfaced in the API response / dashboard. If it's computed but never exposed, add it to the relevant API serializer and to the RTM table's row data — don't touch the frontend UI itself unless asked.

Report back: "confidence was [dead / computed-but-hidden / working correctly]" before moving to Item 2.

---

## Item 2 — Is the GitHub webhook signature actually verified?

1. Find the webhook route(s) that receive GitHub PR events (`github/` or equivalent).
2. Check whether `GITHUB_WEBHOOK_SECRET` is used anywhere besides being loaded from env — specifically, is there an HMAC-SHA256 comparison against the incoming `X-Hub-Signature-256` header before the payload is processed?
3. If the secret is loaded but never checked: this is a real security gap. Add the standard verification — compute HMAC-SHA256 of the raw request body using the secret, compare against the header using a constant-time comparison (`hmac.compare_digest`), reject with 401 on mismatch or missing header. Do this before any payload parsing happens, not after.
4. Separately check what (if anything) authenticates the Jira webhook endpoint, since Jira doesn't use the same signature scheme. Report what's there, even if it's "nothing" — don't add auth to it unless you find it's trivially missing something Jira's docs specify (e.g. a shared secret query param), in which case flag it rather than guessing at implementation.

Report back what you found and what you changed before moving to Item 3.

---

## Item 3 — Does the requirement-side constraint extractor generalize, or is it overfit to the 30-pair eval set?

1. Find the regex/NLP constraint extractor (`extraction/` or equivalent) that pulls numeric boundaries and comparison operators out of requirement text.
2. Look at what phrasings it currently matches (e.g. "<=", "at least", "no more than").
3. Write 8–10 new test requirement strings that were NOT in the original 30-pair benchmark set, using varied natural phrasing for the same underlying constraint types — e.g. "should not take longer than 100ms", "must respond within 100 milliseconds", "response time under 100ms is required", "cannot exceed a 100ms threshold". Include a couple of trickier cases: compound conditions ("must be at least 5 and no more than 20"), and units written differently ("100ms" vs "100 ms" vs "0.1s").
4. Run the extractor against these and report which ones it correctly parses into structured constraints and which ones it fails or misparses on.
5. Do NOT try to make it perfect — this is a rule-based extractor for a final-year project, not a production NLP system. Just report the failure rate honestly, and if there's a cheap, obvious fix for common cases (e.g. it's missing a synonym list for "must not exceed" / "cannot exceed" / "no more than" all meaning the same operator), add that. Don't attempt anything requiring an actual NLP model — that would contradict the project's own "no LLM in the decision path" design claim.

Report back the pass/fail breakdown before moving to Item 4.

---

## Item 4 — Confirm the Check Run status doesn't assume merge-blocking

1. Find where the GitHub Check Run is created/posted (`github/` or equivalent) for Drifted and Partial results.
2. Check what `conclusion` value is sent — `failure`, `neutral`, `success`, etc. — for each classification (Covered / Partial / Drifted).
3. Confirm the code itself doesn't set anything else that would force blocking behavior beyond the Check Run's own conclusion field (e.g. don't auto-configure branch protection via the GitHub API anywhere — that would make Orion enforce blocking rather than just report status, which contradicts its advisory-only design).
4. Report what conclusion values are currently used for each status. No code change needed unless you find something that actively configures required-status-check enforcement — if you find that, flag it and ask before removing it, since it might be intentional for a demo.

---

After all four items: give a short summary — what was already correct, what you fixed, and what you found but didn't touch (with a one-line reason why, e.g. "flagged for Athul's decision" or "out of scope — would need an NLP model").
