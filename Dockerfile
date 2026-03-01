# ── Stage 1: Builder ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry==1.8.5

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock* ./

# Install production dependencies only (no dev group, no project itself yet)
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-interaction --no-ansi --without dev --no-root

# ── Stage 2: Runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# curl is needed for the health check
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy project metadata (needed for pip install -e .)
COPY pyproject.toml README.md ./

# Copy application code
COPY src/ src/
COPY conf/ conf/
COPY data/coverage_data.csv data/coverage_data.csv

# Copy policy PDF if it exists (may not be present during build)
COPY data/policy.pd[f] data/

# Install the project package (editable-style) into the venv
RUN pip install --no-deps -e .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["python", "-m", "claim_agent.main"]
