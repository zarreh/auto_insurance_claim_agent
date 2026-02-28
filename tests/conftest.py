"""Shared fixtures for the claim-processing agent test suite."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from omegaconf import OmegaConf

from claim_agent.schemas.claim import ClaimDecision, ClaimInfo

# ---------------------------------------------------------------------------
# ClaimInfo fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_claim() -> ClaimInfo:
    """A valid claim that should pass all validation checks (PN-2: active, no dues)."""
    return ClaimInfo(
        claim_number="CLM-TEST-001",
        policy_number="PN-2",
        claimant_name="Jane Doe",
        date_of_loss=date(2026, 2, 15),
        loss_description="Rear-end collision at intersection, bumper and taillight damage",
        estimated_repair_cost=3500.00,
        vehicle_details="2022 Toyota Camry",
    )


@pytest.fixture()
def invalid_policy_claim() -> ClaimInfo:
    """Claim with a policy number that does not exist in the CSV."""
    return ClaimInfo(
        claim_number="CLM-TEST-002",
        policy_number="PN-99",
        claimant_name="John Nobody",
        date_of_loss=date(2026, 3, 1),
        loss_description="Fender bender in parking lot",
        estimated_repair_cost=1200.00,
    )


@pytest.fixture()
def expired_policy_claim() -> ClaimInfo:
    """Claim against PN-1 whose coverage ended 2022-12-31."""
    return ClaimInfo(
        claim_number="CLM-TEST-003",
        policy_number="PN-1",
        claimant_name="Alice Expired",
        date_of_loss=date(2026, 1, 10),
        loss_description="Windshield cracked by road debris",
        estimated_repair_cost=800.00,
    )


@pytest.fixture()
def dues_remaining_claim() -> ClaimInfo:
    """Claim against PN-3 which has outstanding premium dues."""
    return ClaimInfo(
        claim_number="CLM-TEST-004",
        policy_number="PN-3",
        claimant_name="Bob Dues",
        date_of_loss=date(2021, 8, 1),
        loss_description="Hail damage to roof and hood",
        estimated_repair_cost=5000.00,
    )


@pytest.fixture()
def inflated_cost_claim() -> ClaimInfo:
    """Claim with a suspiciously high estimated repair cost."""
    return ClaimInfo(
        claim_number="CLM-TEST-005",
        policy_number="PN-4",
        claimant_name="Chuck Inflated",
        date_of_loss=date(2026, 6, 1),
        loss_description="Minor scratch on passenger door",
        estimated_repair_cost=15000.00,
        vehicle_details="2020 Honda Civic",
    )


# ---------------------------------------------------------------------------
# Mock CSV data fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def coverage_csv(tmp_path: Path) -> str:
    """Write a small coverage CSV and return its path."""
    csv_file = tmp_path / "coverage_data.csv"
    rows = [
        ["policy_number", "premium_dues_remaining", "coverage_start_date", "coverage_end_date"],
        ["PN-1", "False", "2022-01-01", "2022-12-31"],
        ["PN-2", "False", "2023-01-01", "2027-01-01"],
        ["PN-3", "True", "2021-06-01", "2022-06-01"],
        ["PN-4", "False", "2023-05-01", "2026-12-31"],
    ]
    with csv_file.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return str(csv_file)


# ---------------------------------------------------------------------------
# Hydra config fixture (test overrides)
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_cfg(tmp_path: Path, coverage_csv: str) -> Any:
    """Return a minimal OmegaConf DictConfig with test overrides."""
    chroma_dir = str(tmp_path / "chroma_db")

    cfg_dict = {
        "pipeline": {
            "type": "langchain",
            "graph": {"max_iterations": 10, "recursion_limit": 25},
            "price_check": {"inflation_threshold": 0.40},
            "agent": {"max_steps": 10, "verbosity_level": 0},
        },
        "llm": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 4096,
            "api_key": "test-key",
        },
        "vectordb": {
            "collection_name": "test_policy_chunks",
            "embedding_model": "all-MiniLM-L6-v2",
            "n_results": 5,
            "chunk_size": 500,
            "chunk_overlap": 50,
        },
        "data": {
            "coverage_csv": coverage_csv,
            "policy_pdf": str(tmp_path / "policy.pdf"),
            "chroma_persist_dir": chroma_dir,
        },
        "logging": {
            "level": "WARNING",
            "colored": False,
            "format": "pretty",
        },
        "server": {
            "host": "127.0.0.1",
            "port": 8000,
            "debug": False,
            "cors_origins": ["http://localhost:8501"],
        },
    }
    return OmegaConf.create(cfg_dict)


# ---------------------------------------------------------------------------
# Sample ClaimDecision
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_decision() -> ClaimDecision:
    """A pre-built ClaimDecision for route tests."""
    return ClaimDecision(
        claim_number="CLM-TEST-001",
        covered=True,
        deductible=500.0,
        recommended_payout=3000.0,
        notes="Claim approved based on policy coverage.",
    )


# ---------------------------------------------------------------------------
# Mock pipeline
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_pipeline(sample_decision: ClaimDecision) -> MagicMock:
    """Return a MagicMock whose ``process_claim`` returns *sample_decision*."""
    pipeline = MagicMock()
    pipeline.process_claim.return_value = sample_decision
    return pipeline
