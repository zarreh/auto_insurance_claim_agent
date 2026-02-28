"""LangChain / LangGraph pipeline implementation."""

from __future__ import annotations

import time
from typing import Any

from langchain_openai import ChatOpenAI
from loguru import logger
from omegaconf import DictConfig

from claim_agent.pipelines.base import BasePipeline
from claim_agent.pipelines.langchain_pipeline.chains import build_claim_graph
from claim_agent.schemas.claim import ClaimDecision, ClaimInfo


class LangChainPipeline(BasePipeline):
    """Claim-processing pipeline backed by LangGraph's stateful graph.

    The graph encodes the exact workflow:
    PARSE → VALIDATE → [INVALID → DONE] /
    [VALID → CHECK POLICY → PRICE CHECK → [INFLATED → DONE] /
    [OK → RECOMMENDATION → FINAL DECISION → DONE]]
    """

    def __init__(self, cfg: DictConfig) -> None:
        super().__init__(cfg)

        # ── Initialise LLM ──────────────────────────────────────────────
        self.llm = ChatOpenAI(
            model=cfg.llm.model,
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
            api_key=cfg.llm.api_key,
        )
        logger.info(
            "LLM initialised: model={model}, temp={temp}",
            model=cfg.llm.model,
            temp=cfg.llm.temperature,
        )

        # ── Compile the graph ───────────────────────────────────────────
        self.graph = build_claim_graph(cfg, self.llm)
        logger.info("LangChainPipeline ready")

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def process_claim(self, claim: ClaimInfo) -> ClaimDecision:
        """Run the full claim-processing graph.

        Parameters
        ----------
        claim:
            A validated ``ClaimInfo`` instance.

        Returns
        -------
        ClaimDecision
            The final coverage decision produced by the graph.
        """
        logger.info(
            "Processing claim {num} via LangGraph pipeline",
            num=claim.claim_number,
        )
        start = time.time()

        # Invoke the compiled graph
        result: dict[str, Any] = self.graph.invoke(
            {"claim_data": claim.model_dump(mode="json")},
            config={"recursion_limit": self.cfg.pipeline.graph.recursion_limit},
        )

        elapsed = time.time() - start
        decision: ClaimDecision = result["decision"]

        logger.info(
            "Claim {num} processed in {t:.2f}s — covered={cov}",
            num=claim.claim_number,
            t=elapsed,
            cov=decision.covered,
        )

        # Attach trace to notes for observability (append, don't overwrite)
        trace = result.get("trace", [])
        if trace:
            trace_summary = _format_trace(trace)
            if decision.notes:
                decision.notes += f"\n\n--- Processing Trace ---\n{trace_summary}"
            else:
                decision.notes = f"--- Processing Trace ---\n{trace_summary}"

        return decision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_trace(trace: list[dict[str, Any]]) -> str:
    """Format the execution trace into a readable string."""
    lines: list[str] = []
    for entry in trace:
        node = entry.get("node", "?")
        elapsed = entry.get("elapsed", 0)
        extra_parts: list[str] = []
        for k, v in entry.items():
            if k in ("node", "entered_at", "elapsed"):
                continue
            extra_parts.append(f"{k}={v}")
        extra = " | ".join(extra_parts) if extra_parts else ""
        lines.append(f"  [{node}] {elapsed:.2f}s{' — ' + extra if extra else ''}")
    return "\n".join(lines)
