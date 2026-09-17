"""Verify Phase 13: Asynchronous Task Queue & Worker.

Enqueues a simulated task and runs the worker in the background
to ensure that the task reaches SUCCESS and records progress.
"""

import asyncio
import logging
from uuid import UUID

from orion.database import get_session_context
from orion.queue.broker import enqueue_task, get_task_status
from orion.models.task_job import TaskStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Verifying Phase 13 Task Queue subsystem...")
    
    # Payload for simulation task
    payload = {
        "requirement_external_id": "REQ-PHASE13",
        "requirement_title": "Async Worker Support",
        "requirement_description": "The system must process heavy tasks asynchronously in the background. The queue must track progress.",
        "test_function_name": "test_background_worker",
        "test_file_path": "tests/test_worker.py",
        "test_source_code": "def test_background_worker():\n    assert worker.is_running() == True"
    }
    
    # Start the worker loop in the background
    from orion.queue.worker import worker
    import orion.queue.tasks  # register handlers
    
    worker_task = asyncio.create_task(worker.start(poll_interval=1.0))
    
    # 1. Enqueue task
    task_id = None
    async with get_session_context() as session:
        task_id = await enqueue_task(session, "simulate_run", payload)
        logger.info("Enqueued task %s", task_id)
        
    if not task_id:
        logger.error("Failed to enqueue task.")
        await worker.stop()
        return

    # 2. Poll task status
    logger.info("Polling task status...")
    max_retries = 30
    final_status = None
    
    for i in range(max_retries):
        async with get_session_context() as session:
            job = await get_task_status(session, task_id)
            if job:
                logger.info("  [%d] Status: %s, Progress: %.2f, Step: %s", i, job.status, job.progress, job.current_step)
                if job.status in (TaskStatus.SUCCESS.value, TaskStatus.FAILURE.value):
                    final_status = job.status
                    break
                    
        await asyncio.sleep(1.0)
        
    # 3. Stop the worker
    await worker.stop()
    await worker_task
    
    if final_status == TaskStatus.SUCCESS.value:
        logger.info("Phase 13 Verification SUCCESS! Background task completed normally.")
    elif final_status == TaskStatus.FAILURE.value:
        logger.error("Phase 13 Verification FAILED! Task failed.")
        raise SystemExit(1)
    else:
        logger.error("Phase 13 Verification TIMED OUT. Task did not complete.")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
