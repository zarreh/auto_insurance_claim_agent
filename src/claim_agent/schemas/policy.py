"""Pydantic models for policy-related intermediate results."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PolicyQueries(BaseModel):
    """LLM-generated search queries for policy retrieval."""

    queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Targeted search queries to find relevant policy sections",
    )


class PolicyRecommendation(BaseModel):
    """LLM-generated coverage recommendation based on claim + policy text."""

    policy_section: str = Field(
        ..., description="The policy section that applies to this claim"
    )
    recommendation_summary: str = Field(
        ..., description="Human-readable summary of the coverage recommendation"
    )
    deductible: Optional[float] = Field(
        default=None, ge=0, description="Applicable deductible amount in USD"
    )
    settlement_amount: Optional[float] = Field(
        default=None, ge=0, description="Recommended settlement / payout amount in USD"
    )
