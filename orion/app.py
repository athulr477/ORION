"""FastAPI application entry point for Orion."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orion.dashboard.routes import router as dashboard_router
from orion.github.routes import router as github_router
from orion.ingestion.routes import router as ingestion_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Orion",
    description="AI-powered Requirements Traceability Matrix engine",
    version="0.1.0",
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
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(github_router, prefix="/api/v1")  # Phase 9 — GitHub App


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "orion"}
