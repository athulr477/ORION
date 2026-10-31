"""Check GitHub App installation token and trigger PR analysis."""
import asyncio
import time
from pathlib import Path

import httpx
import jwt as pyjwt

key = Path("github-app.pem").read_text()
now = int(time.time())
payload = {"iat": now - 60, "exp": now + 600, "iss": "4930949"}
app_jwt = pyjwt.encode(payload, key, algorithm="RS256")

HEADERS = {
    "Authorization": f"Bearer {app_jwt}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        # List installations
        r = await client.get("https://api.github.com/app/installations", headers=HEADERS)
        print("Installations status:", r.status_code)
        installs = r.json()
        for inst in installs:
            acct = inst.get("account", {})
            print(f"  ID={inst['id']}  Account={acct.get('login')}  Target={inst.get('target_type')}")

        # Exchange for installation access token
        inst_id = 161384467
        r2 = await client.post(
            f"https://api.github.com/app/installations/{inst_id}/access_tokens",
            headers=HEADERS,
        )
        print("\nToken exchange status:", r2.status_code)
        data = r2.json()
        if r2.status_code == 201:
            token = data["token"]
            print("Got token:", token[:15] + "...")

            # Use the token to fetch PR files
            pr_files_r = await client.get(
                "https://api.github.com/repos/athulrj455/orion-sandbox/pulls/1/files",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            print("\nPR files status:", pr_files_r.status_code)
            files = pr_files_r.json()
            for f in files:
                print(f"  {f['filename']} ({f['status']})")
        else:
            print("Error:", data)

asyncio.run(main())
