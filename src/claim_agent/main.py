"""Claim Agent server entry point.

Uses Hydra's Compose API to load configuration and then starts the
FastAPI application via uvicorn.

Usage::

    poetry run python -m claim_agent.main          # default config
    poetry run python -m claim_agent.main pipeline=smolagents  # override
"""

from __future__ import annotations

import hydra
import uvicorn
from loguru import logger
from omegaconf import DictConfig

from claim_agent.api.app import create_app


@hydra.main(version_base=None, config_path="../../conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Bootstrap the application from Hydra config and run uvicorn."""
    app = create_app(cfg)

    host: str = cfg.server.host
    port: int = cfg.server.port
    debug: bool = cfg.server.debug

    logger.info(
        "Starting server on {host}:{port} (debug={debug})",
        host=host,
        port=port,
        debug=debug,
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug" if debug else "info",
    )


if __name__ == "__main__":
    main()
