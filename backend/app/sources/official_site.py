"""Official website scraping for parking-related information."""

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TIMEOUT = 10.0
MAX_BODY_SIZE = 500_000  # 500KB per page
MAX_PAGES = 5

# Subpaths likely to contain access/parking info
ACCESS_PATHS = [
    "/access",
    "/access/",
    "/shop",
    "/store",
    "/info",
    "/faq",
    "/about",
    "/guide",
    "/map",
]

# --- Keyword patterns ---

POSITIVE_KEYWORDS = [
    r"駐車場あり",
    r"駐車場\s*[:：]\s*あり",
    r"専用駐車場",
    r"無料駐車場",
    r"駐車場完備",
    r"お車でお越し",
    r"駐車場を.*ご用意",
    r"free\s+parking",
    r"parking\s+(?:lot|available)",
    r"valet\s+parking",
]

PARTNER_KEYWORDS = [
    r"提携駐車場",
    r"契約駐車場",
    r"サービス券",
    r"駐車券.*サービス",
    r"駐車料金.*割引",
    r"validated\s+parking",
]

NEGATIVE_KEYWORDS = [
    r"駐車場(?:は)?(?:ございません|ありません|なし|無し)",
    r"専用駐車場(?:は)?(?:ございません|ありません|なし|無し)",
    r"お車での(?:ご来店|来店).*(?:ご遠慮|遠慮|控え)",
    r"近隣(?:の)?コインパーキング.*(?:ご利用|利用)",
    r"no\s+parking",
    r"parking\s+(?:not\s+available|unavailable)",
]

CAPACITY_PATTERN = re.compile(
    r"(?:駐車場|parking)\s*[:：]?\s*(\d+)\s*台", re.IGNORECASE
)

HEIGHT_LIMIT_PATTERN = re.compile(
    r"(?:車高|高さ)\s*(?:制限|リミット)?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:m|cm|mm|メートル|センチ)",
    re.IGNORECASE,
)

WIDTH_LIMIT_PATTERN = re.compile(
    r"(?:車幅|幅)\s*(?:制限)?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:m|cm|mm|メートル|センチ)",
    re.IGNORECASE,
)

TIGHT_KEYWORDS = [
    r"狭い",
    r"1台のみ",
    r"1台分",
    r"軽自動車.*(?:推奨|限定|のみ)",
    r"小型車.*(?:推奨|限定|のみ)",
    r"切り返し",
    r"(?:compact|small)\s+(?:cars?\s+)?only",
]


@dataclass
class ParkingMention:
    text: str
    context: str  # surrounding text
    kind: str  # positive / negative / partner / capacity / height_limit / width_limit / tight
    value: str | None = None  # extracted numeric value if any


@dataclass
class SiteScrapingResult:
    url: str
    pages_fetched: int = 0
    mentions: list[ParkingMention] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _get_context(text: str, match_start: int, match_end: int, window: int = 80) -> str:
    """Get surrounding context for a match."""
    start = max(0, match_start - window)
    end = min(len(text), match_end + window)
    return text[start:end].replace("\n", " ").strip()


def _find_mentions(text: str) -> list[ParkingMention]:
    """Find all parking-related mentions in text."""
    mentions: list[ParkingMention] = []

    for pattern in POSITIVE_KEYWORDS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            mentions.append(ParkingMention(
                text=m.group(),
                context=_get_context(text, m.start(), m.end()),
                kind="positive",
            ))

    for pattern in PARTNER_KEYWORDS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            mentions.append(ParkingMention(
                text=m.group(),
                context=_get_context(text, m.start(), m.end()),
                kind="partner",
            ))

    for pattern in NEGATIVE_KEYWORDS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            mentions.append(ParkingMention(
                text=m.group(),
                context=_get_context(text, m.start(), m.end()),
                kind="negative",
            ))

    for m in CAPACITY_PATTERN.finditer(text):
        mentions.append(ParkingMention(
            text=m.group(),
            context=_get_context(text, m.start(), m.end()),
            kind="capacity",
            value=m.group(1),
        ))

    for m in HEIGHT_LIMIT_PATTERN.finditer(text):
        mentions.append(ParkingMention(
            text=m.group(),
            context=_get_context(text, m.start(), m.end()),
            kind="height_limit",
            value=m.group(1),
        ))

    for m in WIDTH_LIMIT_PATTERN.finditer(text):
        mentions.append(ParkingMention(
            text=m.group(),
            context=_get_context(text, m.start(), m.end()),
            kind="width_limit",
            value=m.group(1),
        ))

    for pattern in TIGHT_KEYWORDS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            mentions.append(ParkingMention(
                text=m.group(),
                context=_get_context(text, m.start(), m.end()),
                kind="tight",
            ))

    return mentions


def _candidate_urls(base_url: str) -> list[str]:
    """Generate candidate URLs to check for parking info."""
    urls = [base_url]
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    for path in ACCESS_PATHS:
        candidate = urljoin(base, path)
        if candidate != base_url:
            urls.append(candidate)

    return urls


async def scrape_site(website_url: str) -> SiteScrapingResult:
    """Scrape a website for parking-related information."""
    result = SiteScrapingResult(url=website_url)

    if not website_url:
        return result

    candidate_urls = _candidate_urls(website_url)

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=3),
    ) as client:
        for url in candidate_urls:
            if result.pages_fetched >= MAX_PAGES:
                break

            try:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "parking-judge/0.1 (personal use)"},
                )
                if resp.status_code != 200:
                    continue
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue

                body = resp.text[:MAX_BODY_SIZE]
                result.pages_fetched += 1

            except httpx.HTTPError as e:
                logger.debug("Failed to fetch %s: %s", url, e)
                result.errors.append(f"Failed to fetch {url}: {e}")
                continue

            text = _extract_text(body)
            mentions = _find_mentions(text)
            result.mentions.extend(mentions)

    return result
