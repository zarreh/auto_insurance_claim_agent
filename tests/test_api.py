"""Integration tests for the FastAPI application.

Uses ``httpx.AsyncClient`` (via ``pytest-asyncio``) with a mocked pipeline so
no LLM or vector-store calls are needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from omegaconf import DictConfig

from claim_agent.schemas.claim import ClaimInfo

# ---------------------------------------------------------------------------
# App fixture (bypass heavy lifespan)
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(test_cfg: DictConfig, mock_pipeline: MagicMock) -> FastAPI:
    """Build a FastAPI app with the pipeline mocked out."""
    from claim_agent.api.routes.claims import router as claims_router

    _app = FastAPI(title="test")
    _app.state.cfg = test_cfg
    _app.state.pipeline = mock_pipeline
    _app.include_router(claims_router, prefix="/api/v1")
    return _app


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "pipeline" in body


class TestPipelinesEndpoint:
    @pytest.mark.asyncio
    async def test_list_pipelines(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/pipelines")
        assert resp.status_code == 200
        body = resp.json()
        assert "langchain" in body["pipelines"]
        assert "smolagents" in body["pipelines"]


class TestProcessClaim:
    @pytest.mark.asyncio
    async def test_valid_claim_returns_decision(
        self, client: AsyncClient, valid_claim: ClaimInfo
    ) -> None:
        payload = valid_claim.model_dump(mode="json")
        resp = await client.post("/api/v1/claims/process", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["claim_number"] == "CLM-TEST-001"
        assert body["covered"] is True
        assert body["deductible"] == 500.0

    @pytest.mark.asyncio
    async def test_invalid_payload_returns_422(self, client: AsyncClient) -> None:
        """Missing required fields should trigger Pydantic validation error."""
        resp = await client.post(
            "/api/v1/claims/process",
            json={"claim_number": "X"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_pipeline_error_returns_500(
        self,
        client: AsyncClient,
        valid_claim: ClaimInfo,
        mock_pipeline: MagicMock,
    ) -> None:
        """If the pipeline raises, the route should return a 500."""
        mock_pipeline.process_claim.side_effect = RuntimeError("boom")
        payload = valid_claim.model_dump(mode="json")
        resp = await client.post("/api/v1/claims/process", json=payload)
        assert resp.status_code == 500
        assert "boom" in resp.json()["detail"]
