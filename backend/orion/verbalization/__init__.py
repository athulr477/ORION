"""Verbalization module — Phase 7.

Evidence-grounded LLM verbalization: assembles a deterministic evidence tuple
from Phases 5–6 output and prompts Llama 3.1 8B (temperature=0.0) to verbalize
it into a single audit sentence.

Only Partial/Drifted entries are verbalized — Covered results don't need an
explanation.

IMPORTANT: No LLM in the decision path. The LLM is used ONLY for phrasing,
never for scoring or classification.
"""
