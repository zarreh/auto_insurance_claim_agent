# Planning Prompt: Intelligent Insurance Claim Processing Agent

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
- **`policy.pdf`** — An auto insurance policy document. Text is extracted, chunked (e.g., by paragraph or page), embedded, and stored in a vector database for semantic retrieval.

### Pydantic Data Models

The system uses these structured schemas throughout the pipeline:

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
- Define each processing step (parse, validate, query generation, retrieval, recommendation, decision) as a `@tool`-decorated function.
- Configure the agent with custom `PromptTemplates` (system prompt, planning prompt, managed agent prompt, final answer prompt).
- Include `WebSearchTool` from smolagents for repair cost estimation.
- The agent autonomously orchestrates tool invocation order based on its system and planning prompts.

#### Pipeline 2: LangChain/LangGraph Pipeline
- Use LangChain and/or LangGraph to implement the same workflow.
- Consider one or more of these patterns (choose the best fit):
  - **LangGraph stateful workflow**: Define a graph with nodes for each processing step and edges encoding the sequential (and conditional) flow. This gives explicit control over the execution order and allows conditional branching (e.g., short-circuit on invalid claim).
  - **Multi-agent architecture**: Separate agents or chains for validation, retrieval, recommendation, and decision — coordinated by a supervisor or router.
  - **Custom chain with skills/tools**: Use LangChain's tool-calling capabilities with a structured chain of prompts and tool invocations.
- Use LangChain's vector store integrations for ChromaDB and its document loaders for PDF processing.
- Use LangChain's web search tool integration for repair cost estimation.

#### Pipeline Abstraction
- Define a **common interface** (abstract base class or protocol) that both pipelines implement. This interface should expose at minimum:
  - `process_claim(claim_path: str) -> ClaimDecision` — the main entry point.
  - Any necessary initialization (loading models, setting up vector stores, etc.).
- A **factory function or class** that reads the Hydra config and instantiates the correct pipeline.
- Both pipelines must consume the same data sources and produce the same `ClaimDecision` output schema. This is also the entity that the REST API returns to the frontend.

### Frontend (Streamlit)

- A **visually polished, aesthetically pleasant** Streamlit application. This is a portfolio project — the UI should look professional and impressive.
- The frontend communicates with the backend **exclusively through REST API calls** (no direct Python imports from the backend).
- Key UI features:
  - A clean, modern layout with proper spacing, typography, and color scheme.
  - A form or JSON editor to input/upload claim data (JSON file or manual entry).
  - A "Process Claim" button that triggers the API call.
  - A results panel that displays the `ClaimDecision` in a clear, card-based or dashboard-style format (coverage status with color indicators, deductible, payout, notes).
  - A processing status/progress indicator while the claim is being evaluated.
  - An expandable section or tab showing the agent's reasoning trace / intermediate steps (tool calls, retrieved policy text, etc.) — this makes the agentic process transparent and is great for portfolio demonstration.
  - Error handling with user-friendly messages.
  - Optional: support for processing multiple claims, viewing claim history, or uploading new policy documents.

### REST API (Backend Server)

- Use **FastAPI** as the REST API framework.
- Endpoints:
  - `POST /api/v1/claims/process` — Accept claim JSON, run the active pipeline, return the `ClaimDecision`.
  - `GET /api/v1/claims/{claim_id}/status` — (Optional) For async processing, check claim status.
  - `GET /api/v1/health` — Health check endpoint.
  - Additional endpoints as needed (e.g., `GET /api/v1/pipelines` to list available pipeline types, upload policy documents, etc.).
- Request/response schemas defined with Pydantic models (shared with the pipeline schemas).
- Proper error handling, input validation, and HTTP status codes.
- CORS configuration to allow the Streamlit frontend to call the API.

### Logging

- **Full logging visibility** on the backend. Every significant action should be logged: claim received, validation result, queries generated, policy text retrieved, recommendation generated, decision finalized, errors, etc.
- Use Python's `logging` module with **colored console output** for better developer experience. Use a library such as `colorlog`, `rich`, or `loguru` for colored and structured logging.
- Log levels used meaningfully: `DEBUG` for detailed trace, `INFO` for high-level flow, `WARNING` for recoverable issues, `ERROR` for failures.
- Include contextual information in log messages: claim number, pipeline type, tool name, timing, etc.
- Consider structured logging (JSON format) for production, with colored pretty-printing for development — switchable via config.

### Configuration (Hydra)

