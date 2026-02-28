"""Prompt templates for the LangChain / LangGraph pipeline."""

from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# Query Generation — produce 3-5 targeted policy search queries
# ---------------------------------------------------------------------------

QUERY_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert insurance claims analyst. Given a claim's details, "
            "generate 3 to 5 targeted search queries that would help locate the most "
            "relevant sections of an auto insurance policy document.\n\n"
            "Focus on:\n"
            "- The type of coverage applicable (collision, comprehensive, liability, etc.)\n"
            "- Deductible and limit clauses\n"
            "- Exclusions or endorsements that might apply\n"
            "- Conditions for claim validity\n\n"
            "Return your answer as a JSON object with a single key 'queries' "
            "containing a list of query strings.",
        ),
        (
            "human",
            "Claim details:\n"
            "- Claim Number: {claim_number}\n"
            "- Policy Number: {policy_number}\n"
            "- Date of Loss: {date_of_loss}\n"
            "- Loss Description: {loss_description}\n"
            "- Estimated Repair Cost: ${estimated_repair_cost:,.2f}\n"
            "- Vehicle: {vehicle_details}\n\n"
            "Generate the search queries now.",
        ),
    ]
)

# ---------------------------------------------------------------------------
# Coverage Recommendation — determine coverage, deductible, payout
# ---------------------------------------------------------------------------

RECOMMENDATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior insurance underwriter. Based on the claim details, "
            "the relevant policy text retrieved from the insurance document, and the "
            "market repair cost estimate, determine:\n\n"
            "1. Whether the collision/loss is covered under the policy.\n"
            "2. The applicable policy section.\n"
            "3. The deductible amount (if any).\n"
            "4. The recommended settlement amount.\n\n"
            "Provide a concise recommendation summary explaining your reasoning.\n\n"
            "Return your answer as a JSON object with keys: "
            "'policy_section', 'recommendation_summary', 'deductible', 'settlement_amount'.",
        ),
        (
            "human",
            "== CLAIM DETAILS ==\n"
            "Claim Number: {claim_number}\n"
            "Policy Number: {policy_number}\n"
            "Date of Loss: {date_of_loss}\n"
            "Loss Description: {loss_description}\n"
            "Estimated Repair Cost: ${estimated_repair_cost:,.2f}\n"
            "Vehicle: {vehicle_details}\n\n"
            "== RELEVANT POLICY TEXT ==\n"
            "{policy_text}\n\n"
            "== MARKET REPAIR COST ESTIMATE ==\n"
            "{market_cost_info}\n\n"
            "Provide your coverage recommendation now.",
        ),
    ]
)
