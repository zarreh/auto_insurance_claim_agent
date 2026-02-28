"""FastAPI application factory.

``create_app`` builds a fully configured ``FastAPI`` instance with:

* CORS middleware
* Request-logging / exception-handling middleware
* Claim-processing routes
* Lifespan manager for startup (PDF ingestion) and shutdown
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from claim_agent.api.middleware import ExceptionHandlerMiddleware, RequestLoggingMiddleware
from claim_agent.api.routes.claims import router as claims_router
from claim_agent.core.ingestion import ingest_policy_pdf
from claim_agent.logging.setup import setup_logging
from claim_agent.pipelines.factory import create_pipeline

if TYPE_CHECKING:
    from omegaconf import DictConfig


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle for the FastAPI application."""
    cfg: DictConfig = app.state.cfg

    # ── Startup: ingest policy PDF if needed ─────────────────────────────
    pdf_path = Path(cfg.data.policy_pdf)
    if pdf_path.exists():
        try:
            ingest_policy_pdf(
                pdf_path=str(pdf_path),
                chroma_persist_dir=cfg.data.chroma_persist_dir,
                collection_name=cfg.vectordb.collection_name,
                embedding_model=cfg.vectordb.embedding_model,
                chunk_size=cfg.vectordb.chunk_size,
                chunk_overlap=cfg.vectordb.chunk_overlap,
            )
        except Exception as exc:
            logger.warning("PDF ingestion skipped or failed: {e}", e=exc)
    else:
        logger.info("No policy PDF at {path} — skipping ingestion", path=pdf_path)

    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_app(cfg: DictConfig) -> FastAPI:
    """Build and return a fully configured :class:`FastAPI` application.

    Parameters
    ----------
    cfg:
        The merged Hydra configuration.

    Returns
    -------
    FastAPI
        Ready-to-run application instance.
    """
    # ── Logging ──────────────────────────────────────────────────────────
    setup_logging(cfg.logging)

    # ── App ──────────────────────────────────────────────────────────────
    app = FastAPI(
        title="Claim Processing Agent",
        description="Agentic RAG Insurance Claim Processor",
        version="1.0.0",
        lifespan=_lifespan,
    )

    # Store config in app state for access in lifespan & routes
    app.state.cfg = cfg

    # ── Pipeline ─────────────────────────────────────────────────────────
    pipeline = create_pipeline(cfg)
    app.state.pipeline = pipeline
    logger.info("Pipeline registered: {type}", type=cfg.pipeline.type)

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cfg.server.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware (outermost = first to run) ─────────────────────
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(claims_router, prefix="/api/v1")

    return app
