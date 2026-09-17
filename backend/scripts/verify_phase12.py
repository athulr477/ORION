import asyncio
import httpx

async def verify_auth():
    print("Verifying Phase 12 Auth & Audit Trail...\n")
    
    async with httpx.AsyncClient() as client:
        # 1. Try to access matrix without token
        resp = await client.get("http://localhost:8000/api/v1/dashboard/stats")
        print(f"GET /stats (No Token): {resp.status_code} (Expected 401)")
        assert resp.status_code == 401

        # 2. Login as QA Lead
        print("\nLogging in as QA Lead...")
        resp = await client.post("http://localhost:8000/api/v1/auth/token", data={
            "username": "qa.lead",
            "password": "password123"
        })
        print(f"Login response: {resp.status_code}")
        assert resp.status_code == 200
        qa_token = resp.json()["access_token"]
        print("Obtained JWT token!")

        # 3. Access stats with token
        resp = await client.get(
            "http://localhost:8000/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {qa_token}"}
        )
        print(f"GET /stats (With Token): {resp.status_code} (Expected 200)")
        assert resp.status_code == 200

        print("\nPhase 12 Backend Auth Verification Passed!")

if __name__ == "__main__":
    asyncio.run(verify_auth())
