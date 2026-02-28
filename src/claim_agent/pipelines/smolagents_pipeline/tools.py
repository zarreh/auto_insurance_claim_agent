"""Smolagents tool definitions for the autonomous claim-processing agent.

Each tool wraps a piece of core business logic (validation, retrieval, LLM call,
web search) and is decorated with ``@tool`` so smolagents' ``ToolCallingAgent``
can discover and invoke them automatically.

Because smolagents ``@tool`` functions must be **self-contained** (the agent
serialises their source), we pass configuration values as explicit string/float
parameters rather than injecting ``DictConfig`` objects.
"""

from __future__ import annotations

from smolagents import tool

# ---------------------------------------------------------------------------
# Tool: parse and validate claim
# ---------------------------------------------------------------------------

@tool
def parse_and_validate_claim(
    claim_json: str,
    csv_path: str,
) -> str:
    """Parse an insurance claim from JSON and validate it against the policy CSV.

    Args:
        claim_json: A JSON string representing the claim (must match ClaimInfo schema).
        csv_path: Filesystem path to the coverage_data.csv file.

    Returns:
        A JSON string with keys 'is_valid' (bool), 'reason' (str), and 'claim' (dict).
    """
    import json as _json

    from claim_agent.core.validation import validate_claim
    from claim_agent.schemas.claim import ClaimInfo

    data = _json.loads(claim_json)
    claim = ClaimInfo(**data)
    is_valid, reason = validate_claim(claim, csv_path)
    return _json.dumps(
        {
            "is_valid": is_valid,
            "reason": reason,
            "claim": claim.model_dump(mode="json"),
        }
    )


# ---------------------------------------------------------------------------
# Tool: generate policy search queries via LLM
# ---------------------------------------------------------------------------

@tool
def generate_policy_queries(
    claim_json: str,
    model_name: str,
    temperature: float,
    api_key: str,
) -> str:
    """Generate 3-5 targeted policy search queries from claim details using an LLM.

    Args:
        claim_json: A JSON string representing the validated claim.
        model_name: OpenAI model identifier (e.g. 'gpt-4o-mini').
        temperature: LLM sampling temperature.
        api_key: OpenAI API key.

    Returns:
        A JSON string with key 'queries' containing a list of search query strings.
    """
    import json as _json

    from langchain_openai import ChatOpenAI

    from claim_agent.pipelines.langchain_pipeline.prompts import QUERY_GENERATION_PROMPT
    from claim_agent.schemas.claim import ClaimInfo
    from claim_agent.schemas.policy import PolicyQueries

    claim = ClaimInfo(**_json.loads(claim_json))
    llm = ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
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
    return _json.dumps({"queries": result.queries})


# ---------------------------------------------------------------------------
# Tool: retrieve policy text from ChromaDB
# ---------------------------------------------------------------------------

@tool
def retrieve_policy_text(
    queries_json: str,
    chroma_persist_dir: str,
    collection_name: str,
    embedding_model: str,
    n_results: int,
) -> str:
    """Retrieve relevant policy text chunks from ChromaDB via semantic search.

    Args:
        queries_json: A JSON string with key 'queries' — a list of search query strings.
        chroma_persist_dir: Directory where ChromaDB data is persisted.
        collection_name: Name of the ChromaDB collection to query.
        embedding_model: HuggingFace model identifier for sentence-transformers.
        n_results: Maximum number of results to return per query.

    Returns:
        A JSON string with key 'chunks' containing a list of relevant policy text strings.
    """
    import json as _json

    from claim_agent.core.retrieval import retrieve_policy_text as _retrieve

    data = _json.loads(queries_json)
    queries = data["queries"]
    chunks = _retrieve(
        queries=queries,
        chroma_persist_dir=chroma_persist_dir,
        collection_name=collection_name,
        embedding_model=embedding_model,
        n_results=n_results,
    )
    return _json.dumps({"chunks": chunks})


# ---------------------------------------------------------------------------
# Tool: estimate repair cost via web search
# ---------------------------------------------------------------------------

