"""LLM-based parking information extraction.

Uses LLM to understand natural language descriptions of parking availability
from official site text. Only called when rule-based extraction finds nothing.

The LLM receives pre-extracted text (not raw HTML) and returns structured JSON.
Its output becomes evidence fed into the rule engine — the LLM does NOT make
the final verdict.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from app.core.config import settings
from app.sources.official_site import ParkingMention

logger = logging.getLogger(__name__)


@dataclass
class LLMExtractionRequest:
    """Pre-processed facts for LLM consumption."""
    place_name: str
    site_text: str  # extracted text from official site, truncated


@dataclass
class LLMExtractionResult:
    """Structured output from LLM."""
    has_parking: bool | None = None  # True/False/None(unknown)
    parking_type: str | None = None  # "dedicated", "partner", "coin_parking", None
    parking_detail: str | None = None  # free-text summary from LLM
    capacity: int | None = None
    height_limit_m: float | None = None
    width_limit_m: float | None = None
    is_tight: bool | None = None
    raw_response: str = ""

    def to_mentions(self) -> list[ParkingMention]:
        """Convert LLM output to ParkingMention list for rule engine."""
        mentions: list[ParkingMention] = []

        if self.has_parking is True:
            kind = "positive"
            if self.parking_type == "partner":
                kind = "partner"
            mentions.append(ParkingMention(
                text=self.parking_detail or "LLM: 駐車場あり",
                context=self.parking_detail or "",
                kind=kind,
            ))
        elif self.has_parking is False:
            mentions.append(ParkingMention(
                text=self.parking_detail or "LLM: 駐車場なし",
                context=self.parking_detail or "",
                kind="negative",
            ))

        if self.capacity is not None:
            mentions.append(ParkingMention(
                text=f"LLM: {self.capacity}台",
                context=self.parking_detail or "",
                kind="capacity",
                value=str(self.capacity),
            ))

        if self.height_limit_m is not None:
            mentions.append(ParkingMention(
                text=f"LLM: 車高制限 {self.height_limit_m}m",
                context=self.parking_detail or "",
                kind="height_limit",
                value=str(self.height_limit_m),
            ))

        if self.width_limit_m is not None:
            mentions.append(ParkingMention(
                text=f"LLM: 車幅制限 {self.width_limit_m}m",
                context=self.parking_detail or "",
                kind="width_limit",
                value=str(self.width_limit_m),
            ))

        if self.is_tight is True:
            mentions.append(ParkingMention(
                text=self.parking_detail or "LLM: 狭い駐車場",
                context=self.parking_detail or "",
                kind="tight",
            ))

        return mentions


SYSTEM_PROMPT = """\
あなたは店舗の駐車場情報を抽出するアシスタントです。
与えられた公式サイトのテキストから、駐車場に関する情報を読み取ってください。

以下のJSON形式で回答してください。情報がない場合はnullにしてください。
推測や創作はしないでください。テキストに書かれていることだけを元にしてください。

{
  "has_parking": true/false/null,
  "parking_type": "dedicated" | "partner" | "coin_parking" | null,
  "parking_detail": "駐車場に関する要約（1-2文）",
  "capacity": 台数(数値) or null,
  "height_limit_m": 車高制限(メートル) or null,
  "width_limit_m": 車幅制限(メートル) or null,
  "is_tight": true/false/null
}

parking_type:
- "dedicated": 店専用・施設併設の駐車場
- "partner": 提携駐車場（割引券やサービス券あり）
- "coin_parking": 近隣コインパーキングを案内している
- null: 情報なし"""


class LLMExtractor(ABC):
    """Abstract base for LLM-based parking extraction."""

    @abstractmethod
    async def extract(self, request: LLMExtractionRequest) -> LLMExtractionResult | None:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class NoOpLLMExtractor(LLMExtractor):
    async def extract(self, request: LLMExtractionRequest) -> LLMExtractionResult | None:
        return None

    def is_available(self) -> bool:
        return False


class AnthropicExtractor(LLMExtractor):
    """Claude-based parking information extractor."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def extract(self, request: LLMExtractionRequest) -> LLMExtractionResult | None:
        # Truncate site text to keep token usage low
        site_text = request.site_text[:3000]

        user_message = f"店名: {request.place_name}\n\n公式サイトのテキスト:\n{site_text}"

        body = {
            "model": self.model,
            "max_tokens": 300,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_message}],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("Anthropic API call failed: %s", e)
                return None

        data = resp.json()
        content = data.get("content", [])
        if not content:
            return None

        raw_text = content[0].get("text", "")
        return self._parse_response(raw_text)

    def _parse_response(self, raw_text: str) -> LLMExtractionResult | None:
        # Extract JSON from response (may have markdown fences)
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON response: %s", raw_text[:200])
            return None

        return LLMExtractionResult(
            has_parking=parsed.get("has_parking"),
            parking_type=parsed.get("parking_type"),
            parking_detail=parsed.get("parking_detail"),
            capacity=parsed.get("capacity"),
            height_limit_m=parsed.get("height_limit_m"),
            width_limit_m=parsed.get("width_limit_m"),
            is_tight=parsed.get("is_tight"),
            raw_response=raw_text,
        )


class OpenAIExtractor(LLMExtractor):
    """OpenAI-based parking information extractor."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def extract(self, request: LLMExtractionRequest) -> LLMExtractionResult | None:
        site_text = request.site_text[:3000]
        user_message = f"店名: {request.place_name}\n\n公式サイトのテキスト:\n{site_text}"

        body = {
            "model": self.model,
            "max_tokens": 300,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.warning("OpenAI API call failed: %s", e)
                return None

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return None

        raw_text = choices[0].get("message", {}).get("content", "")
        return AnthropicExtractor._parse_response(None, raw_text)  # reuse parser


def get_llm_extractor() -> LLMExtractor:
    """Factory: return the appropriate LLM extractor based on config."""
    if not settings.enable_llm or not settings.llm_api_key:
        return NoOpLLMExtractor()

    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        model = settings.llm_model or "claude-haiku-4-5-20251001"
        logger.info("LLM extractor: Anthropic Claude (%s)", model)
        return AnthropicExtractor(api_key=settings.llm_api_key, model=model)
    elif provider == "openai":
        model = settings.llm_model or "gpt-4o-mini"
        logger.info("LLM extractor: OpenAI (%s)", model)
        return OpenAIExtractor(api_key=settings.llm_api_key, model=model)
    else:
        logger.warning("Unknown LLM provider '%s', LLM extraction disabled", provider)
        return NoOpLLMExtractor()
