# Plan: Intelligent Insurance Claim Processing Agent

**TL;DR** — Build a production-grade Agentic RAG insurance claim processor with dual pipelines (LangChain/LangGraph first, Smolagents second), FastAPI backend, Streamlit frontend, ChromaDB vector store, and Docker deployment. The system ingests claims as JSON, validates against CSV policy records, retrieves relevant policy text via semantic search, estimates repair costs via DuckDuckGo web search, and produces structured coverage decisions. LLM: OpenAI GPT-4o. Configuration via Hydra, dependencies via Poetry. Git initialized from the start; server IP and remote repo to be provided later.

---

## Phase 1: Project Scaffolding & Configuration *(Effort: Medium)*

**Goal:** Set up the project skeleton, dependency management, Git, and Hydra configuration so all subsequent phases have a solid foundation.

### Step 1.1 — Git init & ignore rules
- Run `git init` in `/home/alireza/greatlearning/agentic_ai_jhu/projects/claim_process_agent/`
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
- Create the full directory tree per the spec in PLANNING_PROMPT.md:
  - `src/claim_agent/` with `schemas/`, `core/`, `pipelines/` (with `smolagents_pipeline/` and `langchain_pipeline/` subdirs), `api/routes/`, `logging/`
  - `frontend/` with `components/`, `assets/`
  - `conf/` with `pipeline/`, `llm/`, `vectordb/`, `logging/`, `server/`
  - `tests/`
- Add `__init__.py` files to all Python packages

### Step 1.4 — Hydra configuration files
- `conf/config.yaml` — Main config with defaults list:
  ```yaml
  defaults:
    - pipeline: langchain
    - llm: openai
    - vectordb: chroma
    - logging: default
    - server: default
  data:
    coverage_csv: data/coverage_data.csv
    policy_pdf: data/policy.pdf
    chroma_persist_dir: data/chroma_db
  ```
- `conf/pipeline/langchain.yaml` — `type: langchain`, LangGraph-specific settings
- `conf/pipeline/smolagents.yaml` — `type: smolagents`, agent-specific settings
- `conf/llm/openai.yaml` — `model: gpt-4o-mini`, `temperature: 0.1`, `max_tokens: 4096`, `api_key: ${oc.env:OPENAI_API_KEY}`
- `conf/vectordb/chroma.yaml` — `collection_name: policy_chunks`, `embedding_model: all-MiniLM-L6-v2`, `n_results: 5`, `chunk_size: 500`, `chunk_overlap: 50`
- `conf/logging/default.yaml` — `level: INFO`, `colored: true`, `format: structured`
- `conf/server/default.yaml` — `host: 0.0.0.0`, `port: 8000`, `debug: false`, `cors_origins: ["http://localhost:8501"]`

### Step 1.5 — Environment template
- Create `.env.example` with `OPENAI_API_KEY=your-key-here`

### Step 1.6 — Update coverage_data.csv
- Update `data/coverage_data.csv`: extend at least 5 policies (PN-2, PN-4, PN-6, PN-8, PN-10) to have `coverage_end_date` in 2026–2027 so current-date claims can pass validation. Keep some expired/dues-remaining policies for rejection testing.

### Step 1.7 — Makefile
- Create `Makefile` with all targets specified in the prompt: `install`, `run-api`, `run-frontend`, `run`, `docker-build`, `docker-up`, `docker-down`, `test`, `lint`, `format`, `clean`, `ingest`

---

## Phase 2: Pydantic Schemas & Logging *(Effort: Small)*

**Goal:** Define all shared data models and set up colored logging — these are foundational and used by every subsequent phase.

### Step 2.1 — Pydantic schemas
- `src/claim_agent/schemas/claim.py`:
  - `ClaimInfo` — `claim_number: str`, `policy_number: str`, `claimant_name: str`, `date_of_loss: date`, `loss_description: str`, `estimated_repair_cost: float`, `vehicle_details: Optional[str]`
  - `ClaimDecision` — `claim_number: str`, `covered: bool`, `deductible: float`, `recommended_payout: float`, `notes: Optional[str]`
- `src/claim_agent/schemas/policy.py`:
  - `PolicyQueries` — `queries: list[str]`
  - `PolicyRecommendation` — `policy_section: str`, `recommendation_summary: str`, `deductible: Optional[float]`, `settlement_amount: Optional[float]`
