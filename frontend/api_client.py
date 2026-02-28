"""Thin HTTP client that talks to the Claim Processing Agent REST API."""

from __future__ import annotations

import os
from typing import Any

import requests


class ClaimAPIClient:
    """Wrapper around ``requests`` for the claim-processing backend.

    Parameters
    ----------
    base_url:
        Root URL of the FastAPI backend (e.g. ``http://localhost:8000``).
        Falls back to the ``API_BASE_URL`` env-var, then ``http://localhost:8000``.
    timeout:
        Request timeout in seconds.
    max_retries:
        Number of retry attempts on connection / 5xx errors.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = 120,
        max_retries: int = 2,
    ) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    # -----------------------------------------------------------------
    # Public helpers
    # -----------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        """``GET /api/v1/health`` — lightweight liveness probe."""
        return self._get("/api/v1/health")

    def list_pipelines(self) -> dict[str, Any]:
        """``GET /api/v1/pipelines`` — available pipeline types."""
        return self._get("/api/v1/pipelines")

    def process_claim(self, claim_data: dict[str, Any]) -> dict[str, Any]:
        """``POST /api/v1/claims/process`` — submit a claim for processing."""
        return self._post("/api/v1/claims/process", json=claim_data)

    # -----------------------------------------------------------------
    # Internal request helpers
    # -----------------------------------------------------------------

    def _get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path)

    def _post(self, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, json=json)

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs,
                )
                resp.raise_for_status()
                return resp.json()
            except requests.ConnectionError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    continue
            except requests.HTTPError as exc:
                # Don't retry client errors (4xx)
                if exc.response is not None and exc.response.status_code < 500:
                    error_body = _safe_json(exc.response)
                    raise APIError(
                        f"HTTP {exc.response.status_code}: "
                        f"{error_body.get('detail', exc.response.text)}",
                        status_code=exc.response.status_code,
                    ) from exc
                last_exc = exc
                if attempt < self.max_retries:
                    continue
            except requests.Timeout as exc:
                last_exc = exc

        raise APIError(
            f"Request to {url} failed after {self.max_retries} attempts: {last_exc}",
        )


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class APIError(Exception):
    """Raised when the backend returns an error or is unreachable."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_json(resp: requests.Response) -> dict[str, Any]:
    """Try to parse a response body as JSON, returning ``{}`` on failure."""
    try:
        return resp.json()
    except Exception:
        return {}
