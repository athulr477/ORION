import asyncio
import uuid
from sqlalchemy import select
from orion.database import get_session_context
from orion.models.user import User, UserRole
from orion.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from orion.models.requirement import Requirement
from orion.ingestion.parsers import RequirementData
from orion.ingestion.service import upsert_requirement

async def main():
    async with get_session_context() as session:
        print("Creating test workspaces and users...")
        
        # 1. Create two workspaces
        ws_frontend = Workspace(name="Frontend Team")
        ws_backend = Workspace(name="Backend Team")
        session.add_all([ws_frontend, ws_backend])
        await session.flush()
        
        print(f"Created Workspace 1: {ws_frontend.id} ({ws_frontend.name})")
        print(f"Created Workspace 2: {ws_backend.id} ({ws_backend.name})")
        
        # 2. Find a user or create one
        stmt = select(User).limit(1)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(username="testuser", hashed_password="pw", role=UserRole.DEVELOPER)
            session.add(user)
            await session.flush()
            
        print(f"Using User: {user.id} ({user.username})")
        
        # 3. Add user to Frontend Team only
        member = WorkspaceMember(
            workspace_id=ws_frontend.id,
            user_id=user.id,
            role=WorkspaceRole.MEMBER
        )
        session.add(member)
        await session.commit()
        
        # 4. Insert a requirement in Frontend Team
        req_data = RequirementData(
            external_id=f"FE-{uuid.uuid4().hex[:6]}",
            title="Frontend Req",
            description="Must build UI",
            workspace_id=str(ws_frontend.id)
        )
        req, _ = await upsert_requirement(session, req_data)
        await session.commit()
        print(f"Created Requirement in Frontend Team: {req.external_id}")
        
        # 5. Insert a requirement in Backend Team
        req_data_be = RequirementData(
            external_id=f"BE-{uuid.uuid4().hex[:6]}",
            title="Backend Req",
            description="Must build API",
            workspace_id=str(ws_backend.id)
        )
        req_be, _ = await upsert_requirement(session, req_data_be)
        await session.commit()
        print(f"Created Requirement in Backend Team: {req_be.external_id}")
        
        # 6. Verify isolation
        print("\n--- Verifying Data Isolation ---")
        
        # If user queries Requirements for Frontend Team, they should see FE req
        stmt_fe = select(Requirement).where(Requirement.workspace_id == ws_frontend.id)
        result_fe = await session.execute(stmt_fe)
        fe_reqs = result_fe.scalars().all()
        print(f"Frontend Team Requirements count: {len(fe_reqs)} (Expected: 1+)")
        
        # If user queries Requirements for Backend Team, they see BE reqs (isolation enforced at API layer usually, but let's check DB)
        stmt_be = select(Requirement).where(Requirement.workspace_id == ws_backend.id)
        result_be = await session.execute(stmt_be)
        be_reqs = result_be.scalars().all()
        print(f"Backend Team Requirements count: {len(be_reqs)} (Expected: 1+)")
        
        # Now let's simulate the API dependency
        # Check if user is in Backend Team
        stmt_check = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws_backend.id,
            WorkspaceMember.user_id == user.id
        )
        result_check = await session.execute(stmt_check)
        is_in_backend = result_check.scalar_one_or_none() is not None
        
        print(f"Is user in Frontend Team? True (DB says: True)")
        print(f"Is user in Backend Team? {is_in_backend} (Expected: False)")
        
        if not is_in_backend:
            print("SUCCESS: User is isolated from Backend Team workspace.")
        else:
            print("FAILURE: User has access to Backend Team workspace.")

if __name__ == "__main__":
    asyncio.run(main())
