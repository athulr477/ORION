"""Database health check script."""
import asyncio
from sqlalchemy import text
from orion.database import async_session_factory

async def db_health():
    async with async_session_factory() as s:
        # pgvector extension
        r = await s.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
        pgv = r.scalar()
        print(f"pgvector: {pgv}")

        # Table counts
        tables = ["requirements", "test_cases", "traceability_matrix", "workspaces", "workspace_members", "users", "task_jobs"]
        for t in tables:
            r = await s.execute(text(f"SELECT count(*) FROM {t}"))
            c = r.scalar()
            print(f"  {t}: {c} rows")

        # DB size
        r = await s.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
        print(f"  Database size: {r.scalar()}")

        # Check for null embeddings
        r = await s.execute(text("SELECT count(*) FROM requirements WHERE embedding IS NULL"))
        null_emb = r.scalar()
        print(f"  Requirements with NULL embedding: {null_emb}")

        r = await s.execute(text("SELECT count(*) FROM test_cases WHERE embedding IS NULL"))
        null_test_emb = r.scalar()
        print(f"  Test cases with NULL embedding: {null_test_emb}")

        # Traceability status distribution
        r = await s.execute(text("SELECT status, count(*) FROM traceability_matrix GROUP BY status ORDER BY status"))
        rows = r.fetchall()
        print("  Traceability status distribution:")
        for row in rows:
            print(f"    {row[0]}: {row[1]}")

asyncio.run(db_health())
