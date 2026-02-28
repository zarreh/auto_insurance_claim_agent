"""LangChain tool definitions for the LangGraph claim-processing pipeline.

Each tool wraps a piece of core business logic or an LLM call so that it can be
invoked as a node function inside the LangGraph ``StateGraph``.  The tools are
**not** decorated with ``@tool`` because they are called directly by graph
nodes — but they follow the same thin-wrapper pattern.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from duckduckgo_search import DDGS
from langchain_openai import ChatOpenAI
from loguru import logger

from claim_agent.core.retrieval import retrieve_policy_text
from claim_agent.core.validation import validate_claim
from claim_agent.pipelines.langchain_pipeline.prompts import (
    QUERY_GENERATION_PROMPT,
    RECOMMENDATION_PROMPT,
)
from claim_agent.schemas.claim import ClaimDecision, ClaimInfo
from claim_agent.schemas.policy import PolicyQueries, PolicyRecommendation

if TYPE_CHECKING:
    from omegaconf import DictConfig


# ---------------------------------------------------------------------------
# Tool: parse claim
# ---------------------------------------------------------------------------

def parse_claim(claim_data: dict) -> ClaimInfo:
    """Validate raw dict/JSON against the ``ClaimInfo`` schema.

    Raises ``pydantic.ValidationError`` on bad input.
    """
    claim = ClaimInfo(**claim_data)
    logger.info("Parsed claim {num}", num=claim.claim_number)
    return claim


# ---------------------------------------------------------------------------
# Tool: validate claim against CSV
# ---------------------------------------------------------------------------

def validate_claim_tool(claim: ClaimInfo, csv_path: str) -> tuple[bool, str]:
    """Delegate to ``core.validation.validate_claim``."""
    is_valid, reason = validate_claim(claim, csv_path)
    return is_valid, reason


# ---------------------------------------------------------------------------
# Tool: generate policy search queries via LLM
# ---------------------------------------------------------------------------

def generate_policy_queries(claim: ClaimInfo, llm: ChatOpenAI) -> PolicyQueries:
    """Ask the LLM to produce 3–5 targeted policy search queries."""
    chain = QUERY_GENERATION_PROMPT | llm.with_structured_output(PolicyQueries)
    result: PolicyQueries = chain.invoke(
        {
            "claim_number": claim.claim_number,
            "policy_number": claim.policy_number,
            "date_of_loss": str(claim.date_of_loss),
            "loss_description": claim.loss_description,
            "estimated_repair_cost": claim.estimated_repair_cost,
            "vehicle_details": claim.vehicle_details or "N/A",
        }
    )
    logger.info(
        "Generated {n} policy queries for claim {num}",
        n=len(result.queries),
        num=claim.claim_number,
    )
    return result


# ---------------------------------------------------------------------------
# Tool: retrieve policy text from ChromaDB
# ---------------------------------------------------------------------------

def retrieve_policy_text_tool(
    queries: list[str],
    cfg: DictConfig,
) -> list[str]:
    """Embed *queries* and retrieve relevant policy chunks from ChromaDB."""
    chunks = retrieve_policy_text(
        queries=queries,
        chroma_persist_dir=cfg.data.chroma_persist_dir,
        collection_name=cfg.vectordb.collection_name,
        embedding_model=cfg.vectordb.embedding_model,
        n_results=cfg.vectordb.n_results,
    )
    return chunks


# ---------------------------------------------------------------------------
# Tool: web-search repair cost estimate
# ---------------------------------------------------------------------------

def web_search_repair_cost(
    claim: ClaimInfo,
    inflation_threshold: float = 0.40,
) -> tuple[float | None, bool, str]:
    """Search DuckDuckGo for typical market repair costs.

    Returns
    -------
    tuple[float | None, bool, str]
        ``(market_estimate, is_inflated, summary_text)``
    """
    query = (
        f"average auto repair cost {claim.loss_description} "
        f"{claim.vehicle_details or ''} USD"
    )
    logger.info("Web-searching repair costs: {q}", q=query)

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: {e}", e=exc)
        return None, False, f"Web search unavailable ({exc}). Price check skipped."

    if not results:
        return None, False, "No web search results found. Price check skipped."

    # Combine snippet text for the LLM / heuristic
    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('body', '')}" for r in results
    )

    # Try to extract dollar amounts from snippets
    amounts = _extract_dollar_amounts(snippets)
    if not amounts:
        summary = (
            f"Web search returned results but no clear dollar estimates.\n"
            f"Snippets:\n{snippets}"
        )
        return None, False, summary

    market_estimate = sum(amounts) / len(amounts)
    threshold_amount = market_estimate * (1 + inflation_threshold)
    is_inflated = claim.estimated_repair_cost > threshold_amount

    summary = (
        f"Market estimate: ${market_estimate:,.2f} "
        f"(based on {len(amounts)} data points). "
        f"Claimed: ${claim.estimated_repair_cost:,.2f}. "
        f"Threshold ({int(inflation_threshold * 100)}% above market): "
        f"${threshold_amount:,.2f}. "
        f"{'INFLATED — claimed cost exceeds threshold.' if is_inflated else 'Within acceptable range.'}"
    )
    logger.info(summary)
    return market_estimate, is_inflated, summary


# ---------------------------------------------------------------------------
# Tool: generate recommendation via LLM
# ---------------------------------------------------------------------------

def generate_recommendation(
    claim: ClaimInfo,
    policy_text: str,
    market_cost_info: str,
    llm: ChatOpenAI,
) -> PolicyRecommendation:
    """Ask the LLM for a coverage recommendation given claim + policy + costs."""
    chain = RECOMMENDATION_PROMPT | llm.with_structured_output(PolicyRecommendation)
    result: PolicyRecommendation = chain.invoke(
        {
            "claim_number": claim.claim_number,
            "policy_number": claim.policy_number,
            "date_of_loss": str(claim.date_of_loss),
            "loss_description": claim.loss_description,
            "estimated_repair_cost": claim.estimated_repair_cost,
            "vehicle_details": claim.vehicle_details or "N/A",
            "policy_text": policy_text,
            "market_cost_info": market_cost_info,
        }
    )
    logger.info(
        "Recommendation for {num}: covered section='{sec}'",
        num=claim.claim_number,
        sec=result.policy_section,
    )
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_dollar_amounts(text: str) -> list[float]:
    """Extract dollar amounts from free text (e.g. ``$1,234.56``)."""
    pattern = r"\$\s?([\d,]+(?:\.\d{1,2})?)"
    matches = re.findall(pattern, text)
    amounts: list[float] = []
    for m in matches:
        try:
            amounts.append(float(m.replace(",", "")))
        except ValueError:
            continue
    # Filter out unreasonable amounts (< $50 or > $200k likely noise)
    return [a for a in amounts if 50 <= a <= 200_000]
