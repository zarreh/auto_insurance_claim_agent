# Quick Start

Get the Claim Processing Agent running locally in under 5 minutes.

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.12+ |
| Poetry | 1.8+ |
| OpenAI API Key | Required |

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/zarreh/auto_insurance_claim_agent.git
cd claim_process_agent
```

### 2. Install Dependencies

```bash
make install
# or manually:
poetry install
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```dotenv
OPENAI_API_KEY=sk-your-key-here
```

### 4. Ingest Policy PDF

Before processing claims, you need to ingest the insurance policy document into the vector store:

```bash
make ingest
```

This extracts text from `data/policy.pdf`, chunks it, computes embeddings with `all-MiniLM-L6-v2`, and stores the vectors in ChromaDB at `data/chroma_db/`.

!!! info "Idempotent Operation"
    Re-running `make ingest` is safe — it skips ingestion if the collection already has documents.

### 5. Start the Application

=== "Both Services"

    ```bash
    make run
    ```
    This starts the FastAPI backend on port **8000** and the Streamlit frontend on port **8501**.

=== "Backend Only"

    ```bash
    make run-api
    ```

=== "Frontend Only"

    ```bash
    make run-frontend
    ```

### 6. Open the UI

Navigate to [http://localhost:8501](http://localhost:8501) in your browser.

## Processing Your First Claim

### Via the Web UI

1. Open [http://localhost:8501](http://localhost:8501)
2. Select a sample claim from the sidebar dropdown, or fill in the form manually
3. Click **Process Claim**
4. View the decision card with coverage status, deductible, and payout
5. Expand the **Processing Trace** to see the agent's step-by-step reasoning

### Via the API

```bash
curl -X POST http://localhost:8000/api/v1/claims/process \
  -H "Content-Type: application/json" \
  -d '{
    "claim_number": "CLM-001",
    "policy_number": "PN-2",
    "claimant_name": "Jane Doe",
    "date_of_loss": "2026-02-15",
    "loss_description": "Rear-end collision at intersection, bumper and taillight damage",
    "estimated_repair_cost": 3500.00,
    "vehicle_details": "2022 Toyota Camry"
  }'
```

### Via Sample JSON Files

```bash
curl -X POST http://localhost:8000/api/v1/claims/process \
  -H "Content-Type: application/json" \
  -d @data/sample_claims/valid_claim.json
```

## Health Check

```bash
curl http://localhost:8000/api/v1/health
# {"status": "healthy", "pipeline": "langchain"}
```

## Switching Pipelines

To switch from the LangChain pipeline to the Smolagents pipeline, edit `conf/config.yaml`:

```yaml
defaults:
  - pipeline: smolagents   # ← change from 'langchain'
  - llm: openai
  - vectordb: chroma
  - logging: default
  - server: default
```

Restart the server and the autonomous agent pipeline will handle claims instead of the deterministic graph.

## Makefile Reference

| Command | Description |
|---|---|
| `make install` | Install all dependencies via Poetry |
| `make run-api` | Start FastAPI backend (port 8000) |
| `make run-frontend` | Start Streamlit frontend (port 8501) |
| `make run` | Start both services |
| `make ingest` | Ingest policy PDF into ChromaDB |
| `make test` | Run the full test suite |
| `make lint` | Run ruff + mypy checks |
| `make format` | Auto-format code with ruff |
| `make docker-build` | Build Docker images |
| `make docker-up` | Start containers (detached) |
| `make docker-down` | Stop containers |
| `make clean` | Remove caches and build artifacts |
| `make docs-serve` | Serve documentation locally |
