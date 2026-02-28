"""Smolagents pipeline implementation.

Uses smolagents' ``ToolCallingAgent`` with custom tools and prompt templates
to autonomously process insurance claims through the same workflow as the
LangGraph pipeline, but with LLM-driven orchestration instead of explicit
graph edges.
"""

from __future__ import annotations

import json
import time
from typing import Any

from loguru import logger
from omegaconf import DictConfig
from smolagents import DuckDuckGoSearchTool, OpenAIServerModel, ToolCallingAgent

from claim_agent.pipelines.base import BasePipeline
from claim_agent.pipelines.smolagents_pipeline.prompts import get_prompt_templates
from claim_agent.pipelines.smolagents_pipeline.tools import (
    estimate_repair_cost,
    generate_policy_queries,
    generate_recommendation,
    parse_and_validate_claim,
    retrieve_policy_text,
)
from claim_agent.schemas.claim import ClaimDecision, ClaimInfo


class SmolAgentsPipeline(BasePipeline):
    """Claim-processing pipeline backed by smolagents' ``ToolCallingAgent``.

    The agent receives the full claim context as a task prompt and is expected
    to call the registered tools in the correct order (parse → validate →
    query → retrieve → price check → recommend → decide).  The system prompt
    enforces the strict sequential workflow.
    """

    def __init__(self, cfg: DictConfig) -> None:
        super().__init__(cfg)

        # ── Model ────────────────────────────────────────────────────────
        model_kwargs: dict[str, Any] = {
            "model_id": cfg.llm.model,
            "api_key": cfg.llm.api_key,
        }
        if cfg.llm.get("base_url"):
            model_kwargs["api_base"] = cfg.llm.base_url
        self.model = OpenAIServerModel(**model_kwargs)
        logger.info(
            "Smolagents model initialised: {model}",
            model=cfg.llm.model,
        )

        # ── Tools ────────────────────────────────────────────────────────
        self.tools = [
            parse_and_validate_claim,
            generate_policy_queries,
            retrieve_policy_text,
            estimate_repair_cost,
            generate_recommendation,
            DuckDuckGoSearchTool(),
        ]

        # ── Prompt templates ─────────────────────────────────────────────
        self.prompt_templates = get_prompt_templates()

        # ── Agent config ─────────────────────────────────────────────────
        self.max_steps = cfg.pipeline.agent.max_steps
        self.verbosity = cfg.pipeline.agent.verbosity_level

        logger.info("SmolAgentsPipeline ready")

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def process_claim(self, claim: ClaimInfo) -> ClaimDecision:
        """Run the autonomous agent to process a single claim.

        Parameters
        ----------
        claim:
            A validated ``ClaimInfo`` instance.

        Returns
        -------
        ClaimDecision
            The final coverage decision.
        """
        logger.info(
            "Processing claim {num} via Smolagents pipeline",
            num=claim.claim_number,
        )
        start = time.time()

        # Build a fresh agent per invocation (lightweight; avoids stale state)
        agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model,
            prompt_templates=self.prompt_templates,
            max_steps=self.max_steps,
            verbosity_level=self.verbosity,
            planning_interval=2,
        )

        # Build the task prompt with all config values the tools need
        task = self._build_task_prompt(claim)

        # Run the agent
        raw_result = agent.run(task)
        elapsed = time.time() - start

        logger.info(
            "Smolagents agent finished in {t:.2f}s for claim {num}",
            t=elapsed,
            num=claim.claim_number,
        )

        # Parse agent output into ClaimDecision (with retry)
        decision = self._parse_decision(raw_result, claim)

        logger.info(
            "Claim {num} — covered={cov}, payout=${pay:,.2f}",
            num=claim.claim_number,
            cov=decision.covered,
            pay=decision.recommended_payout,
        )
        return decision

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    def _build_task_prompt(self, claim: ClaimInfo) -> str:
        """Construct the task string with claim data and all config values."""
        claim_json = claim.model_dump_json()
        cfg = self.cfg

        return (
            f"Process the following insurance claim.\n\n"
            f"## Claim JSON\n```json\n{claim_json}\n```\n\n"
            f"## Configuration values for tool calls\n"
            f"- csv_path: {cfg.data.coverage_csv}\n"
            f"- model_name: {cfg.llm.model}\n"
            f"- temperature: {cfg.llm.temperature}\n"
            f"- api_key: {cfg.llm.api_key}\n"
            f"- chroma_persist_dir: {cfg.data.chroma_persist_dir}\n"
            f"- collection_name: {cfg.vectordb.collection_name}\n"
            f"- embedding_model: {cfg.vectordb.embedding_model}\n"
            f"- n_results: {cfg.vectordb.n_results}\n"
            f"- inflation_threshold: {cfg.pipeline.price_check.inflation_threshold}\n\n"
            f"Follow the strict workflow from your system prompt. "
            f"Return the final decision as a JSON object."
        )

    def _parse_decision(
        self,
        raw_result: Any,
        claim: ClaimInfo,
        *,
        _retry: bool = True,
    ) -> ClaimDecision:
        """Parse the agent's raw output into a ``ClaimDecision``.

        If the first parse fails and ``_retry`` is True, attempt to extract
        JSON from the raw string and retry once.
        """
        # If agent returned a string, try to parse as JSON
        text = str(raw_result)

        # Try to extract JSON from the text (agent may wrap it in markdown)
        json_str = self._extract_json(text)

        try:
            data = json.loads(json_str)
            return ClaimDecision(**data)
        except Exception as first_err:
            logger.warning(
                "First parse attempt failed for claim {num}: {err}",
                num=claim.claim_number,
                err=first_err,
            )

            if _retry:
                # Retry: be more lenient — try to find any JSON object in text
                try:
                    # Look for JSON-like content
                    data = self._fuzzy_extract(text, claim)
                    return ClaimDecision(**data)
                except Exception as retry_err:
                    logger.error(
                        "Retry parse also failed for claim {num}: {err}",
                        num=claim.claim_number,
                        err=retry_err,
                    )

            # Fallback: return a decision noting the parse failure
            logger.error(
                "Could not parse agent output for claim {num}. "
                "Returning fallback decision. Raw output: {raw}",
                num=claim.claim_number,
                raw=text[:500],
            )
            return ClaimDecision(
                claim_number=claim.claim_number,
                covered=False,
                deductible=0.0,
                recommended_payout=0.0,
                notes=f"Agent output could not be parsed into a valid decision. Raw: {text[:300]}",
            )

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract the first JSON object from *text* (handles markdown fences)."""
        import re

        # Try markdown code block first
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)

        # Try bare JSON object
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            return match.group(0)

        return text

    @staticmethod
    def _fuzzy_extract(text: str, claim: ClaimInfo) -> dict:
        """Best-effort extraction of decision fields from free-form text."""
        import re

        data: dict[str, Any] = {"claim_number": claim.claim_number}

        # covered
        if re.search(r'"covered"\s*:\s*true', text, re.IGNORECASE):
            data["covered"] = True
        elif re.search(r'"covered"\s*:\s*false', text, re.IGNORECASE):
            data["covered"] = False
        else:
            data["covered"] = False

        # deductible
        ded_match = re.search(r'"deductible"\s*:\s*([\d.]+)', text)
        data["deductible"] = float(ded_match.group(1)) if ded_match else 0.0

        # recommended_payout
        pay_match = re.search(r'"recommended_payout"\s*:\s*([\d.]+)', text)
        data["recommended_payout"] = float(pay_match.group(1)) if pay_match else 0.0

        # notes
        notes_match = re.search(r'"notes"\s*:\s*"([^"]*)"', text)
        data["notes"] = (
            notes_match.group(1)
            if notes_match
            else "Extracted from agent output via fuzzy parsing."
        )

        return data
