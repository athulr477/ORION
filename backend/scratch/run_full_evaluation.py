import asyncio
import io
import os
import sys
import httpx

# Ensure UTF-8 stdout for Windows console
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath("."))

from orion.config import settings
from orion.github.auth import get_installation_token
from orion.github.client import create_check_run
from orion.github.routes import _analyse_pr
from orion.database import get_session_context
from orion.models.traceability_matrix import TraceabilityMatrix
from orion.models.requirement import Requirement
from orion.models.test_case import TestCase
from sqlalchemy import select

async def main():
    owner = "athulrj455"
    repo = "orion-sandbox"
    pull_number = 1
    head_sha = "510d0147e105a0131bb707c9b24f5679030f7db3"
    installation_id = 161384467
    workspace_id = "7c9e3ac1-e027-4c8e-bf2c-a2e152e5e9c1"

    print("==================================================================")
    print("STEP 1: Authenticate with GitHub App and create Check Run")
    print("==================================================================")
    token = get_installation_token(installation_id)
    print(f"Acquired GitHub installation token (len={len(token)})")

    check_run_id = create_check_run(owner, repo, head_sha, token)
    print(f"Created Check Run #{check_run_id} on {owner}/{repo} @ {head_sha[:8]} (status: in_progress)")

    print("\n==================================================================")
    print("STEP 2: Execute PR Analysis Pipeline via _analyse_pr")
    print("==================================================================")
    await _analyse_pr(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        head_sha=head_sha,
        installation_id=installation_id,
        check_run_id=check_run_id,
        token=token,
        workspace_id=workspace_id,
    )
    print("Completed _analyse_pr pipeline execution!")

    print("\n==================================================================")
    print("STEP 3: Verify GitHub Check Run and Line Annotations")
    print("==================================================================")
    check_url = f"https://api.github.com/repos/{owner}/{repo}/check-runs/{check_run_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client() as client:
        resp = client.get(check_url, headers=headers)
        resp.raise_for_status()
        check_data = resp.json()
        print(f"Check Run ID        : {check_data['id']}")
        print(f"Check Run Name      : {check_data['name']}")
        print(f"Status              : {check_data['status']}")
        print(f"Conclusion          : {check_data['conclusion']}")
        print(f"Title               : {check_data['output']['title']}")
        print(f"HTML URL            : {check_data['html_url']}")

        # Fetch annotations
        ann_url = f"https://api.github.com/repos/{owner}/{repo}/check-runs/{check_run_id}/annotations"
        ann_resp = client.get(ann_url, headers=headers)
        ann_resp.raise_for_status()
        annotations = ann_resp.json()
        print(f"Annotations count   : {len(annotations)}")
        print("\nSample Annotations:")
        for a in annotations[:5]:
            print(f"  - [{a.get('annotation_level').upper()}] {a.get('path')}:{a.get('start_line')}-{a.get('end_line')} | {a.get('title')}: {a.get('message')[:100]}...")

    print("\n==================================================================")
    print("STEP 4: Verify Jira Comments for Intended Drifts")
    print("==================================================================")
    from orion.jira.client import _auth_headers, _base_url
    jira_keys = ["SCRUM-5", "SCRUM-8", "SCRUM-17", "SCRUM-38", "SCRUM-47"]
    with httpx.Client(timeout=20) as client:
        for key in jira_keys:
            c_url = f"{_base_url()}/issue/{key}/comment"
            r = client.get(c_url, headers=_auth_headers())
            if r.status_code == 200:
                comments = r.json().get("comments", [])
                latest_orion_comment = None
                for c in reversed(comments):
                    body_str = str(c.get("body", ""))
                    if "orion-rtm-alert" in body_str or "Orion Traceability Alert" in body_str:
                        latest_orion_comment = c
                        break
                if latest_orion_comment:
                    print(f"✓ Jira issue {key}: Found Orion audit comment (ID: {latest_orion_comment.get('id')}, Created: {latest_orion_comment.get('created')})")
                else:
                    print(f"- Jira issue {key}: {len(comments)} comments, none with Orion tag")
            else:
                print(f"x Jira issue {key}: Failed to fetch comments ({r.status_code})")

    print("\n==================================================================")
    print("STEP 5: Summary of Database Traceability Matrix Entries")
    print("==================================================================")
    async with get_session_context() as session:
        stmt = (
            select(TraceabilityMatrix, Requirement, TestCase)
            .join(Requirement, TraceabilityMatrix.requirement_id == Requirement.id)
            .join(TestCase, TraceabilityMatrix.test_case_id == TestCase.id)
            .where(TraceabilityMatrix.workspace_id == workspace_id)
            .order_by(Requirement.external_id)
        )
        res = (await session.execute(stmt)).all()
        print(f"Total Database Matrix Records: {len(res)}")
        status_counts = {"Covered": 0, "Partial": 0, "Drifted": 0}
        for tm, req, tc in res:
            st = tm.status.value if hasattr(tm.status, "value") else str(tm.status)
            status_counts[st] = status_counts.get(st, 0) + 1
        print("Status Breakdown:", status_counts)

        print("\nDrifted Tickets in Matrix:")
        for tm, req, tc in res:
            st = tm.status.value if hasattr(tm.status, "value") else str(tm.status)
            if st == "Drifted":
                print(f"  {req.external_id:<10} | {req.title:<45} | Risk: {tm.risk_score:.3f} | Test: {tc.function_name}")

        print("\nFirst 10 Covered Tickets in Matrix:")
        covered_list = [x for x in res if (x[0].status.value if hasattr(x[0].status, "value") else str(x[0].status)) == "Covered"]
        for tm, req, tc in covered_list[:10]:
            print(f"  {req.external_id:<10} | {req.title:<45} | Risk: {tm.risk_score:.3f} | Test: {tc.function_name}")

if __name__ == "__main__":
    asyncio.run(main())
