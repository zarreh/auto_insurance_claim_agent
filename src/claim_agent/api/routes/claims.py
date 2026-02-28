"""Claim-processing API routes.

Endpoints
---------
POST /api/v1/claims/process
    Accept a ``ClaimInfo`` JSON body, run the pipeline, return ``ClaimDecision``.

GET  /api/v1/health
    Lightweight health-check.

GET  /api/v1/pipelines
    List available pipeline types.
"""

from __future__ import annotations

import traceback

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import ValidationError

from claim_agent.schemas.claim import ClaimDecision, ClaimInfo

router = APIRouter()

# Available pipeline implementations
_PIPELINE_TYPES = ["langchain", "smolagents"]


# ---------------------------------------------------------------------------
# POST /claims/process
# ---------------------------------------------------------------------------

@router.post(
    "/claims/process",
    response_model=ClaimDecision,
    summary="Process an insurance claim",
    description="Submit a claim for processing through the configured pipeline.",
)
async def process_claim(claim: ClaimInfo, request: Request) -> ClaimDecision:
    """Validate and process a single insurance claim.

    The active pipeline (LangChain or Smolagents) is resolved at startup and
    stored in ``app.state.pipeline``.
    """
    pipeline = request.app.state.pipeline
    claim_num = claim.claim_number
    logger.info("API: received claim {num}", num=claim_num)

    try:
        decision = pipeline.process_claim(claim)
    except ValidationError as exc:
        logger.warning(
            "Validation error processing claim {num}: {err}",
            num=claim_num,
            err=exc,
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(
            "Pipeline error processing claim {num}: {err}\n{tb}",
            num=claim_num,
            err=exc,
            tb=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {exc}",
        ) from exc

    logger.info(
        "API: claim {num} processed — covered={cov}",
        num=claim_num,
        cov=decision.covered,
    )
    return decision


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    summary="Health check",
    description="Returns service health status and active pipeline type.",
)
async def health(request: Request) -> dict:
    """Return a lightweight health-check response."""
    pipeline_type = request.app.state.cfg.pipeline.type
    return {"status": "healthy", "pipeline": pipeline_type}


# ---------------------------------------------------------------------------
# GET /pipelines
# ---------------------------------------------------------------------------

@router.get(
    "/pipelines",
    summary="Available pipelines",
    description="Returns the list of available pipeline implementations.",
)
async def list_pipelines() -> dict:
    """Return the list of supported pipeline types."""
    return {"pipelines": _PIPELINE_TYPES}
