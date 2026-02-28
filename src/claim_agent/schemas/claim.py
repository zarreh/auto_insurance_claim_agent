"""Pydantic models for insurance claims."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ClaimInfo(BaseModel):
    """Incoming claim payload — validated at the API boundary."""

    claim_number: str = Field(..., description="Unique claim identifier (e.g. CLM-001)")
    policy_number: str = Field(..., description="Policy number to validate against records")
    claimant_name: str = Field(..., description="Full name of the claimant")
    date_of_loss: date = Field(..., description="Date the loss / incident occurred")
    loss_description: str = Field(..., description="Free-text description of the loss event")
    estimated_repair_cost: float = Field(
        ..., gt=0, description="Claimant's estimated repair cost in USD"
    )
    vehicle_details: Optional[str] = Field(
        default=None, description="Vehicle make/model/year (optional)"
    )

    model_config = {"json_schema_extra": {
        "examples": [
            {
                "claim_number": "CLM-001",
                "policy_number": "PN-2",
                "claimant_name": "Jane Doe",
                "date_of_loss": "2026-02-15",
                "loss_description": "Rear-end collision at intersection, bumper and taillight damage",
                "estimated_repair_cost": 3500.00,
                "vehicle_details": "2022 Toyota Camry",
            }
        ]
    }}


class ClaimDecision(BaseModel):
    """Final coverage decision returned by the pipeline."""

    claim_number: str = Field(..., description="Claim identifier this decision refers to")
    covered: bool = Field(..., description="Whether the claim is covered under the policy")
    deductible: float = Field(
        default=0.0, ge=0, description="Applicable deductible amount in USD"
    )
    recommended_payout: float = Field(
        default=0.0, ge=0, description="Recommended settlement payout in USD"
    )
    notes: Optional[str] = Field(
        default=None, description="Explanatory notes (rejection reason, coverage details, etc.)"
    )
