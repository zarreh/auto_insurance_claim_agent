"""Claim Agent server entry point.

Uses Hydra's Compose API to load configuration and then starts the
FastAPI application via uvicorn.

Usage::

    poetry run python -m claim_agent.main          # default config
    poetry run python -m claim_agent.main pipeline=smolagents  # override
"""

from __future__ import annotations

import os
from pathlib import Path

import hydra
import uvicorn
from dotenv import load_dotenv
from loguru import logger
from omegaconf import DictConfig, open_dict

from claim_agent.api.app import create_app

# Load .env BEFORE Hydra resolves ${oc.env:...} references
load_dotenv()


def _resolve_data_paths(cfg: DictConfig) -> None:
    """Convert relative data paths to absolute using the original working dir.

    Hydra changes the CWD to ``outputs/<date>/<time>/``.  All relative paths
    in ``cfg.data`` must be anchored to the project root so downstream code
    (ingestion, validation, retrieval) finds the files regardless of CWD.
    """
    original_cwd = Path(hydra.utils.get_original_cwd())

    with open_dict(cfg):
        for key in ("coverage_csv", "policy_pdf", "chroma_persist_dir"):
            raw = cfg.data[key]
            resolved = Path(raw)
            if not resolved.is_absolute():
                cfg.data[key] = str(original_cwd / resolved)


@hydra.main(version_base=None, config_path="../../conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Bootstrap the application from Hydra config and run uvicorn."""
    # Fix Hydra CWD issue: make data paths absolute
    _resolve_data_paths(cfg)

    # Change back to project root so uvicorn / other libs behave normally
    os.chdir(hydra.utils.get_original_cwd())

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
