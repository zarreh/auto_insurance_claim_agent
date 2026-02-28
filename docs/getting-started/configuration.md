# Configuration

All configuration is managed via **Hydra** with YAML files in the `conf/` directory. Settings can be overridden via command-line arguments, environment variables, or config file edits.

## Configuration Structure

```
conf/
├── config.yaml          # Main config with defaults
├── pipeline/
│   ├── langchain.yaml   # LangChain/LangGraph settings
│   └── smolagents.yaml  # Smolagents agent settings
├── llm/
│   └── openai.yaml      # LLM model settings
├── vectordb/
│   └── chroma.yaml      # Vector store settings
├── logging/
│   └── default.yaml     # Logging settings
└── server/
    └── default.yaml     # API server settings
```

## Main Config

```yaml title="conf/config.yaml"
defaults:
  - pipeline: langchain      # or 'smolagents'
  - llm: openai
  - vectordb: chroma
  - logging: default
  - server: default

data:
  coverage_csv: data/coverage_data.csv
  policy_pdf: data/policy.pdf
  chroma_persist_dir: data/chroma_db
```

## Pipeline Configuration

=== "LangChain/LangGraph"

    ```yaml title="conf/pipeline/langchain.yaml"
    type: langchain

    graph:
      max_iterations: 10
      recursion_limit: 25

    price_check:
      inflation_threshold: 0.40  # flag if >40% above market
    ```

=== "Smolagents"

    ```yaml title="conf/pipeline/smolagents.yaml"
    type: smolagents

    agent:
      max_steps: 10
      verbosity_level: 1

    price_check:
      inflation_threshold: 0.40
    ```

## LLM Settings

```yaml title="conf/llm/openai.yaml"
model: gpt-4o-mini
temperature: 0.1
max_tokens: 4096
api_key: ${oc.env:OPENAI_API_KEY}   # reads from environment
```

!!! warning "API Key Security"
    Never hardcode API keys in config files. Use the `${oc.env:OPENAI_API_KEY}` interpolation to read from environment variables. Set the key in your `.env` file (which is gitignored).

## Vector Store Settings

```yaml title="conf/vectordb/chroma.yaml"
collection_name: policy_chunks
embedding_model: all-MiniLM-L6-v2
n_results: 5
chunk_size: 500
chunk_overlap: 50
```

| Setting | Description | Default |
|---|---|---|
| `collection_name` | ChromaDB collection name | `policy_chunks` |
| `embedding_model` | HuggingFace model for embeddings | `all-MiniLM-L6-v2` |
| `n_results` | Max results per query | `5` |
| `chunk_size` | Characters per text chunk | `500` |
| `chunk_overlap` | Overlapping characters between chunks | `50` |

## Logging Settings

```yaml title="conf/logging/default.yaml"
level: INFO
colored: true
format: structured   # "structured" for JSON, "pretty" for colored console
```

## Server Settings

```yaml title="conf/server/default.yaml"
host: 0.0.0.0
port: 8000
debug: false
cors_origins:
  - "http://localhost:8501"
```

## Command-Line Overrides

Hydra supports runtime overrides via CLI arguments:

```bash
# Switch pipeline
poetry run python -m claim_agent.main pipeline=smolagents

# Change LLM model
poetry run python -m claim_agent.main llm.model=gpt-4o

# Enable debug logging
poetry run python -m claim_agent.main logging.level=DEBUG

# Multiple overrides
poetry run python -m claim_agent.main \
  pipeline=smolagents \
  llm.temperature=0.3 \
  server.port=9000
```

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | **Yes** |
| `API_BASE_URL` | Backend URL for the frontend (Docker) | No (default: `http://localhost:8000`) |
