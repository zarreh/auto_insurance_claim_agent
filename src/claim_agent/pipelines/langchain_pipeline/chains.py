"""LangGraph state graph for the claim-processing workflow.

Graph topology::

    START
      │
      ▼
    parse_claim
      │
      ▼
    validate_claim ──(invalid)──► finalize_invalid ──► END
      │ (valid)
      ▼
    check_policy
      │
      ▼
    price_check ──(inflated)──► finalize_inflated ──► END
      │ (ok)
      ▼
    generate_recommendation
      │
      ▼
    finalize_decision ──► END
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from loguru import logger
from omegaconf import DictConfig

from claim_agent.pipelines.langchain_pipeline.tools import (
    generate_policy_queries,
    generate_recommendation,
    parse_claim,
    retrieve_policy_text_tool,
    validate_claim_tool,
    web_search_repair_cost,
)
from claim_agent.schemas.claim import ClaimDecision, ClaimInfo
from claim_agent.schemas.policy import PolicyQueries, PolicyRecommendation


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class ClaimState(TypedDict, total=False):
    """Mutable state carried through the LangGraph execution."""

    # Input
    claim_data: dict[str, Any]

    # After parse
    claim: ClaimInfo

    # After validate
    is_valid: bool
    validation_reason: str

    # After check_policy
    policy_queries: PolicyQueries
    policy_text: list[str]

    # After price_check
    market_cost_estimate: float | None
    is_inflated: bool
    market_cost_info: str

    # After generate_recommendation
    recommendation: PolicyRecommendation

    # Final output
    decision: ClaimDecision

    # Trace / observability
    trace: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def _log_node(name: str) -> dict[str, Any]:
    """Return a trace entry dict and log entry into a node."""
    logger.info("── Entering node: {name} ──", name=name)
    return {"node": name, "entered_at": time.time()}


def node_parse_claim(state: ClaimState) -> dict:
    t = _log_node("parse_claim")
    claim = parse_claim(state["claim_data"])
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    return {"claim": claim, "trace": trace}


def node_validate_claim(state: ClaimState, cfg: DictConfig) -> dict:
    t = _log_node("validate_claim")
    is_valid, reason = validate_claim_tool(state["claim"], cfg.data.coverage_csv)
    t["is_valid"] = is_valid
    t["reason"] = reason
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    return {"is_valid": is_valid, "validation_reason": reason, "trace": trace}


def node_check_policy(state: ClaimState, cfg: DictConfig, llm: ChatOpenAI) -> dict:
    t = _log_node("check_policy")

    # Generate queries
    pq = generate_policy_queries(state["claim"], llm)
    t["queries"] = pq.queries

    # Retrieve policy text
    chunks = retrieve_policy_text_tool(pq.queries, cfg)
    t["chunks_retrieved"] = len(chunks)
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    return {"policy_queries": pq, "policy_text": chunks, "trace": trace}


def node_price_check(state: ClaimState, cfg: DictConfig) -> dict:
    t = _log_node("price_check")
    threshold = cfg.pipeline.price_check.inflation_threshold
    market_est, is_inflated, info = web_search_repair_cost(
        state["claim"], inflation_threshold=threshold,
    )
    t["market_estimate"] = market_est
    t["is_inflated"] = is_inflated
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    return {
        "market_cost_estimate": market_est,
        "is_inflated": is_inflated,
        "market_cost_info": info,
        "trace": trace,
    }


def node_generate_recommendation(state: ClaimState, llm: ChatOpenAI) -> dict:
    t = _log_node("generate_recommendation")
    policy_text_combined = "\n\n---\n\n".join(state.get("policy_text", []))
    rec = generate_recommendation(
        claim=state["claim"],
        policy_text=policy_text_combined or "No policy text available.",
        market_cost_info=state.get("market_cost_info", "No market cost data."),
        llm=llm,
    )
    t["recommendation"] = rec.recommendation_summary
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    return {"recommendation": rec, "trace": trace}


def node_finalize_decision(state: ClaimState) -> dict:
    t = _log_node("finalize_decision")
    claim: ClaimInfo = state["claim"]
    rec: PolicyRecommendation = state["recommendation"]
    decision = ClaimDecision(
        claim_number=claim.claim_number,
        covered=True,
        deductible=rec.deductible or 0.0,
        recommended_payout=rec.settlement_amount or 0.0,
        notes=rec.recommendation_summary,
    )
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    logger.info("✓ Claim {num} APPROVED — payout ${pay:,.2f}", num=claim.claim_number, pay=decision.recommended_payout)
    return {"decision": decision, "trace": trace}


def node_finalize_invalid(state: ClaimState) -> dict:
    t = _log_node("finalize_invalid")
    claim: ClaimInfo = state["claim"]
    decision = ClaimDecision(
        claim_number=claim.claim_number,
        covered=False,
        deductible=0.0,
        recommended_payout=0.0,
        notes=f"Claim rejected — {state['validation_reason']}",
    )
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    logger.info("✗ Claim {num} REJECTED — {reason}", num=claim.claim_number, reason=state["validation_reason"])
    return {"decision": decision, "trace": trace}


def node_finalize_inflated(state: ClaimState) -> dict:
    t = _log_node("finalize_inflated")
    claim: ClaimInfo = state["claim"]
    decision = ClaimDecision(
        claim_number=claim.claim_number,
        covered=False,
        deductible=0.0,
        recommended_payout=0.0,
        notes=(
            f"Claim rejected — estimated repair cost appears inflated. "
            f"{state.get('market_cost_info', '')}"
        ),
    )
    t["elapsed"] = time.time() - t["entered_at"]
    trace = state.get("trace", [])
    trace.append(t)
    logger.info("✗ Claim {num} REJECTED — inflated cost", num=claim.claim_number)
    return {"decision": decision, "trace": trace}


# ---------------------------------------------------------------------------
# Conditional edge routers
# ---------------------------------------------------------------------------

def route_after_validate(state: ClaimState) -> str:
    """Route to ``check_policy`` if valid, else ``finalize_invalid``."""
    return "check_policy" if state.get("is_valid") else "finalize_invalid"


def route_after_price_check(state: ClaimState) -> str:
    """Route to ``generate_recommendation`` if ok, else ``finalize_inflated``."""
    return "finalize_inflated" if state.get("is_inflated") else "generate_recommendation"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_claim_graph(cfg: DictConfig, llm: ChatOpenAI) -> StateGraph:
    """Construct and compile the LangGraph ``StateGraph``.

    Parameters
    ----------
    cfg:
        Full Hydra configuration (used for data paths, thresholds, etc.).
    llm:
        Initialised ``ChatOpenAI`` instance.

    Returns
    -------
    StateGraph
        A compiled graph ready to be invoked with
        ``graph.invoke({"claim_data": ...})``.
    """
    graph = StateGraph(ClaimState)

    # ── Register nodes (bind cfg / llm via closures) ────────────────────
    graph.add_node("parse_claim", node_parse_claim)
    graph.add_node("validate_claim", lambda s: node_validate_claim(s, cfg))
    graph.add_node("check_policy", lambda s: node_check_policy(s, cfg, llm))
    graph.add_node("price_check", lambda s: node_price_check(s, cfg))
    graph.add_node("generate_recommendation", lambda s: node_generate_recommendation(s, llm))
    graph.add_node("finalize_decision", node_finalize_decision)
    graph.add_node("finalize_invalid", node_finalize_invalid)
    graph.add_node("finalize_inflated", node_finalize_inflated)

    # ── Edges ───────────────────────────────────────────────────────────
    graph.set_entry_point("parse_claim")
    graph.add_edge("parse_claim", "validate_claim")

    graph.add_conditional_edges(
        "validate_claim",
        route_after_validate,
        {"check_policy": "check_policy", "finalize_invalid": "finalize_invalid"},
    )

    graph.add_edge("check_policy", "price_check")

    graph.add_conditional_edges(
        "price_check",
        route_after_price_check,
        {"generate_recommendation": "generate_recommendation", "finalize_inflated": "finalize_inflated"},
    )

    graph.add_edge("generate_recommendation", "finalize_decision")
    graph.add_edge("finalize_decision", END)
    graph.add_edge("finalize_invalid", END)
    graph.add_edge("finalize_inflated", END)

    logger.info("LangGraph claim-processing graph compiled")
    return graph.compile()
