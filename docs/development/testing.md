# Testing

Comprehensive guide to the test suite for the Claim Processing Agent.

## Overview

| Metric | Value |
|---|---|
| **Framework** | pytest 8.x |
| **Async** | pytest-asyncio (auto mode) |
| **Total Tests** | 58 |
| **Test Files** | 6 |
| **Runtime** | ~18 s |

```bash
# Quick run
make test

# Verbose with short tracebacks
poetry run pytest tests/ -v --tb=short
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── test_schemas.py                # Pydantic model validation (17 tests)
├── test_validation.py             # Business rule validation (8 tests)
├── test_retrieval.py              # ChromaDB retrieval (6 tests)
├── test_langchain_pipeline.py     # LangGraph nodes & routing (7 tests)
├── test_smolagents_pipeline.py    # Smolagents tools & parsing (8 tests)
└── test_api.py                    # FastAPI endpoints (5 tests)
```

## Fixtures

All shared fixtures live in `tests/conftest.py`:

### Claim Fixtures

Five factory functions that create `ClaimInfo` objects covering common scenarios:

| Fixture | Scenario |
|---|---|
| `valid_claim` | Happy path — all fields valid, amounts reasonable |
| `expired_claim` | `policy_end_date` in the past |
| `invalid_policy_claim` | Non-existent `policy_number` |
| `inflated_claim` | `claim_amount` far exceeds typical amounts |
| `minimal_claim` | Empty/minimal description |

### Infrastructure Fixtures

| Fixture | Scope | Purpose |
|---|---|---|
| `mock_csv_data` | function | Temporary CSV file with synthetic coverage data |
| `hydra_cfg` | function | Hydra `DictConfig` matching production structure |
| `sample_decision` | function | Pre-built `ClaimDecision` for assertion targets |
| `mock_pipeline` | function | `MagicMock` implementing `BasePipeline` interface |

## Test Modules

### `test_schemas.py` — 17 Tests

Validates all Pydantic models in `claim_agent.schemas`:

- **ClaimInfo**: Required fields, defaults, date formats, Pydantic validation errors
- **ClaimDecision**: `decision` field enum, `confidence_score` bounds, `flags` list
- **PolicyQueries**: Generated search queries structure
- **PolicyRecommendation**: `recommendation` and `reasoning` fields

```bash
poetry run pytest tests/test_schemas.py -v
```

### `test_validation.py` — 8 Tests

Tests `claim_agent.core.validation.validate_claim()`:

| Test | Validates |
|---|---|
| `test_valid_claim_passes` | Clean claim returns no findings |
| `test_expired_policy` | Past `policy_end_date` → "expired" flag |
| `test_invalid_policy_number` | Bad policy number format → "invalid" flag |
| `test_inflated_amount` | Excessive amount → "inflated" flag |
| `test_multiple_flags` | Expired + inflated → both flags |
| `test_future_claim_date` | Claim date in the future |
| `test_boundary_amount` | Amount at exact threshold |
| `test_missing_description` | Empty description handling |

```bash
poetry run pytest tests/test_validation.py -v
```

### `test_retrieval.py` — 6 Tests

Uses an **in-memory ChromaDB** instance (no external dependencies):

- Collection creation and document insertion
- Query returns relevant results
- Metadata filtering works correctly
- Empty collection edge case
- Result count respects `n_results` parameter
- Similarity scores are returned

```bash
poetry run pytest tests/test_retrieval.py -v
```

### `test_langchain_pipeline.py` — 7 Tests

Tests the LangGraph-based pipeline with **mocked LLM calls**:

- Individual node functions (`validation_node`, `retrieval_node`, `decision_node`)
- Router logic (`route_after_validation` — approve / reject / review)
- End-to-end graph execution with mocked `ChatOpenAI`
- State management through the graph

```bash
poetry run pytest tests/test_langchain_pipeline.py -v
```

### `test_smolagents_pipeline.py` — 8 Tests

Tests the Smolagents pipeline with **mocked agent execution**:

- JSON extraction from agent output
- Fuzzy/partial parsing fallback
- Tool registration
- End-to-end processing with mocked `CodeAgent`
- Error handling for malformed responses
- Decision normalization

```bash
poetry run pytest tests/test_smolagents_pipeline.py -v
```

### `test_api.py` — 5 Async Tests

Uses `httpx.AsyncClient` with `pytest-asyncio`:

| Test | Endpoint | Validates |
|---|---|---|
| `test_health` | `GET /health` | Returns `"ok"` status |
| `test_list_pipelines` | `GET /pipelines` | Returns list of available pipelines |
| `test_process_claim` | `POST /process` | Successful claim processing |
| `test_process_claim_422` | `POST /process` | Invalid input returns 422 |
| `test_process_claim_500` | `POST /process` | Pipeline error returns 500 |

```bash
poetry run pytest tests/test_api.py -v
```

## Writing New Tests

### Adding a test

1. Create a test function in the appropriate file (or a new file prefixed `test_`).
2. Use fixtures from `conftest.py` — inject by name.
3. Follow the **Arrange → Act → Assert** pattern.

```python
def test_claim_with_zero_amount(valid_claim):
    """Zero claim amount should be flagged."""
    valid_claim.claim_amount = 0.0
    findings = validate_claim(valid_claim)
    assert any("zero" in f.lower() for f in findings)
```

### Async tests

Use `@pytest.mark.asyncio` (auto mode is configured in `pyproject.toml`):

```python
@pytest.mark.asyncio
async def test_async_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
```

### Mocking external services

All LLM and external API calls are mocked in tests — no API keys required:

```python
from unittest.mock import AsyncMock, patch

@patch("claim_agent.pipelines.langchain_pipeline.pipeline.ChatOpenAI")
async def test_with_mock_llm(mock_llm, valid_claim):
    mock_llm.return_value.ainvoke = AsyncMock(return_value="approved")
    # ... test logic
```

## Configuration

```toml title="pyproject.toml"
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```