- Use **Hydra** for all configuration management.
- Configuration should cover:
  - Active pipeline selection (`pipeline: smolagents` or `pipeline: langchain`).
  - LLM settings (model ID, API base URL, API key reference, temperature, max tokens).
  - Embedding model settings (model name, device).
  - Vector database settings (collection name, number of results to retrieve).
  - Data paths (coverage CSV path, policy PDF path, claim input directory).
  - API server settings (host, port, debug mode).
  - Logging settings (level, format, colored output toggle).
  - Frontend settings (API base URL).
- Use Hydra's config groups for pipeline-specific settings (each pipeline can have its own config sub-file).
- API keys should be loaded from environment variables, not hardcoded in config files.

### Dependency Management (Poetry)

- Use **Poetry** for dependency management.
- Organize dependencies into groups:
  - Core: `pydantic`, `hydra-core`, `omegaconf`, `chromadb`, `sentence-transformers`, `PyPDF2`, `openai`.
  - Smolagents pipeline: `smolagents[toolkit]`.
  - LangChain pipeline: `langchain`, `langchain-openai`, `langchain-community`, `langgraph` (as needed).
  - API: `fastapi`, `uvicorn`.
  - Frontend: `streamlit`, `requests`.
  - Logging: `colorlog` or `rich` or `loguru`.
  - Dev: `pytest`, `ruff`, `mypy`, `pre-commit`.
- Pin versions where important for reproducibility.

### Docker & Deployment

- The application is deployed on a **Linux server using Docker**.
- Provide a `Dockerfile` (or multi-stage Dockerfile) that:
  - Uses an appropriate Python base image.
  - Installs Poetry and project dependencies.
  - Copies application code.
  - Exposes the API port.
  - Sets the entrypoint to run the FastAPI server.
- Provide a `docker-compose.yml` that:
  - Defines services for the backend API and the Streamlit frontend.
  - Sets environment variables (API keys, etc.) via `.env` file.
  - Configures networking so the frontend can reach the API.
  - Optionally includes a persistent volume for the ChromaDB data.
- Consider health checks in compose.

### Makefile

- Provide a `Makefile` with convenient targets:
  - `make install` — Install dependencies via Poetry.
  - `make run-api` — Start the FastAPI backend server locally.
  - `make run-frontend` — Start the Streamlit frontend locally.
  - `make run` — Start both backend and frontend.
  - `make docker-build` — Build Docker images.
  - `make docker-up` — Start services via docker-compose.
  - `make docker-down` — Stop services.
  - `make test` — Run tests.
  - `make lint` — Run linting (ruff, mypy).
  - `make format` — Auto-format code.
  - `make clean` — Remove caches, build artifacts, etc.
  - `make ingest` — Run the policy document ingestion (PDF → ChromaDB) as a standalone step.

---

## Project Structure

Plan the project as a well-organized Python package. Suggested layout:

