# Contributing

Development guide for the Claim Processing Agent.

## Development Setup

```bash
# Clone and install (including dev dependencies)
git clone https://github.com/zarreh/auto_insurance_claim_agent.git
cd claim_process_agent
poetry install

# Set up environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

## Code Quality

### Formatting

```bash
make format
# Runs: ruff format + ruff check --fix
```

### Linting

```bash
make lint
# Runs: ruff check + mypy
```

### Ruff Configuration

```toml title="pyproject.toml"
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP"]
```

Rules enabled:

| Code | Category |
|---|---|
| `E` | pycodestyle errors |
| `F` | pyflakes |
| `I` | isort (import sorting) |
| `W` | pycodestyle warnings |
| `UP` | pyupgrade (Python 3.12+ syntax) |

### Type Checking

```bash
poetry run mypy src/
```

## Testing

```bash
# Run all tests
make test

# Run with coverage
poetry run pytest tests/ -v --tb=short

# Run a specific test file
poetry run pytest tests/test_schemas.py -v

# Run a specific test class or method
poetry run pytest tests/test_validation.py::TestValidation::test_valid_claim_passes -v
```

See the [Testing](testing.md) page for details on test structure and fixtures.

## Project Layout

```
src/claim_agent/          # Main package
├── schemas/              # Pydantic models (shared)
├── core/                 # Business logic (framework-agnostic)
├── pipelines/            # LangChain + Smolagents implementations
│   ├── base.py           # Abstract interface
│   ├── factory.py        # Pipeline factory
│   ├── langchain_pipeline/
│   └── smolagents_pipeline/
├── api/                  # FastAPI app, routes, middleware
└── logging/              # Loguru configuration

frontend/                 # Streamlit UI (separate)
tests/                    # pytest test suite
conf/                     # Hydra YAML configs
docs/                     # MkDocs documentation
```

## Key Conventions

### Imports

- Use `from __future__ import annotations` in every module
- Use `TYPE_CHECKING` guard for type-only imports
- Let ruff handle import sorting (`isort` rules)

### Type Hints

- All public functions must have complete type annotations
- Use modern syntax: `list[str]` not `List[str]`, `str | None` not `Optional[str]`

### Docstrings

- Use Google/NumPy-style docstrings for all public functions
- Include `Parameters`, `Returns`, and `Raises` sections

### Logging

- Use `loguru.logger` (not `logging`)
- Use Loguru's lazy formatting: `logger.info("msg {key}", key=value)`
- Log levels: `DEBUG` for trace, `INFO` for flow, `WARNING` for recoverable, `ERROR` for failures

### Error Handling

- No silent exception swallowing
- Always log errors with context (claim number, pipeline type, etc.)
- Use descriptive error messages

## Documentation

### Serving Locally

```bash
make docs-serve
# Opens at http://localhost:8000
```

### Building

```bash
make docs-build
```

Documentation is automatically deployed to GitHub Pages via the CI workflow on pushes to `master`.
