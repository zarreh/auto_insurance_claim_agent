# Implementation Plan

!!! info "Origin"
    This document was the AI-generated implementation plan that guided the
    development of the Claim Processing Agent. It is preserved here as part
    of the project's planning history.

---

# Plan: Intelligent Insurance Claim Processing Agent

**TL;DR** — Build a production-grade Agentic RAG insurance claim processor with dual pipelines (LangChain/LangGraph first, Smolagents second), FastAPI backend, Streamlit frontend, ChromaDB vector store, and Docker deployment. The system ingests claims as JSON, validates against CSV policy records, retrieves relevant policy text via semantic search, estimates repair costs via DuckDuckGo web search, and produces structured coverage decisions. LLM: OpenAI GPT-4o. Configuration via Hydra, dependencies via Poetry. Git initialized from the start; server IP and remote repo to be provided later.

---

## Phase 1: Project Scaffolding & Configuration *(Effort: Medium)*

**Goal:** Set up the project skeleton, dependency management, Git, and Hydra configuration so all subsequent phases have a solid foundation.

### Step 1.1 — Git init & ignore rules
- Run `git init`
- Create `.gitignore` — ignore `__pycache__`, `.venv`, `data/chroma_db/`, `*.egg-info`, `.env`, `poetry.lock` (optional), `dist/`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `notebook/`

### Step 1.2 — Poetry project setup
- Create `pyproject.toml` with Python `^3.12` and dependency groups:
  - **core**: `pydantic>=2.0`, `hydra-core>=1.3`, `omegaconf`, `chromadb>=0.4`, `sentence-transformers`, `pypdf2`, `openai>=1.0`, `pandas`
  - **langchain**: `langchain>=0.3`, `langchain-openai`, `langchain-community`, `langchain-chroma`, `langgraph>=0.2`, `duckduckgo-search`
  - **smolagents**: `smolagents[toolkit]`
  - **api**: `fastapi>=0.110`, `uvicorn[standard]`
  - **frontend**: `streamlit>=1.30`, `requests`
  - **logging**: `loguru`
  - **dev**: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pre-commit`
- Set package source as `src/claim_agent`

### Step 1.3 — Directory structure creation
- Create the full directory tree per the spec
- Add `__init__.py` files to all Python packages

### Step 1.4 — Hydra configuration files
- `conf/config.yaml` — Main config with defaults list
- `conf/pipeline/langchain.yaml` — LangGraph-specific settings
- `conf/pipeline/smolagents.yaml` — agent-specific settings
- `conf/llm/openai.yaml` — model settings with env var reference
- `conf/vectordb/chroma.yaml` — embedding and collection settings
- `conf/logging/default.yaml` — log level and format
- `conf/server/default.yaml` — host, port, CORS

### Step 1.5 — Environment template
- Create `.env.example` with `OPENAI_API_KEY=your-key-here`

### Step 1.6 — Update coverage_data.csv
- Extend policies to have future `coverage_end_date` for demo testing

### Step 1.7 — Makefile
- All targets: `install`, `run-api`, `run-frontend`, `run`, `docker-build`, `docker-up`, `docker-down`, `test`, `lint`, `format`, `clean`, `ingest`

---

## Phase 2: Pydantic Schemas & Logging *(Effort: Small)*

**Goal:** Define all shared data models and set up colored logging.

### Step 2.1 — Pydantic schemas
- `ClaimInfo` — claim number, policy number, claimant name, date of loss, loss description, estimated repair cost, vehicle details
- `ClaimDecision` — covered, deductible, recommended payout, notes
- `PolicyQueries` — list of search queries
- `PolicyRecommendation` — policy section, recommendation summary, deductible, settlement amount

### Step 2.2 — Logging setup
- Loguru with colored console output (dev) or structured JSON (prod)
- Intercept standard `logging` module
- Contextual fields: claim number, pipeline type, tool name, timing

---

## Phase 3: Core Business Logic *(Effort: Medium)*

**Goal:** Implement shared domain logic (validation, ingestion, retrieval).

### Step 3.1 — Claim validation
- Check policy exists, no premium dues, date within coverage period

### Step 3.2 — PDF ingestion
- Extract text, chunk, embed via `sentence-transformers`, store in ChromaDB

### Step 3.3 — Policy retrieval
- Semantic similarity search against ChromaDB collection

---

## Phase 4: LangChain/LangGraph Pipeline *(Effort: Large)*

**Goal:** LangGraph stateful graph for explicit orchestration.

### Step 4.1 — Pipeline interface (abstract base class)
### Step 4.2 — Pipeline factory
### Step 4.3 — LangGraph state and tools
### Step 4.4 — LangGraph state graph (conditional edges for VALIDATE and PRICE CHECK)
### Step 4.5 — Prompt templates
### Step 4.6 — Pipeline class

---

## Phase 5: Smolagents Pipeline *(Effort: Medium)*

**Goal:** Autonomous agent with the same inputs/outputs.

### Step 5.1 — Smolagents tools (`@tool` decorated functions)
### Step 5.2 — Prompt templates
### Step 5.3 — Pipeline class

---

## Phase 6: FastAPI Backend *(Effort: Medium)*

**Goal:** REST API with error handling, CORS, and logging middleware.

### Step 6.1 — App factory
### Step 6.2 — API routes
### Step 6.3 — Middleware
### Step 6.4 — Server entry point

---

## Phase 7: Streamlit Frontend *(Effort: Medium–Large)*

**Goal:** Polished, portfolio-worthy UI communicating via REST API.

### Step 7.1 — API client
### Step 7.2 — Custom styles
### Step 7.3 — UI components (form, result card, trace viewer)
### Step 7.4 — Main app

---

## Phase 8: Docker & Deployment *(Effort: Medium)*

**Goal:** Containerize both services.

### Step 8.1 — Backend Dockerfile (multi-stage)
### Step 8.2 — Frontend Dockerfile
### Step 8.3 — Docker Compose

---

## Phase 9: Testing *(Effort: Medium)*

**Goal:** Unit and integration tests covering critical paths (58 tests).

### Step 9.1 — Fixtures
### Step 9.2 — Unit tests (schemas, validation, retrieval)
### Step 9.3 — Integration tests (LangGraph pipeline, Smolagents pipeline, API)

---

## Phase 10: Documentation & Polish *(Effort: Small)*

### Step 10.1 — MkDocs documentation site
### Step 10.2 — Sample claims
### Step 10.3 — Final polish

---

## Key Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over plain LangChain chains** | Stateful graph with conditional edges maps directly to the workflow diagram |
| **LangChain/LangGraph first** | More mature ecosystem, explicit graph gives reliable baseline |
| **DuckDuckGo for web search** | No API key needed |
| **Loguru over colorlog/rich** | Simpler API, built-in colored output, structured logging |
| **Multi-stage Dockerfile** | Keeps image size small |
| **`all-MiniLM-L6-v2` embeddings** | Fast, lightweight, good on CPU |

---

## Risk Areas & Mitigations

| Risk | Mitigation |
|---|---|
| **LLM response format** | `with_structured_output()` + retry |
| **Smolagents unpredictability** | Strict system prompt + max iterations + output validation |
| **Vector search quality** | Tuned chunk size/overlap + logging |
| **Web search flakiness** | Try/except fallback + cache + timeout |
| **ChromaDB persistence** | Docker volume mount + startup check |
| **Hydra + FastAPI** | `hydra.utils.get_original_cwd()` or `compose` API |