@tool
def estimate_repair_cost(
    claim_json: str,
    inflation_threshold: float,
) -> str:
    """Search DuckDuckGo for typical market repair costs and compare to the claimed amount.

    Args:
        claim_json: A JSON string representing the claim.
        inflation_threshold: Fractional threshold above market estimate
            to flag as inflated (e.g. 0.40 means 40%).

    Returns:
        A JSON string with keys 'market_estimate' (float or null),
            'is_inflated' (bool), and 'summary' (str).
    """
    import json as _json
    import re as _re

    from duckduckgo_search import DDGS

    from claim_agent.schemas.claim import ClaimInfo

    claim = ClaimInfo(**_json.loads(claim_json))
    query = (
        f"average auto repair cost {claim.loss_description} "
        f"{claim.vehicle_details or ''} USD"
    )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
    except Exception as exc:
        return _json.dumps(
            {
                "market_estimate": None,
                "is_inflated": False,
                "summary": f"Web search unavailable ({exc}). Price check skipped.",
            }
        )

    if not results:
        return _json.dumps(
            {
                "market_estimate": None,
                "is_inflated": False,
                "summary": "No web search results found. Price check skipped.",
            }
        )

    snippets = "\n".join(
        f"- {r.get('title', '')}: {r.get('body', '')}" for r in results
    )

    # Extract dollar amounts
    pattern = r"\$\s?([\d,]+(?:\.\d{1,2})?)"
    matches = _re.findall(pattern, snippets)
    amounts: list[float] = []
    for m in matches:
        try:
            val = float(m.replace(",", ""))
            if 50 <= val <= 200_000:
                amounts.append(val)
        except ValueError:
            continue

    if not amounts:
        return _json.dumps(
            {
                "market_estimate": None,
                "is_inflated": False,
                "summary": (
                    f"Web search returned results but no clear dollar estimates.\n"
                    f"Snippets:\n{snippets}"
                ),
            }
        )

    market_estimate = sum(amounts) / len(amounts)
    threshold_amount = market_estimate * (1 + inflation_threshold)
    is_inflated = claim.estimated_repair_cost > threshold_amount

    summary = (
        f"Market estimate: ${market_estimate:,.2f} "
        f"(based on {len(amounts)} data points). "
        f"Claimed: ${claim.estimated_repair_cost:,.2f}. "
        f"Threshold ({int(inflation_threshold * 100)}% above market): "
        f"${threshold_amount:,.2f}. "
        f"{'INFLATED — claimed cost exceeds threshold.' if is_inflated else 'Within acceptable range.'}"  # noqa: E501
    )

    return _json.dumps(
        {
            "market_estimate": market_estimate,
            "is_inflated": is_inflated,
            "summary": summary,
        }
    )


# ---------------------------------------------------------------------------
# Tool: generate coverage recommendation via LLM
# ---------------------------------------------------------------------------

@tool
def generate_recommendation(
    claim_json: str,
    policy_text: str,
    market_cost_info: str,
    model_name: str,
    temperature: float,
    api_key: str,
) -> str:
    """Generate a coverage recommendation using the LLM given claim details,
    policy text, and cost data.

    Args:
        claim_json: A JSON string representing the claim.
        policy_text: Concatenated relevant policy text chunks.
        market_cost_info: Summary of market repair cost comparison.
        model_name: OpenAI model identifier (e.g. 'gpt-4o-mini').
        temperature: LLM sampling temperature.
        api_key: OpenAI API key.

    Returns:
        A JSON string with keys 'policy_section',
            'recommendation_summary', 'deductible', and 'settlement_amount'.
    """
    import json as _json

    from langchain_openai import ChatOpenAI

    from claim_agent.pipelines.langchain_pipeline.prompts import RECOMMENDATION_PROMPT
    from claim_agent.schemas.claim import ClaimInfo
    from claim_agent.schemas.policy import PolicyRecommendation

    claim = ClaimInfo(**_json.loads(claim_json))
    llm = ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
    chain = RECOMMENDATION_PROMPT | llm.with_structured_output(PolicyRecommendation)
    result: PolicyRecommendation = chain.invoke(
        {
            "claim_number": claim.claim_number,
            "policy_number": claim.policy_number,
            "date_of_loss": str(claim.date_of_loss),
            "loss_description": claim.loss_description,
            "estimated_repair_cost": claim.estimated_repair_cost,
            "vehicle_details": claim.vehicle_details or "N/A",
            "policy_text": policy_text or "No policy text available.",
            "market_cost_info": market_cost_info or "No market cost data.",
        }
    )
    return _json.dumps(
        {
            "policy_section": result.policy_section,
            "recommendation_summary": result.recommendation_summary,
            "deductible": result.deductible,
            "settlement_amount": result.settlement_amount,
        }
    )
