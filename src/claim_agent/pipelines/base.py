"""Abstract base class that both pipeline implementations must fulfill."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omegaconf import DictConfig

    from claim_agent.schemas.claim import ClaimDecision, ClaimInfo


class BasePipeline(ABC):
    """Contract for interchangeable claim-processing pipelines.

    Subclasses must implement :meth:`process_claim`.  The active pipeline is
    selected at runtime via the Hydra configuration (``cfg.pipeline.type``).
    """

    def __init__(self, cfg: DictConfig) -> None:
        self.cfg = cfg

    @abstractmethod
    def process_claim(self, claim: ClaimInfo) -> ClaimDecision:
        """Run the full claim-processing workflow and return a decision.

        Parameters
        ----------
        claim:
            A validated :class:`ClaimInfo` instance.

        Returns
        -------
        ClaimDecision
            The final coverage decision.
        """
        ...
