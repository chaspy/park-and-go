"""LLM judge abstraction layer.

Provides an abstract interface for LLM-based parking judgment.
Default implementation is a no-op that returns None.
Future implementations can use OpenAI, Gemini, Anthropic, etc.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas.analyze import EvidenceItem, Verdict, VehicleFit
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMJudgmentRequest:
    """Facts extracted from sources, ready for LLM consumption."""
    place_name: str = ""
    address: str = ""
    places_parking_info: str | None = None
    site_mentions: list[str] | None = None
    nearby_parking_count: int = 0
    vehicle_name: str = ""
    vehicle_dimensions: str = ""


@dataclass
class LLMJudgmentResponse:
    verdict: Verdict | None = None
    confidence: float | None = None
    vehicle_fit: VehicleFit | None = None
    summary: str | None = None
    evidence: list[EvidenceItem] | None = None


class LLMJudge(ABC):
    """Abstract base class for LLM-based judgment."""

    @abstractmethod
    async def judge(self, request: LLMJudgmentRequest) -> LLMJudgmentResponse:
        """Run LLM judgment on extracted facts."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this LLM provider is configured and available."""
        ...


class NoOpLLMJudge(LLMJudge):
    """No-op implementation that always returns empty results."""

    async def judge(self, request: LLMJudgmentRequest) -> LLMJudgmentResponse:
        return LLMJudgmentResponse()

    def is_available(self) -> bool:
        return False


def get_llm_judge() -> LLMJudge:
    """Factory function that returns the appropriate LLM judge based on config."""
    if not settings.enable_llm:
        return NoOpLLMJudge()

    provider = settings.llm_provider.lower()

    if provider == "openai":
        logger.info("LLM provider: OpenAI (not yet implemented, using no-op)")
        return NoOpLLMJudge()
    elif provider == "anthropic":
        logger.info("LLM provider: Anthropic (not yet implemented, using no-op)")
        return NoOpLLMJudge()
    elif provider == "gemini":
        logger.info("LLM provider: Gemini (not yet implemented, using no-op)")
        return NoOpLLMJudge()
    else:
        logger.warning("Unknown LLM provider '%s', using no-op", provider)
        return NoOpLLMJudge()