- `src/claim_agent/schemas/__init__.py` — Re-export all models

### Step 2.2 — Logging setup
- `src/claim_agent/logging/setup.py`:
  - Function `setup_logging(cfg)` that configures `loguru` with colored console output (dev mode) or structured JSON (prod mode), controlled by Hydra config
  - Intercept standard `logging` module to route through loguru
  - Include contextual fields: claim number, pipeline type, tool name, timing

---

## Phase 3: Core Business Logic *(Effort: Medium)*

**Goal:** Implement the shared domain logic (validation, ingestion, retrieval) that both pipelines will use. These are plain Python functions — no framework dependency.

### Step 3.1 — Claim validation
- `src/claim_agent/core/validation.py`:
  - `validate_claim(claim: ClaimInfo, csv_path: str) -> tuple[bool, str]`
  - Loads `coverage_data.csv` via pandas
  - Checks: (1) policy exists, (2) `premium_dues_remaining == False`, (3) `coverage_start_date <= date_of_loss <= coverage_end_date`
  - Returns `(is_valid, reason_string)`
  - All failures are descriptive (e.g., "Policy PN-99 not found in records")

### Step 3.2 — PDF ingestion
- `src/claim_agent/core/ingestion.py`:
  - `ingest_policy_pdf(pdf_path: str, chroma_persist_dir: str, collection_name: str, embedding_model: str, chunk_size: int, chunk_overlap: int) -> None`
  - Extract text from PDF using PyPDF2
  - Chunk by paragraph/page with configurable `chunk_size` and `chunk_overlap`
  - Compute embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`)
  - Store in ChromaDB with persistent storage at `data/chroma_db/`
  - Idempotent: skip ingestion if collection already exists and has documents
  - Standalone CLI entry point for `make ingest`

### Step 3.3 — Policy retrieval
- `src/claim_agent/core/retrieval.py`:
  - `retrieve_policy_text(queries: list[str], chroma_persist_dir: str, collection_name: str, embedding_model: str, n_results: int) -> list[str]`
  - Connect to persisted ChromaDB collection
  - Embed each query and perform similarity search
  - Deduplicate and return top relevant chunks
  - Log retrieved chunks with scores

---

## Phase 4: LangChain/LangGraph Pipeline *(Effort: Large)*

**Goal:** Implement the first (primary) pipeline using LangGraph's stateful graph for explicit orchestration. This matches the workflow diagram exactly: PARSE → VALIDATE → [INVALID → DONE] / [VALID → CHECK POLICY → GENERATE RECOMMENDATION → PRICE CHECK → [INFLATED → DONE] / [OK → FINAL DECISION]]

### Step 4.1 — Pipeline interface
- `src/claim_agent/pipelines/base.py`:
  - Abstract class `BasePipeline(ABC)`:
    - `__init__(self, cfg: DictConfig) -> None`
    - `@abstractmethod process_claim(self, claim: ClaimInfo) -> ClaimDecision`
  - This is the contract both pipelines fulfill

### Step 4.2 — Pipeline factory
- `src/claim_agent/pipelines/factory.py`:
  - `create_pipeline(cfg: DictConfig) -> BasePipeline`
  - Reads `cfg.pipeline.type` → instantiates the correct pipeline class
  - Lazy imports to avoid pulling in unused framework dependencies

### Step 4.3 — LangGraph state and tools
- `src/claim_agent/pipelines/langchain_pipeline/tools.py`:
  - Define LangChain `@tool`-decorated functions:
    - `parse_claim_tool` — validates JSON against `ClaimInfo` schema
    - `validate_claim_tool` — calls `core.validation.validate_claim`
    - `generate_policy_queries_tool` — prompts LLM (GPT-4o) to produce 3–5 targeted queries from claim details, returns `PolicyQueries`
    - `retrieve_policy_text_tool` — calls `core.retrieval.retrieve_policy_text`
    - `web_search_repair_cost_tool` — uses `duckduckgo-search` to look up market repair costs for the described damage; compares to claimed amount; flags if inflated (>40% above market estimate)
    - `generate_recommendation_tool` — prompts LLM with claim + policy text + cost data → returns `PolicyRecommendation`

### Step 4.4 — LangGraph state graph
- `src/claim_agent/pipelines/langchain_pipeline/chains.py`:
  - Define `ClaimState(TypedDict)` — tracks `claim`, `is_valid`, `validation_reason`, `policy_queries`, `policy_text`, `market_cost_estimate`, `is_inflated`, `recommendation`, `decision`
  - Build a `StateGraph` with nodes:
    - `parse_claim` — parse and validate input JSON
    - `validate_claim` — check CSV (conditional edge: invalid → `finalize_invalid`)
    - `check_policy` — generate queries + retrieve policy text
    - `generate_recommendation` — LLM recommendation
    - `price_check` — web search + comparison (conditional edge: inflated → `finalize_inflated`)
    - `finalize_decision` — assemble `ClaimDecision` (valid path)
    - `finalize_invalid` — assemble `ClaimDecision` with `covered=False`
    - `finalize_inflated` — assemble `ClaimDecision` with `covered=False`, notes about inflated cost
  - Conditional edges match the workflow diagram exactly

### Step 4.5 — Prompt templates
- `src/claim_agent/pipelines/langchain_pipeline/prompts.py`:
  - `QUERY_GENERATION_PROMPT` — system + human prompt for generating policy search queries
  - `RECOMMENDATION_PROMPT` — system + human prompt for coverage recommendation given claim + policy text + cost data

### Step 4.6 — Pipeline class
- `src/claim_agent/pipelines/langchain_pipeline/pipeline.py`:
  - `LangChainPipeline(BasePipeline)`:
    - `__init__` — initialize LLM (`ChatOpenAI`), compile the LangGraph, set up ChromaDB connection
    - `process_claim(claim: ClaimInfo) -> ClaimDecision` — invoke the compiled graph, return result
    - Log every node entry/exit with timing

---

## Phase 5: Smolagents Pipeline *(Effort: Medium)*

**Goal:** Implement the second pipeline using smolagents' autonomous agent. Same inputs/outputs, different orchestration style.

### Step 5.1 — Smolagents tools
- `src/claim_agent/pipelines/smolagents_pipeline/tools.py`:
  - `@tool` decorated functions wrapping the same core logic:
    - `parse_and_validate_claim` — parse JSON + CSV validation
    - `generate_policy_queries` — LLM-based query generation
    - `retrieve_policy_text` — ChromaDB semantic search
    - `estimate_repair_cost` — DuckDuckGo search
    - `generate_recommendation` — LLM-based recommendation
  - Also include `WebSearchTool` from smolagents

### Step 5.2 — Prompt templates
- `src/claim_agent/pipelines/smolagents_pipeline/prompts.py`:
  - Define `PromptTemplates` object with system prompt, planning prompt, managed agent prompt, final answer prompt
  - System prompt instructs the agent on the strict sequential workflow (parse → validate → query → retrieve → recommend → price check → decide)

### Step 5.3 — Pipeline class
- `src/claim_agent/pipelines/smolagents_pipeline/pipeline.py`:
  - `SmolAgentsPipeline(BasePipeline)`:
    - `__init__` — set up `OpenAIServerModel`, register tools, configure `ToolCallingAgent` with custom prompts
    - `process_claim(claim: ClaimInfo) -> ClaimDecision` — invoke the agent, parse its output into `ClaimDecision`
    - Extra guardrails: validate the agent's final output against the Pydantic schema; retry once if malformed

---

## Phase 6: FastAPI Backend *(Effort: Medium)*

**Goal:** Expose the pipeline as a REST API with proper error handling, CORS, and logging middleware.

### Step 6.1 — App factory
- `src/claim_agent/api/app.py`:
  - `create_app(cfg: DictConfig) -> FastAPI`
  - Initialize logging, create pipeline via factory, mount routes, configure CORS
  - Store pipeline instance in `app.state`
  - Lifespan context manager for startup (ingest PDF if needed) and shutdown

### Step 6.2 — API routes
- `src/claim_agent/api/routes/claims.py`:
  - `POST /api/v1/claims/process` — accept `ClaimInfo` JSON body, call `pipeline.process_claim()`, return `ClaimDecision`
  - `GET /api/v1/health` — return `{"status": "healthy", "pipeline": "<type>"}`
  - `GET /api/v1/pipelines` — return list of available pipeline types
  - Request/response models: reuse the Pydantic schemas
  - Error handling: return 422 for validation errors, 500 for pipeline errors with descriptive messages

### Step 6.3 — Middleware
- `src/claim_agent/api/middleware.py`:
  - Request logging middleware: log method, path, status code, duration
  - Exception handler middleware: catch unhandled exceptions, log traceback, return structured error response

### Step 6.4 — Server entry point
- `src/claim_agent/main.py`:
  - Hydra `@hydra.main` entry point
  - Calls `create_app(cfg)` and runs `uvicorn.run()`

---

## Phase 7: Streamlit Frontend *(Effort: Medium–Large)*

**Goal:** Build a polished, portfolio-worthy UI that communicates exclusively via REST API calls.

### Step 7.1 — API client
- `frontend/api_client.py`:
  - `ClaimAPIClient` class wrapping `requests`:
    - `process_claim(claim_data: dict) -> dict`
    - `health_check() -> dict`
  - Configurable base URL (from environment variable or Streamlit secrets)
  - Timeout handling, retry logic, error wrapping

### Step 7.2 — Custom styles
- `frontend/styles.py`:
  - CSS injection for professional look: custom color palette (blues/greens for approved, reds for denied), card shadows, typography, spacing
  - Consistent branded header with project title + logo area

### Step 7.3 — UI components
- `frontend/components/claim_form.py`:
  - Two input modes: (1) structured form with labeled fields for each `ClaimInfo` field, (2) raw JSON editor/file upload
  - Input validation before submission
  - Example claim data pre-populated for demo purposes
- `frontend/components/result_card.py`:
  - Dashboard-style card showing: coverage status (green checkmark / red X with background color), deductible amount, recommended payout, explanatory notes
  - Animated or color-coded status indicator
- `frontend/components/trace_viewer.py`:
  - Expandable section showing the agent's reasoning trace
  - Step-by-step display: which tool was called, inputs/outputs, retrieved policy text, LLM reasoning
  - Collapsible sections per pipeline step

### Step 7.4 — Main app
- `frontend/app.py`:
  - Page config: wide layout, custom title, favicon
  - Sidebar: API connection status, pipeline info, sample claims dropdown
  - Main area: claim form → "Process Claim" button → spinner during processing → result card + trace viewer
  - Error handling with user-friendly toast messages
  - Optional: claim history (session state) to compare multiple results

---

## Phase 8: Docker & Deployment *(Effort: Medium)*

**Goal:** Containerize both services for deployment on the target Linux server.

### Step 8.1 — Backend Dockerfile
- `Dockerfile`:
  - Multi-stage build: builder stage installs Poetry + dependencies, runtime stage copies only what's needed
  - Base image: `python:3.12-slim`
  - Install only production dependencies (exclude dev group)
  - Copy `src/`, `conf/`, `data/` (CSV + PDF, not chroma_db)
  - Expose port 8000
  - Entrypoint: `python -m claim_agent.main`
  - Health check: `curl http://localhost:8000/api/v1/health`

