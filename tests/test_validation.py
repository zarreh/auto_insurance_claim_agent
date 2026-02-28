"""Tests for claim validation logic against coverage CSV records."""

from __future__ import annotations

from datetime import date

from claim_agent.core.validation import validate_claim
from claim_agent.schemas.claim import ClaimInfo


class TestValidation:
    """Test the four validation paths: not found, dues, expired, valid."""

    # ── 1. Policy not found ─────────────────────────────────────────────

    def test_policy_not_found(
        self, invalid_policy_claim: ClaimInfo, coverage_csv: str
    ) -> None:
        is_valid, reason = validate_claim(invalid_policy_claim, coverage_csv)
        assert is_valid is False
        assert "PN-99" in reason
        assert "not found" in reason.lower()

    # ── 2. Outstanding premium dues ─────────────────────────────────────

    def test_outstanding_dues(
        self, dues_remaining_claim: ClaimInfo, coverage_csv: str
    ) -> None:
        is_valid, reason = validate_claim(dues_remaining_claim, coverage_csv)
        assert is_valid is False
        assert "outstanding" in reason.lower() or "dues" in reason.lower()

    # ── 3. Expired coverage ─────────────────────────────────────────────

    def test_expired_coverage(
        self, expired_policy_claim: ClaimInfo, coverage_csv: str
    ) -> None:
        is_valid, reason = validate_claim(expired_policy_claim, coverage_csv)
        assert is_valid is False
        assert "outside" in reason.lower() or "coverage period" in reason.lower()

    # ── 4. Valid policy passes ──────────────────────────────────────────

    def test_valid_claim_passes(
        self, valid_claim: ClaimInfo, coverage_csv: str
    ) -> None:
        is_valid, reason = validate_claim(valid_claim, coverage_csv)
        assert is_valid is True
        assert reason == "valid"

    # ── Edge: CSV file not found ────────────────────────────────────────

    def test_csv_not_found(self, valid_claim: ClaimInfo) -> None:
        is_valid, reason = validate_claim(valid_claim, "/nonexistent/coverage.csv")
        assert is_valid is False
        assert "not found" in reason.lower()

    # ── Edge: Date exactly on boundary ──────────────────────────────────

    def test_date_on_coverage_start(self, coverage_csv: str) -> None:
        claim = ClaimInfo(
            claim_number="CLM-EDGE-START",
            policy_number="PN-2",
            claimant_name="Edge Test",
            date_of_loss=date(2023, 1, 1),  # exactly coverage_start_date
            loss_description="Test",
            estimated_repair_cost=100.0,
        )
        is_valid, reason = validate_claim(claim, coverage_csv)
        assert is_valid is True
        assert reason == "valid"

    def test_date_on_coverage_end(self, coverage_csv: str) -> None:
        claim = ClaimInfo(
            claim_number="CLM-EDGE-END",
            policy_number="PN-2",
            claimant_name="Edge Test",
            date_of_loss=date(2027, 1, 1),  # exactly coverage_end_date
            loss_description="Test",
            estimated_repair_cost=100.0,
        )
        is_valid, reason = validate_claim(claim, coverage_csv)
        assert is_valid is True
        assert reason == "valid"

    def test_date_one_day_after_end(self, coverage_csv: str) -> None:
        claim = ClaimInfo(
            claim_number="CLM-EDGE-AFTER",
            policy_number="PN-2",
            claimant_name="Edge Test",
            date_of_loss=date(2027, 1, 2),  # one day after coverage_end_date
            loss_description="Test",
            estimated_repair_cost=100.0,
        )
        is_valid, reason = validate_claim(claim, coverage_csv)
        assert is_valid is False
        assert "outside" in reason.lower()
