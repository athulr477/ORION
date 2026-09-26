"""Background worker engine."""

import asyncio
import datetime
import logging
import traceback
import uuid
from collections.abc import Callable

from orion.database import get_session_context
from orion.models.task_job import TaskJob, TaskStatus
from orion.queue.broker import claim_next_task

logger = logging.getLogger(__name__)


class WorkerEngine:
    """A background worker engine that polls the database for tasks."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable] = {}
        self._running = False
        self._loop_task: asyncio.Task | None = None

    def register(self, task_type: str) -> Callable:
        """Register a handler function for a specific task type as a decorator."""
        def decorator(handler: Callable) -> Callable:
            self.handlers[task_type] = handler
            logger.info("Registered task handler for '%s'", task_type)
            return handler
        return decorator

    async def start(self, poll_interval: float = 2.0) -> None:
        """Start the worker polling loop."""
        _ensure_tasks_registered()
        if self._running:
            return
        
        self._running = True
        logger.info("Worker engine started (poll interval: %ss)", poll_interval)
        
        while self._running:
            try:
                await self._poll_and_execute()
            except Exception as e:
                logger.error("Worker engine encountered an error: %s", e, exc_info=True)
            
            await asyncio.sleep(poll_interval)

    async def stop(self) -> None:
        """Stop the worker polling loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        logger.info("Worker engine stopped")

    async def _poll_and_execute(self) -> None:
        """Poll for one task and execute it if found."""
        async with get_session_context() as session:
            # Step 1: Claim task
            job = await claim_next_task(session)
            if not job:
                return  # No pending tasks

            await session.commit()
            logger.info("Worker claimed task %s (type: %s)", job.id, job.task_type)

        # Step 2: Execute task in its own transaction context
        # We fetch it again just to be isolated from the claim transaction
        async with get_session_context() as exec_session:
            # Re-fetch job
            from sqlalchemy import select
            stmt = select(TaskJob).where(TaskJob.id == job.id)
            result = await exec_session.execute(stmt)
            active_job = result.scalar_one()
            
            handler = self.handlers.get(active_job.task_type)
            if not handler:
                error_msg = f"No handler registered for task type '{active_job.task_type}'"
                logger.error(error_msg)
                await self._mark_failed(active_job.id, error_msg)
                return

            try:
                # Provide a callback for handlers to update progress in real time.
                # Uses its own short-lived session so it never interferes with the
                # execution session's in-progress transaction.
                async def update_progress(progress: float, step: str) -> None:
                    async with get_session_context() as progress_session:
                        from sqlalchemy import update as sa_update
                        await progress_session.execute(
                            sa_update(TaskJob)
                            .where(TaskJob.id == active_job.id)
                            .values(progress=progress, current_step=step)
                        )
                        await progress_session.commit()
                
                # Execute the handler
                result_data = await handler(active_job.payload, exec_session, update_progress)
                
                # Mark Success — use a fresh update to avoid stale ORM state after
                # the service may have already committed exec_session internally.
                from sqlalchemy import update as sa_update
                await exec_session.execute(
                    sa_update(TaskJob)
                    .where(TaskJob.id == active_job.id)
                    .values(
                        status=TaskStatus.SUCCESS,
                        progress=1.0,
                        current_step="Completed",
                        result=result_data,
                        completed_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                    )
                )
                await exec_session.commit()
                logger.info("Task %s completed successfully", active_job.id)
                
            except Exception as e:
                tb = traceback.format_exc()
                logger.exception("Task %s failed: %s", active_job.id, e)
                await self._mark_failed(active_job.id, tb)

    async def _mark_failed(self, job_id: uuid.UUID, error_message: str) -> None:
        """Mark a job as failed using a dedicated session, so it always succeeds
        even if the execution session is in a broken/rolled-back state."""
        try:
            from sqlalchemy import update as sa_update
            async with get_session_context() as session:
                await session.execute(
                    sa_update(TaskJob)
                    .where(TaskJob.id == job_id)
                    .values(
                        status=TaskStatus.FAILURE,
                        error_message=error_message,
                        completed_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                    )
                )
                await session.commit()
        except Exception as e:
            logger.error("Failed to mark task %s as failed: %s", job_id, e)


# Global worker engine instance
worker = WorkerEngine()


def _ensure_tasks_registered() -> None:
    try:
        import orion.queue.tasks  # noqa: F401
    except Exception as e:
        logger.warning("Could not auto-register queue tasks: %s", e)


_ensure_tasks_registered()


async def main() -> None:
    """CLI entry point for running a standalone worker process."""
    _ensure_tasks_registered()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