### Step 8.2 — Frontend Dockerfile
- `frontend/Dockerfile`:
  - `python:3.12-slim` base
  - Install `streamlit`, `requests`
  - Copy `frontend/`
  - Expose port 8501
  - Entrypoint: `streamlit run app.py --server.port=8501 --server.address=0.0.0.0`

### Step 8.3 — Docker Compose
- `docker-compose.yml`:
  - Services: `backend` (port 8000), `frontend` (port 8501)
  - `.env` file for `OPENAI_API_KEY`
  - Shared network so frontend can reach `http://backend:8000`
  - Volume for `data/chroma_db/` persistence
  - Health checks on both services
  - `depends_on` frontend → backend (with health check condition)

---

## Phase 9: Testing *(Effort: Medium)*

**Goal:** Unit and integration tests covering the critical paths.

### Step 9.1 — Fixtures
- `tests/conftest.py`:
  - Sample `ClaimInfo` fixtures (valid claim, invalid policy, expired policy, outstanding dues, inflated cost)
  - Mock CSV data fixture
  - Hydra config fixture with test overrides

### Step 9.2 — Unit tests
- `tests/test_schemas.py` — Pydantic model validation (valid/invalid inputs, edge cases)
- `tests/test_validation.py` — All 4 validation paths: policy not found, dues remaining, expired coverage, valid policy
- `tests/test_retrieval.py` — ChromaDB query with a small test collection (mock or in-memory)

