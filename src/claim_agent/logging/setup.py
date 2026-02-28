"""Logging configuration using loguru — colored console or structured JSON."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from omegaconf import DictConfig


# ---------------------------------------------------------------------------
# Intercept stdlib logging → loguru
# ---------------------------------------------------------------------------

class _InterceptHandler(logging.Handler):
    """Route standard-library log records through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Find the loguru level that matches the stdlib level.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        # Find the caller frame so loguru reports the correct source location.
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# ---------------------------------------------------------------------------
# Pretty (dev) format
# ---------------------------------------------------------------------------

_PRETTY_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
    "{extra}"
)

# ---------------------------------------------------------------------------
# Structured JSON (prod) format — loguru serializes automatically
# ---------------------------------------------------------------------------


def setup_logging(cfg: DictConfig) -> None:
    """Configure loguru based on the Hydra logging config section.

    Parameters
    ----------
    cfg:
        The ``logging`` sub-config with keys ``level``, ``colored``, ``format``.
        ``format`` should be ``"pretty"`` (colored console) or ``"structured"``
        (JSON lines).
    """
    # Remove any default loguru sinks
    logger.remove()

    level: str = getattr(cfg, "level", "INFO").upper()
    use_json: bool = getattr(cfg, "format", "pretty") == "structured"
    colorize: bool = getattr(cfg, "colored", True)

    if use_json:
        # Structured JSON for production / log aggregation
        logger.add(
            sys.stderr,
            level=level,
            serialize=True,
            colorize=False,
        )
    else:
        # Pretty colored output for development
        logger.add(
            sys.stderr,
            level=level,
            format=_PRETTY_FORMAT,
            colorize=colorize,
        )

    # Intercept stdlib logging so libraries using `logging` also go through loguru
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.info("Logging configured", level=level, json_mode=use_json)
