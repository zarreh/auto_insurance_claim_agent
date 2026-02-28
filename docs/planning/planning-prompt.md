# Planning Prompt

!!! info "Origin"
    This document is the original planning prompt that was used to generate
    the implementation plan. It describes the full project requirements,
    architecture, and constraints.

---

## Context & Role

You are an expert software architect and senior Python developer. Your task is to create a **detailed implementation plan** for a production-grade, portfolio-worthy insurance claim processing application. The plan should be thorough enough that a developer can follow it step-by-step to build the entire system from scratch.

---

## Project Purpose

Build an **Agentic RAG (Retrieval-Augmented Generation) Insurance Claim Processing System** that automates the evaluation of auto insurance claims. The system ingests a claim (as structured JSON), validates it against policy records (CSV), retrieves relevant policy language from insurance documents (PDF) via vector search, estimates repair costs using web search, and produces a structured coverage decision — all orchestrated by an AI agent.

### Core Domain Workflow

The claim processing pipeline follows this strict sequential logic:

1. **Parse Claim** — Accept a structured claim (JSON) containing: claim number, policy number, claimant name, date of loss, loss description, estimated repair cost, and vehicle details. Validate the claim payload against a defined schema (Pydantic model).

2. **Validate Claim** — Cross-reference the parsed claim against policy records stored in a CSV file (`coverage_data.csv`). Check:
   - The policy number exists in the records.
   - There are no outstanding premium dues.
   - The date of loss falls within the policy's coverage period (between `coverage_start_date` and `coverage_end_date`).
   - If any check fails, short-circuit with an "invalid claim" decision.

3. **Generate Policy Queries** — Using the LLM, analyze the claim details to produce 3–5 targeted search queries for relevant policy sections (e.g., collision coverage, liability limits, deductibles, exclusions, endorsements).

4. **Retrieve Policy Text** — Embed the generated queries and perform semantic similarity search against a vector database (ChromaDB) populated with chunked text from the insurance policy PDF (`policy.pdf`). Return the most relevant policy text segments.

5. **Estimate Repair Cost (Web Search)** — Use a web search tool to look up typical market repair costs for the type of damage described in the claim. Compare the estimated cost to the claimant's stated repair cost. If the claimed amount is unreasonably inflated, flag the claim as invalid.

6. **Generate Recommendation** — Using the validated claim details, retrieved policy text, and repair cost estimate, prompt the LLM to determine: whether the collision is covered, the applicable policy section, the deductible amount, and the recommended settlement amount.

7. **Finalize Decision** — Assemble the final `ClaimDecision` object with: claim number, coverage status (boolean), deductible, recommended payout, and explanatory notes.

### Data Sources

- **`coverage_data.csv`** — A CSV file containing policy records with columns: `policy_number`, `premium_dues_remaining` (boolean), `coverage_start_date`, `coverage_end_date`.
- **`policy.pdf`** — An auto insurance policy document. Text is extracted, chunked, embedded, and stored in a vector database for semantic retrieval.

### Pydantic Data Models

- **`ClaimInfo`** — Fields: `claim_number`, `policy_number`, `claimant_name`, `date_of_loss`, `loss_description`, `estimated_repair_cost`, `vehicle_details` (optional).
- **`PolicyQueries`** — Field: `queries` (list of strings).
- **`PolicyRecommendation`** — Fields: `policy_section`, `recommendation_summary`, `deductible` (optional float), `settlement_amount` (optional float).
- **`ClaimDecision`** — Fields: `claim_number`, `covered` (bool), `deductible` (float), `recommended_payout` (float), `notes` (optional string).

---

## Architecture Requirements

### Dual-Pipeline Backend (Interchangeable via Configuration)

The system must support **two independent pipeline implementations** that solve the same problem but use different agentic frameworks. The active pipeline is selected via a Hydra configuration file — switching between them should require **only a config change**, not a code change.

#### Pipeline 1: Smolagents Pipeline
- Use the `smolagents` library (`ToolCallingAgent`, `@tool` decorator, `OpenAIServerModel`).
- Define each processing step as a `@tool`-decorated function.
- Configure the agent with custom `PromptTemplates`.
- Include `WebSearchTool` for repair cost estimation.
- The agent autonomously orchestrates tool invocation order based on prompts.

#### Pipeline 2: LangChain/LangGraph Pipeline
- Use LangChain and LangGraph to implement the same workflow.
- LangGraph stateful workflow with conditional branching at VALIDATE and PRICE CHECK nodes.
- Use LangChain's vector store integrations for ChromaDB and document loaders for PDF.
- Use LangChain's web search tool integration for repair cost estimation.

#### Pipeline Abstraction
- Define a **common interface** (abstract base class) that both pipelines implement.
- A **factory function** that reads the Hydra config and instantiates the correct pipeline.
- Both pipelines must produce the same `ClaimDecision` output schema.

### Frontend (Streamlit)

- A **visually polished** Streamlit application communicating via REST API.
- Features: claim form/JSON upload, result card, processing indicator, reasoning trace viewer.

### REST API (FastAPI)

- `POST /api/v1/claims/process` — Process claim and return `ClaimDecision`.
- `GET /api/v1/health` — Health check.
- `GET /api/v1/pipelines` — List available pipeline types.
- CORS, error handling, logging middleware.

### Logging

- Loguru with colored console output and structured JSON mode.
- Contextual fields: claim number, pipeline type, tool name, timing.

### Configuration (Hydra)

- Pipeline selection, LLM settings, embedding model, vector DB, data paths, server, logging.
- API keys from environment variables.

### Docker & Deployment

- Multi-stage `Dockerfile` for backend.
- Separate `frontend/Dockerfile`.
- `docker-compose.yml` with backend, frontend, networking, health checks.

### Makefile

Targets: `install`, `run-api`, `run-frontend`, `run`, `docker-build`, `docker-up`, `docker-down`, `test`, `lint`, `format`, `clean`, `ingest`.

---

## Code Quality Guidelines

- **Readability over cleverness**
- **Prevent excessive coding** — don't over-engineer
- **Type hints everywhere**
- **Docstrings** for all public functions
- **Error handling** with informative messages
- **Separation of concerns**
- **Testability** with dependency injection
- **Configuration-driven** via Hydra

---

## Constraints

- Python 3.12+
- Poetry for dependency management
- Hydra for configuration
- Docker for deployment
- FastAPI for REST API
- Streamlit for frontend
- Dual pipelines interchangeable via config
- Frontend ↔ Backend communication via REST API only
- Colored logging on backend
- Makefile for common commands
- **Portfolio project** — impressive, well-documented, demonstrating mastery of agentic AI patterns