### Step 9.3 — Integration tests
- `tests/test_langchain_pipeline.py` — End-to-end graph execution with mocked LLM responses (patch `ChatOpenAI` to return deterministic outputs)
- `tests/test_smolagents_pipeline.py` — Agent execution with mocked LLM
- `tests/test_api.py` — FastAPI TestClient hitting `/api/v1/claims/process` and `/api/v1/health` with mocked pipeline

---

## Phase 10: Documentation & Polish *(Effort: Small)*

### Step 10.1 — README
- `README.md`:
  - Project overview with architecture diagram
  - Quick start (Poetry install, set API key, `make ingest`, `make run`)
  - Screenshots of the Streamlit UI
  - Configuration guide
  - Docker deployment instructions
  - Tech stack badges

### Step 10.2 — Sample claims
- Create `data/sample_claims/` with 3–4 example JSON claim files:
  - `valid_claim.json` — passes all checks, gets approved
  - `invalid_policy.json` — policy number doesn't exist
  - `expired_policy.json` — date of loss outside coverage
  - `inflated_claim.json` — repair cost way above market rate

### Step 10.3 — Final polish
- Ensure all `__init__.py` files have clean re-exports
- Run `ruff format` and `ruff check --fix` on entire codebase
- Verify `mypy` passes with no errors
- Git tag `v1.0.0`

