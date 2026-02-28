"""Prompt templates for the Smolagents pipeline.

These templates configure the ``ToolCallingAgent``'s behaviour so it follows the
strict sequential workflow: parse → validate → query → retrieve → price check →
recommend → decide.
"""

from __future__ import annotations

from smolagents import PromptTemplates

# ---------------------------------------------------------------------------
# System prompt — main instruction for the agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert insurance claim processing agent. Your job is to process a \
single insurance claim by executing a strict sequence of tool calls and then \
returning a final JSON decision.

## STRICT WORKFLOW — follow these steps IN ORDER:

1. **Parse & Validate**: Call `parse_and_validate_claim` with the claim JSON \
and the CSV path. If `is_valid` is False, SKIP to step 6 and produce a \
rejection decision immediately.

2. **Generate Policy Queries**: Call `generate_policy_queries` with the \
validated claim JSON, the model name, temperature, and API key to produce \
3-5 targeted search queries.

3. **Retrieve Policy Text**: Call `retrieve_policy_text` with the queries JSON, \
ChromaDB persist directory, collection name, embedding model, and n_results \
to retrieve relevant policy sections.

4. **Estimate Repair Cost**: Call `estimate_repair_cost` with the claim JSON \
and the inflation threshold. If `is_inflated` is True, SKIP to step 6 and \
produce a rejection decision noting the inflated cost.

5. **Generate Recommendation**: Call `generate_recommendation` with the claim \
JSON, the concatenated policy text, the market cost summary, model name, \
temperature, and API key.

6. **Final Decision**: Return a JSON object with EXACTLY these keys:
   - `claim_number` (str)
   - `covered` (bool)
   - `deductible` (float, >= 0)
   - `recommended_payout` (float, >= 0)
   - `notes` (str — explanation of the decision)

## RULES:
- Do NOT skip steps or change the order (except when short-circuiting on \
  invalid/inflated claims as described).
- Do NOT invent information — use ONLY tool outputs.
- Always return the final decision as valid JSON matching the schema above.
- Pass the exact tool parameter values provided in the task description.
"""

# ---------------------------------------------------------------------------
# Planning prompts
# ---------------------------------------------------------------------------

PLANNING_INITIAL = """\
Here is my plan to process this insurance claim:
1. Parse and validate the claim against the CSV policy records.
2. If valid, generate policy search queries using the LLM.
3. Retrieve relevant policy text from ChromaDB.
4. Estimate repair cost from web search and check for inflation.
5. If not inflated, generate a coverage recommendation via LLM.
6. Assemble and return the final claim decision JSON.
"""

PLANNING_UPDATE_PRE = """\
Let me review my progress and update the plan based on what I've learned so far.
"""

PLANNING_UPDATE_POST = """\
Based on the results so far, here is my updated plan for the remaining steps:
"""

# ---------------------------------------------------------------------------
# Managed agent prompts (not used in single-agent setup, but required by type)
# ---------------------------------------------------------------------------

MANAGED_AGENT_TASK = """\
You are a managed sub-agent. Execute the task given to you and report back.
Task: {{task}}
"""

MANAGED_AGENT_REPORT = """\
Here is my report on the completed task:
"""

# ---------------------------------------------------------------------------
# Final answer prompts
# ---------------------------------------------------------------------------

FINAL_ANSWER_PRE = """\
Based on all the tool outputs collected during claim processing, I will now \
produce the final claim decision.
"""

FINAL_ANSWER_POST = """\
Return the final answer as a JSON object with keys: claim_number, covered, \
deductible, recommended_payout, notes.
"""


# ---------------------------------------------------------------------------
# Assembled PromptTemplates object
# ---------------------------------------------------------------------------

def get_prompt_templates() -> PromptTemplates:
    """Return the configured ``PromptTemplates`` for the claim-processing agent."""
    return PromptTemplates(
        system_prompt=SYSTEM_PROMPT,
        planning={
            "initial_plan": PLANNING_INITIAL,
            "update_plan_pre_messages": PLANNING_UPDATE_PRE,
            "update_plan_post_messages": PLANNING_UPDATE_POST,
        },
        managed_agent={
            "task": MANAGED_AGENT_TASK,
            "report": MANAGED_AGENT_REPORT,
        },
        final_answer={
            "pre_messages": FINAL_ANSWER_PRE,
            "post_messages": FINAL_ANSWER_POST,
        },
    )
