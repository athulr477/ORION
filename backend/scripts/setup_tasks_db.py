"""Create task_jobs table for Phase 13 background worker."""

import asyncio
import logging

from orion.database import engine, Base
from orion.models.task_job import TaskJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_tasks_db() -> None:
    """Create task_jobs table."""
    logger.info("Connecting to database...")
    async with engine.begin() as conn:
        logger.info("Creating task_jobs table if not exists...")
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Tasks database setup complete.")

if __name__ == "__main__":
    asyncio.run(setup_tasks_db())