```
projects/claim_process_agent/
├── pyproject.toml                    # Poetry config
├── poetry.lock
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── .env.example                      # Template for environment variables
├── README.md                         # Project documentation (portfolio-facing)
│
├── conf/                             # Hydra configuration
│   ├── config.yaml                   # Main config
│   ├── pipeline/
│   │   ├── smolagents.yaml
│   │   └── langchain.yaml
│   ├── llm/
│   │   └── openai.yaml
│   ├── vectordb/
│   │   └── chroma.yaml
│   ├── logging/
│   │   └── default.yaml
│   └── server/
│       └── default.yaml
│
├── data/
│   ├── coverage_data.csv
│   ├── policy.pdf
│   └── chroma_db/                    # Persisted vector store (gitignored)
│
├── src/
│   └── claim_agent/
│       ├── __init__.py
│       ├── schemas/                  # Pydantic models (shared across pipelines)
│       │   ├── __init__.py
│       │   ├── claim.py              # ClaimInfo, ClaimDecision
│       │   └── policy.py             # PolicyQueries, PolicyRecommendation
│       │
│       ├── core/                     # Core business logic (shared)
│       │   ├── __init__.py
│       │   ├── ingestion.py          # PDF loading, chunking, embedding, ChromaDB insertion
│       │   ├── validation.py         # Claim validation against coverage_data.csv
│       │   └── retrieval.py          # ChromaDB query logic
│       │
│       ├── pipelines/                # Pipeline implementations
│       │   ├── __init__.py
│       │   ├── base.py               # Abstract pipeline interface
│       │   ├── factory.py            # Pipeline factory (reads config, returns the right pipeline)
│       │   ├── smolagents_pipeline/
│       │   │   ├── __init__.py
│       │   │   ├── pipeline.py       # SmolAgents pipeline implementation
│       │   │   ├── tools.py          # @tool-decorated functions
│       │   │   └── prompts.py        # Prompt templates
│       │   └── langchain_pipeline/
│       │       ├── __init__.py
│       │       ├── pipeline.py       # LangChain/LangGraph pipeline implementation
│       │       ├── tools.py          # LangChain tool definitions
│       │       ├── chains.py         # Chain/graph definitions
│       │       └── prompts.py        # Prompt templates
│       │
│       ├── api/                      # FastAPI application
│       │   ├── __init__.py
│       │   ├── app.py                # FastAPI app factory
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   └── claims.py         # Claim processing endpoints
│       │   └── middleware.py         # CORS, logging middleware, etc.
│       │
│       └── logging/                  # Logging setup
│           ├── __init__.py
│           └── setup.py              # Colored logging configuration
│
├── frontend/
│   ├── app.py                        # Streamlit application
│   ├── components/                   # Reusable UI components
│   │   ├── __init__.py
│   │   ├── claim_form.py
│   │   ├── result_card.py
│   │   └── trace_viewer.py
│   ├── api_client.py                 # REST API client wrapper
│   ├── styles.py                     # Custom CSS/theme
│   └── assets/                       # Images, icons, etc.
│
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Shared fixtures
    ├── test_schemas.py
    ├── test_validation.py
    ├── test_retrieval.py
    ├── test_smolagents_pipeline.py
    ├── test_langchain_pipeline.py
    └── test_api.py
```

---

## Code Quality Guidelines

- **Readability over cleverness**: Write code that is easy to trace and debug. Avoid overly abstract patterns, excessive metaprogramming, or deeply nested callbacks. A developer should be able to follow the code linearly.
- **Prevent excessive coding**: Don't over-engineer. If a simple function does the job, don't wrap it in three layers of abstraction. Keep the class hierarchy shallow.
- **Type hints everywhere**: Use Python type hints for all function signatures and class attributes.
- **Docstrings**: Write clear docstrings for all public functions and classes.
- **Error handling**: Use explicit try/except blocks with informative error messages. Never silently swallow exceptions. Log errors with context.
- **Separation of concerns**: Keep business logic, API logic, and UI logic cleanly separated. The core domain logic should not depend on any framework.
- **Testability**: Write code that is easy to test. Inject dependencies where possible. Avoid global state.
- **Configuration-driven**: Hardcode nothing. All tunables go through Hydra config.

---

## What to Produce in the Plan

Your plan should include:

1. **Phase breakdown**: Divide the work into logical phases (e.g., Phase 1: Project scaffolding & config, Phase 2: Core domain logic, Phase 3: Smolagents pipeline, Phase 4: LangChain pipeline, Phase 5: REST API, Phase 6: Frontend, Phase 7: Docker & deployment, Phase 8: Testing & polish).

2. **For each phase**, provide:
   - The specific files to create or modify.
   - The key classes, functions, or components to implement.
   - The dependencies between phases.
   - Any important design decisions or trade-offs to call out.
   - Estimated relative effort (small/medium/large).

3. **Interface contracts**: Define the exact signatures for the pipeline abstract interface, the API request/response schemas, and the API client interface used by the frontend.

4. **Configuration schema**: Outline the full Hydra config structure with example values.

5. **Docker strategy**: Describe the Dockerfile and docker-compose setup, including how the frontend and backend communicate in containerized mode.

6. **Testing strategy**: What to test, how to test it (unit vs. integration), and what fixtures/mocks are needed.

7. **Risk areas & mitigations**: Identify parts of the system that are most likely to cause issues (e.g., agent unpredictability, LLM response format compliance, vector search quality) and suggest mitigations.

---

## Constraints

- Python 3.12+.
- Poetry for dependency management.
- Hydra for configuration.
- Docker for deployment.
- FastAPI for the REST API.
- Streamlit for the frontend.
- The two pipelines (smolagents and langchain/langgraph) must be fully interchangeable via config.
- The frontend and backend must communicate only via REST API.
- Colored logging on the backend.
- Makefile for common commands.
- The code must be clean, understandable, and debuggable — not excessively abstracted or clever.
- **This is a portfolio project** — the end result should be impressive to look at, well-documented, and demonstrate mastery of agentic AI patterns.
