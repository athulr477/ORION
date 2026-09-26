import asyncio
import os
import sys

# Ensure backend is in python path
sys.path.insert(0, os.path.abspath("."))

from orion.config import settings
from orion.database import get_session_context
from orion.github.auth import get_installation_token
from orion.github.client import fetch_file_content, fetch_pr_files
from orion.ingestion.parsers import extract_test_functions
from orion.extraction.code_extractor import extract_assertions
from orion.embedding.engine import semantic_similarity, embed_text
from orion.embedding.text_builder import build_test_text
from orion.analysis.structural_matcher import compute_structural_score
from orion.analysis.risk_engine import classify
from orion.models.requirement import Requirement
from sqlalchemy import select

async def main():
    token = get_installation_token()
    owner = "athulrj455"
    repo = "orion-sandbox"
    pr_num = 1
    head_sha = "510d0147e105a0131bb707c9b24f5679030f7db3"
    workspace_id = "7c9e3ac1-e027-4c8e-bf2c-a2e152e5e9c1"

    print("Fetching file content...")
    content = fetch_file_content(owner, repo, "tests/test_core.py", head_sha, token)
    functions = extract_test_functions(content)
    print(f"Extracted {len(functions)} test functions from tests/test_core.py")

    async with get_session_context() as session:
        # Fetch all requirements in workspace
        stmt = select(Requirement).where(Requirement.workspace_id == workspace_id)
        result = await session.execute(stmt)
        reqs = {r.external_id: r for r in result.scalars().all()}
        print(f"Loaded {len(reqs)} requirements from DB for workspace {workspace_id}")

        results_by_status = {"Covered": [], "Partial": [], "Drifted": []}
        all_results = []

        for fn in functions:
            for req_id in fn.traced_requirements:
                req = reqs.get(req_id)
                if not req:
                    print(f"MISSING IN DB: {req_id}")
                    continue

                code_extraction = extract_assertions(fn.source_code)
                assertions_dict = code_extraction.to_dict()
                test_text = build_test_text(
                    function_name=fn.function_name,
                    docstring=fn.docstring,
                    assertions_extracted=assertions_dict,
                )
                test_embedding = embed_text(test_text)
                sem_score = semantic_similarity(req.embedding, test_embedding)
                match_res = compute_structural_score(req.constraints_extracted, assertions_dict)
                risk_res = classify(sem_score, match_res.structural_score)

                item = {
                    "req_id": req_id,
                    "title": req.title,
                    "fn": fn.function_name,
                    "status": risk_res.status,
                    "risk": risk_res.risk_score,
                    "semantic": sem_score,
                    "structural": match_res.structural_score,
                    "req_constraints": req.constraints_extracted,
                    "code_assertions": assertions_dict["assertions"],
                }
                all_results.append(item)
                results_by_status[risk_res.status].append(item)

        print(f"\n--- EVALUATION SUMMARY ({len(all_results)} pairs evaluated) ---")
        print(f"Covered: {len(results_by_status['Covered'])}")
        print(f"Partial: {len(results_by_status['Partial'])}")
        print(f"Drifted: {len(results_by_status['Drifted'])}")

        print("\n--- DRIFTED CASES ---")
        for item in results_by_status["Drifted"]:
            print(f"[{item['status']}] {item['req_id']} | Test: {item['fn']} | Risk: {item['risk']:.3f} | Sem: {item['semantic']:.3f} | Struct: {item['structural']:.3f}")
            print(f"   Req bounds : {item['req_constraints']}")
            print(f"   Code assert: {item['code_assertions']}")

        print("\n--- PARTIAL CASES ---")
        for item in results_by_status["Partial"][:10]:
            print(f"[{item['status']}] {item['req_id']} | Test: {item['fn']} | Risk: {item['risk']:.3f} | Sem: {item['semantic']:.3f} | Struct: {item['structural']:.3f}")

if __name__ == "__main__":
    asyncio.run(main())
