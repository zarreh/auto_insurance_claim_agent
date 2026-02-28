# 🛡️ Intelligent Insurance Claim Processing Agent

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Smolagents](https://img.shields.io/badge/Smolagents-1.17-green.svg)](https://huggingface.co/docs/smolagents/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **production-grade Agentic RAG (Retrieval-Augmented Generation)** system that automates the evaluation of auto insurance claims. The system ingests claims as JSON, validates against policy records, retrieves relevant policy language via semantic search, estimates repair costs, and produces structured coverage decisions — all orchestrated by an AI agent.

## ✨ Key Features

- **Dual Agentic Pipelines** — LangChain/LangGraph (stateful graph) and Smolagents (autonomous agent), interchangeable via config
- **Agentic RAG** — Semantic retrieval from policy documents using ChromaDB + sentence-transformers
- **Automated Validation** — Policy existence, premium status, coverage dates, and cost inflation checks
- **REST API** — FastAPI backend with structured request/response schemas
- **Streamlit UI** — Polished frontend with claim form, results dashboard, and reasoning trace viewer
- **Docker Deployment** — Multi-stage builds with compose orchestration
- **Hydra Configuration** — All settings externalized; switch pipelines with a single config change

## 🏗️ Architecture

```
┌──────────────┐     REST API     ┌──────────────────────────────────────────┐
│  Streamlit   │ ──────────────▶  │  FastAPI Backend                         │
│  Frontend    │ ◀──────────────  │  ┌─────────┐  ┌────────┐  ┌──────────┐  │
│  :8501       │                  │  │ Validate │→ │ Retrieve│→ │ Decide   │  │
└──────────────┘                  │  └─────────┘  └────────┘  └──────────┘  │
                                  │       ↕             ↕            ↕       │
                                  │  CSV Records   ChromaDB     OpenAI GPT   │
                                  └──────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation)
- OpenAI API key

### Installation

```bash
git clone https://github.com/zarreh/claim_process_agent.git
cd claim_process_agent
make install

# Set your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run Locally

```bash
# Start both backend and frontend
make run

# Or start individually
make run-api       # FastAPI on :8000
make run-frontend  # Streamlit on :8501
```

### Run with Docker

```bash
make docker-build
make docker-up
# Visit http://localhost:8501
```

### Process a Claim via API

```bash
curl -X POST http://localhost:8000/api/v1/claims/process \
  -H "Content-Type: application/json" \
  -d @data/sample_claims/valid_claim.json
```

## 🔧 Configuration

Pipeline selection via Hydra config — no code changes required:

```bash
# Use LangGraph pipeline (default)
python -m claim_agent.main pipeline=langchain

# Use Smolagents pipeline
python -m claim_agent.main pipeline=smolagents
```

See the [Configuration Guide](https://zarreh.github.io/claim_process_agent/getting-started/configuration/) for full details.

## 🧪 Testing

```bash
make test
# 58 tests across schemas, validation, retrieval, pipelines, and API
```

## 📖 Documentation

Full documentation is available at: **[https://zarreh.github.io/claim_process_agent/](https://zarreh.github.io/claim_process_agent/)**

Or serve locally:

```bash
make docs-serve
```

## 🗂️ Project Structure

```
├── src/claim_agent/          # Main package
│   ├── schemas/              # Pydantic models
│   ├── core/                 # Business logic (validation, ingestion, retrieval)
│   ├── pipelines/            # LangChain + Smolagents implementations
│   ├── api/                  # FastAPI app and routes
│   └── logging/              # Loguru configuration
├── frontend/                 # Streamlit UI
├── conf/                     # Hydra YAML configs
├── data/                     # Coverage CSV, sample claims
├── tests/                    # pytest test suite (58 tests)
├── docs/                     # MkDocs documentation
└── docker-compose.yml        # Docker orchestration
```

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.12 |
| LLM | OpenAI GPT-4o |
| Agent Frameworks | LangChain/LangGraph, Smolagents |
| Vector Store | ChromaDB |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Configuration | Hydra |
| Logging | Loguru |
| Data Validation | Pydantic v2 |
| Package Manager | Poetry |
| Containerization | Docker + Compose |
| Linting | Ruff |
| Testing | pytest + pytest-asyncio |

## 📄 License

This project is part of the Johns Hopkins University Agentic AI course.