---

## Verification Checklist

| Check | Method |
|---|---|
| Schemas work | `make test` — `test_schemas.py` passes |
| Validation logic | `make test` — `test_validation.py` covers all 4 paths |
| PDF ingestion | `make ingest` — ChromaDB collection created with chunks |
| LangGraph pipeline | Process a sample claim JSON end-to-end, verify `ClaimDecision` output |
| Smolagents pipeline | Switch config to `pipeline: smolagents`, same claim produces valid `ClaimDecision` |
| API works | `curl -X POST http://localhost:8000/api/v1/claims/process -H "Content-Type: application/json" -d @data/sample_claims/valid_claim.json` |
| Frontend works | Open `http://localhost:8501`, submit a claim, see results card |
| Docker works | `make docker-up`, verify both containers healthy, test from browser |
| Logs visible | Backend console shows colored, structured logs with claim context |
| Pipeline switching | Change `pipeline: langchain` → `pipeline: smolagents` in config, restart, same behavior |

---

## Key Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over plain LangChain chains** | The stateful graph with conditional edges maps directly to the workflow diagram (explicit branching at VALIDATE and PRICE CHECK nodes), making the flow deterministic and debuggable |
| **LangChain/LangGraph implemented first** | More mature ecosystem, better tooling, and the explicit graph gives us a reliable baseline before the autonomous smolagents approach |
| **DuckDuckGo for web search** | No API key needed, simplifies setup and reduces external dependencies |
| **Loguru over colorlog/rich** | Simpler API, built-in colored output, structured logging, and stdlib interception in one package |
| **Multi-stage Dockerfile** | Keeps image size small by separating build-time Poetry from runtime |
| **`all-MiniLM-L6-v2` embeddings** | Fast, lightweight, good enough for policy text similarity; runs on CPU without GPU requirements |
| **Coverage CSV updated** | Extend 5 policies to 2026–2027 so demo claims with current dates pass validation; keep expired/dues policies for rejection testing |

---

## Risk Areas & Mitigations

| Risk | Mitigation |
|---|---|
| **LLM response format compliance** — LLM may not return valid JSON for `PolicyQueries` or `PolicyRecommendation` | Use LangChain's `with_structured_output()` for Pydantic parsing; add retry with re-prompt on parse failure |
| **Smolagents agent unpredictability** — autonomous agent may call tools in wrong order or loop | Explicit system prompt with strict step ordering; max iteration limit; output validation against `ClaimDecision` schema |
| **Vector search quality** — poor chunks = irrelevant policy text retrieved | Tune chunk size/overlap; log retrieved text + scores for debugging; consider overlap and paragraph-aware splitting |
| **Web search flakiness** — DuckDuckGo may rate-limit or return irrelevant results | Wrap in try/except with fallback (skip price check, note in decision); cache results; add timeout |
| **ChromaDB persistence** — collection may not persist correctly across container restarts | Docker volume mount for `data/chroma_db/`; startup check verifies collection exists |
| **Hydra + FastAPI integration** — Hydra's `@hydra.main` changes working directory | Use `hydra.utils.get_original_cwd()` for resolving relative data paths; or initialize Hydra manually via `compose` API |
