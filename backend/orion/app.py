"""FastAPI application entry point for Orion."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orion.auth.routes import router as auth_router
from orion.config import settings
from orion.dashboard.routes import router as dashboard_router
from orion.github.routes import router as github_router
from orion.ingestion.routes import router as ingestion_router
from orion.integrations.routes import router as integrations_router
from orion.jira.routes import router as jira_router
from orion.queue.routes import router as queue_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register all task handlers FIRST so the worker can handle them
    # immediately when it starts polling. register_all() uses a lazy import
    # to avoid the tasks.py → worker.py circular import.
    from orion.queue.tasks import register_all
    from orion.queue.worker import worker

    register_all()
    asyncio.create_task(worker.start(poll_interval=2.0))
    logger.info("Embedded task worker started in background.")

    yield

    logger.info("Shutting down embedded task worker...")
    await worker.stop()


if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=1.0,
    )

app = FastAPI(
    title="Orion",
    description="AI-powered Requirements Traceability Matrix engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Vite dev server and common local origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/api/v1")  # Phase 12 — Authentication
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(github_router, prefix="/api/v1")  # Phase 9 — GitHub App
app.include_router(jira_router, prefix="/api/v1")  # Phase 11 — Jira REST API
app.include_router(queue_router, prefix="/api/v1")  # Phase 13 — Task Queue
app.include_router(integrations_router, prefix="/api/v1")  # Workspace Integrations


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "orion"}
