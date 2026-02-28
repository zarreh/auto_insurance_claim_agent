"""Tests for Pydantic schemas: ClaimInfo, ClaimDecision, PolicyQueries, PolicyRecommendation."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from claim_agent.schemas.claim import ClaimDecision, ClaimInfo
from claim_agent.schemas.policy import PolicyQueries, PolicyRecommendation

# ═══════════════════════════════════════════════════════════════════════
# ClaimInfo
# ═══════════════════════════════════════════════════════════════════════

class TestClaimInfo:
    """Test suite for :class:`ClaimInfo`."""

    def test_valid_claim(self, valid_claim: ClaimInfo) -> None:
        assert valid_claim.claim_number == "CLM-TEST-001"
        assert valid_claim.policy_number == "PN-2"
        assert valid_claim.estimated_repair_cost == 3500.00
        assert valid_claim.vehicle_details == "2022 Toyota Camry"

    def test_optional_vehicle_details(self) -> None:
        claim = ClaimInfo(
            claim_number="CLM-X",
            policy_number="PN-1",
            claimant_name="Test",
            date_of_loss=date(2026, 1, 1),
            loss_description="Scratch",
            estimated_repair_cost=100.0,
        )
        assert claim.vehicle_details is None

    def test_date_of_loss_from_string(self) -> None:
        data = {
            "claim_number": "CLM-X",
            "policy_number": "PN-1",
            "claimant_name": "Test",
            "date_of_loss": "2026-03-15",
            "loss_description": "Scratch",
            "estimated_repair_cost": 500.0,
        }
        claim = ClaimInfo(**data)
        assert claim.date_of_loss == date(2026, 3, 15)

    def test_repair_cost_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="greater_than"):
            ClaimInfo(
                claim_number="CLM-X",
                policy_number="PN-1",
                claimant_name="Test",
                date_of_loss=date(2026, 1, 1),
                loss_description="Scratch",
                estimated_repair_cost=0,  # not > 0
            )

    def test_negative_repair_cost(self) -> None:
        with pytest.raises(ValidationError):
            ClaimInfo(
                claim_number="CLM-X",
                policy_number="PN-1",
                claimant_name="Test",
                date_of_loss=date(2026, 1, 1),
                loss_description="Scratch",
                estimated_repair_cost=-500,
            )

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            ClaimInfo(
                claim_number="CLM-X",
                # policy_number missing
                claimant_name="Test",
                date_of_loss=date(2026, 1, 1),
                loss_description="Scratch",
                estimated_repair_cost=100.0,
            )

    def test_json_round_trip(self, valid_claim: ClaimInfo) -> None:
        json_str = valid_claim.model_dump_json()
        restored = ClaimInfo.model_validate_json(json_str)
        assert restored == valid_claim

    def test_dict_round_trip(self, valid_claim: ClaimInfo) -> None:
        data = valid_claim.model_dump(mode="json")
        restored = ClaimInfo(**data)
        assert restored == valid_claim


# ═══════════════════════════════════════════════════════════════════════
# ClaimDecision
# ═══════════════════════════════════════════════════════════════════════

class TestClaimDecision:
    """Test suite for :class:`ClaimDecision`."""

    def test_valid_decision(self, sample_decision: ClaimDecision) -> None:
        assert sample_decision.covered is True
        assert sample_decision.deductible == 500.0
        assert sample_decision.recommended_payout == 3000.0

    def test_defaults(self) -> None:
        decision = ClaimDecision(claim_number="CLM-1", covered=False)
        assert decision.deductible == 0.0
        assert decision.recommended_payout == 0.0
        assert decision.notes is None

    def test_deductible_cannot_be_negative(self) -> None:
        with pytest.raises(ValidationError, match="greater_than_equal"):
            ClaimDecision(
                claim_number="CLM-1",
                covered=True,
                deductible=-10,
            )

    def test_payout_cannot_be_negative(self) -> None:
        with pytest.raises(ValidationError, match="greater_than_equal"):
            ClaimDecision(
                claim_number="CLM-1",
                covered=True,
                recommended_payout=-100,
            )

    def test_json_round_trip(self, sample_decision: ClaimDecision) -> None:
        json_str = sample_decision.model_dump_json()
        restored = ClaimDecision.model_validate_json(json_str)
        assert restored == sample_decision


# ═══════════════════════════════════════════════════════════════════════
# PolicyQueries
# ═══════════════════════════════════════════════════════════════════════

class TestPolicyQueries:
    """Test suite for :class:`PolicyQueries`."""

    def test_valid_queries(self) -> None:
        pq = PolicyQueries(queries=["What is the deductible?", "Collision coverage limits"])
        assert len(pq.queries) == 2

    def test_empty_queries_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PolicyQueries(queries=[])

    def test_single_query(self) -> None:
        pq = PolicyQueries(queries=["deductible amount"])
        assert len(pq.queries) == 1


# ═══════════════════════════════════════════════════════════════════════
# PolicyRecommendation
# ═══════════════════════════════════════════════════════════════════════

class TestPolicyRecommendation:
    """Test suite for :class:`PolicyRecommendation`."""

    def test_valid_recommendation(self) -> None:
        rec = PolicyRecommendation(
            policy_section="Section 4 — Collision",
            recommendation_summary="Claim is covered under collision coverage.",
            deductible=500.0,
            settlement_amount=3000.0,
        )
        assert rec.policy_section == "Section 4 — Collision"
        assert rec.deductible == 500.0

    def test_optional_fields_default_none(self) -> None:
        rec = PolicyRecommendation(
            policy_section="Section 1",
            recommendation_summary="Summary",
        )
        assert rec.deductible is None
        assert rec.settlement_amount is None

    def test_negative_deductible_rejected(self) -> None:
        with pytest.raises(ValidationError, match="greater_than_equal"):
            PolicyRecommendation(
                policy_section="Section 1",
                recommendation_summary="Summary",
                deductible=-10,
            )

    def test_negative_settlement_rejected(self) -> None:
        with pytest.raises(ValidationError, match="greater_than_equal"):
            PolicyRecommendation(
                policy_section="Section 1",
                recommendation_summary="Summary",
                settlement_amount=-100,
            )
