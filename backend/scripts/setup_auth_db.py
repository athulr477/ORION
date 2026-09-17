import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from orion.auth.security import get_password_hash
from orion.database import Base, engine
from orion.models.audit_log import AuditLog
from orion.models.traceability_matrix import TraceabilityMatrix
from orion.models.user import User, UserRole


async def setup_auth_db():
    print("Setting up Authentication and Audit tables...")
    
    async with engine.begin() as conn:
        print("Creating tables (if they do not exist)...")
        await conn.run_sync(Base.metadata.create_all)
        
        print("Adding is_manually_overridden to traceability_matrix...")
        try:
            await conn.execute(text("ALTER TABLE traceability_matrix ADD COLUMN is_manually_overridden BOOLEAN DEFAULT FALSE NOT NULL;"))
        except Exception as e:
            if "already exists" in str(e) or "DuplicateColumn" in str(e) or "42701" in str(e):
                print("Column already exists.")
            else:
                print(f"Error adding column (maybe already exists): {e}")

    async with AsyncSession(engine) as session:
        print("Seeding default users...")
        qa_lead = User(
            username="qa.lead",
            hashed_password=get_password_hash("password123"),
            role=UserRole.QA_LEAD,
        )
        developer = User(
            username="alex.dev",
            hashed_password=get_password_hash("password123"),
            role=UserRole.DEVELOPER,
        )
        
        session.add_all([qa_lead, developer])
        try:
            await session.commit()
            print("Users seeded successfully!")
            print("QA Lead: qa.lead / password123")
            print("Developer: alex.dev / password123")
        except Exception as e:
            if "duplicate key" in str(e) or "UniqueViolation" in str(e):
                print("Users already seeded.")
            else:
                print(f"Error seeding users: {e}")

if __name__ == "__main__":
    asyncio.run(setup_auth_db())
