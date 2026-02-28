"""Custom ASGI middleware for request logging and exception handling."""

from __future__ import annotations

import time
import traceback

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# ---------------------------------------------------------------------------
# Request logging
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status code, and duration."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.time()
        method = request.method
        path = request.url.path

        response = await call_next(request)

        elapsed_ms = (time.time() - start) * 1000
        logger.info(
            "{method} {path} → {status} ({ms:.0f}ms)",
            method=method,
            path=path,
            status=response.status_code,
            ms=elapsed_ms,
        )
        return response


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return a structured 500 response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "Unhandled exception on {method} {path}: {err}\n{tb}",
                method=request.method,
                path=request.url.path,
                err=exc,
                tb=traceback.format_exc(),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error": str(exc),
                },
            )
