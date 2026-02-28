"""Claim validation against coverage_data.csv policy records."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from loguru import logger

from claim_agent.schemas.claim import ClaimInfo


def validate_claim(claim: ClaimInfo, csv_path: str) -> tuple[bool, str]:
    """Validate a claim against the policy records CSV.

    Checks performed (in order):
    1. Policy number exists in the records.
    2. No outstanding premium dues (``premium_dues_remaining == False``).
    3. Date of loss falls within the coverage period.

    Parameters
    ----------
    claim:
        The parsed claim to validate.
    csv_path:
        Path to the ``coverage_data.csv`` file.

    Returns
    -------
    tuple[bool, str]
        ``(is_valid, reason)`` — *reason* is ``"valid"`` on success or a
        descriptive failure message.
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        msg = f"Coverage data file not found: {csv_path}"
        logger.error(msg)
        return False, msg

    df = pd.read_csv(csv_file)
    logger.debug(
        "Loaded coverage data — {n} policies",
        n=len(df),
    )

    # ── 1. Policy exists ────────────────────────────────────────────────
    policy_row = df[df["policy_number"] == claim.policy_number]
    if policy_row.empty:
        msg = f"Policy {claim.policy_number} not found in records"
        logger.warning(msg, claim_number=claim.claim_number)
        return False, msg

    record = policy_row.iloc[0]

    # ── 2. No outstanding premium dues ──────────────────────────────────
    # CSV stores the value as a string "True"/"False"; coerce to bool.
    dues_remaining = str(record["premium_dues_remaining"]).strip().lower() == "true"
    if dues_remaining:
        msg = (
            f"Policy {claim.policy_number} has outstanding premium dues — "
            "claim cannot be processed"
        )
        logger.warning(msg, claim_number=claim.claim_number)
        return False, msg

    # ── 3. Date of loss within coverage period ──────────────────────────
    coverage_start = _parse_date(record["coverage_start_date"])
    coverage_end = _parse_date(record["coverage_end_date"])

    if not (coverage_start <= claim.date_of_loss <= coverage_end):
        msg = (
            f"Date of loss {claim.date_of_loss} is outside the coverage period "
            f"({coverage_start} to {coverage_end}) for policy {claim.policy_number}"
        )
        logger.warning(msg, claim_number=claim.claim_number)
        return False, msg

    # ── All checks passed ───────────────────────────────────────────────
    logger.info(
        "Claim {claim_number} passed validation for policy {policy}",
        claim_number=claim.claim_number,
        policy=claim.policy_number,
    )
    return True, "valid"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str | date) -> date:
    """Coerce a string or date value to ``datetime.date``."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())
