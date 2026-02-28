# REST API

The backend exposes a FastAPI REST API on port **8000** with the base path `/api/v1`.

## Base URL

| Environment | URL |
|---|---|
| Local | `http://localhost:8000` |
| Docker | `http://backend:8000` (inter-container) |

## Endpoints

### Process Claim

Process a single insurance claim through the configured pipeline.

```
POST /api/v1/claims/process
```

**Request Body** — `ClaimInfo` (JSON):

```json
{
  "claim_number": "CLM-001",
  "policy_number": "PN-2",
  "claimant_name": "Jane Doe",
  "date_of_loss": "2026-02-15",
  "loss_description": "Rear-end collision at intersection",
  "estimated_repair_cost": 3500.00,
  "vehicle_details": "2022 Toyota Camry"
}
```

**Response** — `ClaimDecision` (JSON):

=== "200 — Approved"

    ```json
    {
      "claim_number": "CLM-001",
      "covered": true,
      "deductible": 500.0,
      "recommended_payout": 3000.0,
      "notes": "Claim covered under collision coverage."
    }
    ```

=== "200 — Rejected"

    ```json
    {
      "claim_number": "CLM-002",
      "covered": false,
      "deductible": 0.0,
      "recommended_payout": 0.0,
      "notes": "Claim rejected — Policy PN-99 not found in records"
    }
    ```

=== "422 — Validation Error"

    ```json
    {
      "detail": [
        {
          "type": "missing",
          "loc": ["body", "policy_number"],
          "msg": "Field required"
        }
      ]
    }
    ```

=== "500 — Pipeline Error"

    ```json
    {
      "detail": "Pipeline error: Connection refused"
    }
    ```

**cURL Example**:

```bash
curl -X POST http://localhost:8000/api/v1/claims/process \
  -H "Content-Type: application/json" \
  -d @data/sample_claims/valid_claim.json
```

---

### Health Check

Lightweight health check for monitoring and Docker health checks.

```
GET /api/v1/health
```

**Response**:

```json
{
  "status": "healthy",
  "pipeline": "langchain"
}
```

---

### List Pipelines

Returns the list of available pipeline implementations.

```
GET /api/v1/pipelines
```

**Response**:

```json
{
  "pipelines": ["langchain", "smolagents"]
}
```

## Middleware

The API applies two middleware layers (outermost first):

### Request Logging

Logs every request with method, path, status code, and duration:

```
INFO | POST /api/v1/claims/process → 200 (3421ms)
```

### Exception Handler

Catches unhandled exceptions and returns a structured 500 JSON response instead of a raw 500 error page.

## CORS

Cross-Origin Resource Sharing is configured to allow the Streamlit frontend:

```yaml
cors_origins:
  - "http://localhost:8501"
```

## Authentication

!!! note
    The current version does not implement authentication. For production use, consider adding API key validation via a `Depends` middleware or OAuth2.

## Interactive Docs

When running locally, visit:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
