import re
import urllib.parse


def extract_place_id_from_url(url: str) -> str | None:
    """Extract a place identifier from a Google Maps URL."""
    if not url:
        return None
    # Pattern: /place/.../@lat,lng or /maps/place/...
    # Try to extract the place name from the URL path
    parsed = urllib.parse.urlparse(url)
    path = parsed.path

    # Match patterns like /maps/place/PLACE_NAME/
    match = re.search(r"/place/([^/@]+)", path)
    if match:
        return urllib.parse.unquote(match.group(1))
    return None


def normalize_place_key(
    name: str | None = None,
    address: str | None = None,
    google_maps_url: str | None = None,
) -> str:
    """Generate a normalized key for deduplication."""
    parts: list[str] = []

    if name:
        parts.append(name.strip())
    if address:
        parts.append(address.strip())

    if not parts and google_maps_url:
        extracted = extract_place_id_from_url(google_maps_url)
        if extracted:
            parts.append(extracted)

    if not parts:
        return "unknown"

    key = "_".join(parts)
    # Normalize: lowercase, collapse whitespace
    key = re.sub(r"\s+", "_", key.lower().strip())
    # Remove special chars except underscores and CJK
    key = re.sub(r"[^\w\u3000-\u9fff\uff00-\uffef]", "", key)
    return key[:200]
