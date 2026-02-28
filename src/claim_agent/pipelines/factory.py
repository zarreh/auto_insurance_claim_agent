"""Pipeline factory — instantiate the correct pipeline from Hydra config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from omegaconf import DictConfig

    from claim_agent.pipelines.base import BasePipeline


def create_pipeline(cfg: DictConfig) -> BasePipeline:
    """Create and return the pipeline specified by ``cfg.pipeline.type``.

    Uses lazy imports so only the selected framework's dependencies are loaded.

    Parameters
    ----------
    cfg:
        The full Hydra configuration.

    Returns
    -------
    BasePipeline
        An initialized pipeline instance ready to process claims.

    Raises
    ------
    ValueError
        If the pipeline type is not recognised.
    """
    pipeline_type: str = cfg.pipeline.type
    logger.info("Creating pipeline: {type}", type=pipeline_type)

    if pipeline_type == "langchain":
        from claim_agent.pipelines.langchain_pipeline.pipeline import LangChainPipeline

        return LangChainPipeline(cfg)

    if pipeline_type == "smolagents":
        from claim_agent.pipelines.smolagents_pipeline.pipeline import SmolAgentsPipeline

        return SmolAgentsPipeline(cfg)

    raise ValueError(
        f"Unknown pipeline type '{pipeline_type}'. "
        "Expected 'langchain' or 'smolagents'."
    )
