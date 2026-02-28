"""Integration tests for the Smolagents pipeline.

All LLM and agent calls are mocked so tests are deterministic.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from omegaconf import DictConfig

from claim_agent.schemas.claim import ClaimDecision, ClaimInfo

# ═══════════════════════════════════════════════════════════════════════
# _parse_decision / _extract_json / _fuzzy_extract  (unit tests)
# ═══════════════════════════════════════════════════════════════════════


class TestSmolAgentsParseDecision:
    """Test the parsing helpers on :class:`SmolAgentsPipeline`."""

    @pytest.fixture(autouse=True)
    def _setup(self, test_cfg: DictConfig, valid_claim: ClaimInfo) -> None:
        self.claim = valid_claim
        # Import conditionally to avoid module-level failures if smolagents
        # is not installed with all extras.
        from claim_agent.pipelines.smolagents_pipeline.pipeline import SmolAgentsPipeline

        self.Pipeline = SmolAgentsPipeline

    def test_extract_json_from_markdown(self) -> None:
        text = 'Here is the result:\n```json\n{"claim_number":"CLM-1","covered":true}\n```'
        result = self.Pipeline._extract_json(text)
        assert '"claim_number"' in result
        assert '"covered"' in result

    def test_extract_json_bare_object(self) -> None:
        text = 'The answer is {"claim_number":"CLM-1","covered":false}'
        result = self.Pipeline._extract_json(text)
        data = json.loads(result)
        assert data["covered"] is False

    def test_fuzzy_extract_covered_true(self) -> None:
        text = '"covered": true, "deductible": 500.0, "recommended_payout": 3000.0, "notes": "ok"'
        data = self.Pipeline._fuzzy_extract(text, self.claim)
        assert data["covered"] is True
        assert data["deductible"] == 500.0
        assert data["recommended_payout"] == 3000.0

    def test_fuzzy_extract_covered_false(self) -> None:
        text = '"covered": false'
        data = self.Pipeline._fuzzy_extract(text, self.claim)
        assert data["covered"] is False
        assert data["claim_number"] == self.claim.claim_number

    def test_parse_decision_valid_json(self, test_cfg: DictConfig) -> None:
        decision_json = json.dumps(
            {
                "claim_number": "CLM-TEST-001",
                "covered": True,
                "deductible": 500.0,
                "recommended_payout": 3000.0,
                "notes": "Approved.",
            }
        )

        with patch.object(self.Pipeline, "__init__", lambda s, c: None):
            pipeline = self.Pipeline.__new__(self.Pipeline)
            decision = pipeline._parse_decision(decision_json, self.claim)

        assert isinstance(decision, ClaimDecision)
        assert decision.covered is True
        assert decision.recommended_payout == 3000.0

    def test_parse_decision_unparseable_returns_fallback(self, test_cfg: DictConfig) -> None:
        with patch.object(self.Pipeline, "__init__", lambda s, c: None):
            pipeline = self.Pipeline.__new__(self.Pipeline)
            decision = pipeline._parse_decision("completely invalid output", self.claim)

        assert isinstance(decision, ClaimDecision)
        assert decision.covered is False
        # Fuzzy parsing may succeed with defaults, or full fallback fires
        assert decision.notes is not None


# ═══════════════════════════════════════════════════════════════════════
# End-to-end pipeline with mocked agent
# ═══════════════════════════════════════════════════════════════════════


class TestSmolAgentsPipelineE2E:
    """End-to-end test with a mocked ToolCallingAgent."""

    @patch("claim_agent.pipelines.smolagents_pipeline.pipeline.ToolCallingAgent")
    @patch("claim_agent.pipelines.smolagents_pipeline.pipeline.OpenAIServerModel")
    def test_process_claim_mocked_agent(
        self,
        mock_model_cls: MagicMock,
        mock_agent_cls: MagicMock,
        valid_claim: ClaimInfo,
        test_cfg: DictConfig,
    ) -> None:
        """Pipeline should return a valid ClaimDecision from mocked agent output."""
        # Configure the mock agent to return valid JSON
        mock_agent = MagicMock()
        mock_agent.run.return_value = json.dumps(
            {
                "claim_number": valid_claim.claim_number,
                "covered": True,
                "deductible": 500.0,
                "recommended_payout": 3000.0,
                "notes": "Mock: Approved under collision.",
            }
        )
        mock_agent_cls.return_value = mock_agent

        # Adjust config for smolagents
        test_cfg.pipeline.type = "smolagents"

        from claim_agent.pipelines.smolagents_pipeline.pipeline import SmolAgentsPipeline

        pipeline = SmolAgentsPipeline(test_cfg)
        decision = pipeline.process_claim(valid_claim)

        assert isinstance(decision, ClaimDecision)
        assert decision.covered is True
        assert decision.claim_number == valid_claim.claim_number
        mock_agent.run.assert_called_once()

    @patch("claim_agent.pipelines.smolagents_pipeline.pipeline.ToolCallingAgent")
    @patch("claim_agent.pipelines.smolagents_pipeline.pipeline.OpenAIServerModel")
    def test_process_claim_fallback_on_bad_output(
        self,
        mock_model_cls: MagicMock,
        mock_agent_cls: MagicMock,
        valid_claim: ClaimInfo,
        test_cfg: DictConfig,
    ) -> None:
        """Pipeline should return a safe fallback when agent output is garbage."""
        mock_agent = MagicMock()
        mock_agent.run.return_value = "I don't know what to do"
        mock_agent_cls.return_value = mock_agent

        test_cfg.pipeline.type = "smolagents"

        from claim_agent.pipelines.smolagents_pipeline.pipeline import SmolAgentsPipeline

        pipeline = SmolAgentsPipeline(test_cfg)
        decision = pipeline.process_claim(valid_claim)

        assert isinstance(decision, ClaimDecision)
        assert decision.covered is False  # Safe fallback
