"""Integration tests for the LangChain/LangGraph pipeline.

LLM calls and web searches are fully mocked so tests are deterministic and
require no API keys or network access.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from omegaconf import DictConfig

from claim_agent.pipelines.langchain_pipeline.chains import (
    ClaimState,
    build_claim_graph,
    node_finalize_decision,
    node_finalize_inflated,
    node_finalize_invalid,
    node_parse_claim,
    route_after_price_check,
    route_after_validate,
)
from claim_agent.schemas.claim import ClaimDecision, ClaimInfo
from claim_agent.schemas.policy import PolicyQueries, PolicyRecommendation

# ═══════════════════════════════════════════════════════════════════════
# Unit-level node tests
# ═══════════════════════════════════════════════════════════════════════


class TestNodeFunctions:
    """Test individual graph node functions."""

    def test_node_parse_claim(self, valid_claim: ClaimInfo) -> None:
        state: ClaimState = {"claim_data": valid_claim.model_dump(mode="json")}
        result = node_parse_claim(state)
        assert isinstance(result["claim"], ClaimInfo)
        assert result["claim"].claim_number == valid_claim.claim_number
        assert len(result["trace"]) == 1

    def test_node_finalize_invalid(self, valid_claim: ClaimInfo) -> None:
        state: ClaimState = {
            "claim": valid_claim,
            "validation_reason": "Policy PN-99 not found",
            "trace": [],
        }
        result = node_finalize_invalid(state)
        decision: ClaimDecision = result["decision"]
        assert decision.covered is False
        assert decision.recommended_payout == 0.0
        assert "rejected" in (decision.notes or "").lower()

    def test_node_finalize_inflated(self, valid_claim: ClaimInfo) -> None:
        state: ClaimState = {
            "claim": valid_claim,
            "market_cost_info": "Market estimate $1,200 vs claimed $15,000",
            "trace": [],
        }
        result = node_finalize_inflated(state)
        decision: ClaimDecision = result["decision"]
        assert decision.covered is False
        assert "inflated" in (decision.notes or "").lower()

    def test_node_finalize_decision(self, valid_claim: ClaimInfo) -> None:
        rec = PolicyRecommendation(
            policy_section="Section 4 — Collision",
            recommendation_summary="Claim covered under collision.",
            deductible=500.0,
            settlement_amount=3000.0,
        )
        state: ClaimState = {
            "claim": valid_claim,
            "recommendation": rec,
            "trace": [],
        }
        result = node_finalize_decision(state)
        decision: ClaimDecision = result["decision"]
        assert decision.covered is True
        assert decision.deductible == 500.0
        assert decision.recommended_payout == 3000.0


# ═══════════════════════════════════════════════════════════════════════
# Conditional edge routers
# ═══════════════════════════════════════════════════════════════════════


class TestRouters:
    """Test routing logic for conditional edges."""

    def test_route_valid(self) -> None:
        assert route_after_validate({"is_valid": True}) == "check_policy"

    def test_route_invalid(self) -> None:
        assert route_after_validate({"is_valid": False}) == "finalize_invalid"

    def test_route_inflated(self) -> None:
        assert route_after_price_check({"is_inflated": True}) == "finalize_inflated"

    def test_route_not_inflated(self) -> None:
        assert route_after_price_check({"is_inflated": False}) == "generate_recommendation"


# ═══════════════════════════════════════════════════════════════════════
# End-to-end graph execution (mocked LLM / tools)
# ═══════════════════════════════════════════════════════════════════════


class TestLangChainPipelineE2E:
    """End-to-end graph test with mocked external calls."""

    @patch("claim_agent.pipelines.langchain_pipeline.chains.web_search_repair_cost")
    @patch("claim_agent.pipelines.langchain_pipeline.chains.retrieve_policy_text_tool")
    @patch("claim_agent.pipelines.langchain_pipeline.chains.generate_policy_queries")
    @patch("claim_agent.pipelines.langchain_pipeline.chains.generate_recommendation")
    def test_valid_claim_approved(
        self,
        mock_recommendation: MagicMock,
        mock_queries: MagicMock,
        mock_retrieve: MagicMock,
        mock_price: MagicMock,
        valid_claim: ClaimInfo,
        test_cfg: DictConfig,
    ) -> None:
        """A valid claim should flow through to approval when nothing is inflated."""
        # Mock LLM-dependent tools
        mock_queries.return_value = PolicyQueries(queries=["collision deductible"])
        mock_retrieve.return_value = ["Section 4: Collision coverage..."]
        mock_price.return_value = (3000.0, False, "Market estimate: $3,000")
        mock_recommendation.return_value = PolicyRecommendation(
            policy_section="Section 4",
            recommendation_summary="Approved under collision coverage.",
            deductible=500.0,
            settlement_amount=3000.0,
        )

        mock_llm = MagicMock()
        graph = build_claim_graph(test_cfg, mock_llm)

        result = graph.invoke(
            {"claim_data": valid_claim.model_dump(mode="json")},
            config={"recursion_limit": 25},
        )

        decision: ClaimDecision = result["decision"]
        assert decision.covered is True
        assert decision.deductible == 500.0
        assert decision.recommended_payout == 3000.0

    @patch("claim_agent.pipelines.langchain_pipeline.chains.validate_claim_tool")
    def test_invalid_policy_rejected(
        self,
        mock_validate: MagicMock,
        invalid_policy_claim: ClaimInfo,
        test_cfg: DictConfig,
    ) -> None:
        """An invalid policy should be rejected at the validate step."""
        mock_validate.return_value = (False, "Policy PN-99 not found in records")

        mock_llm = MagicMock()
        graph = build_claim_graph(test_cfg, mock_llm)

        result = graph.invoke(
            {"claim_data": invalid_policy_claim.model_dump(mode="json")},
            config={"recursion_limit": 25},
        )

        decision: ClaimDecision = result["decision"]
        assert decision.covered is False
        assert "PN-99" in (decision.notes or "")

    @patch("claim_agent.pipelines.langchain_pipeline.chains.web_search_repair_cost")
    @patch("claim_agent.pipelines.langchain_pipeline.chains.retrieve_policy_text_tool")
    @patch("claim_agent.pipelines.langchain_pipeline.chains.generate_policy_queries")
    def test_inflated_claim_rejected(
        self,
        mock_queries: MagicMock,
        mock_retrieve: MagicMock,
        mock_price: MagicMock,
        valid_claim: ClaimInfo,
        test_cfg: DictConfig,
    ) -> None:
        """A claim flagged as inflated should be rejected at price_check."""
        mock_queries.return_value = PolicyQueries(queries=["collision"])
        mock_retrieve.return_value = ["Policy text"]
        mock_price.return_value = (1000.0, True, "Market $1,000 vs claimed $3,500")

        mock_llm = MagicMock()
        graph = build_claim_graph(test_cfg, mock_llm)

        result = graph.invoke(
            {"claim_data": valid_claim.model_dump(mode="json")},
            config={"recursion_limit": 25},
        )

        decision: ClaimDecision = result["decision"]
        assert decision.covered is False
        assert "inflated" in (decision.notes or "").lower()
