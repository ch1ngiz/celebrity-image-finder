import logging

import lyricsgenius
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

from finder.models import ImageCandidate

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, TimeoutError)),
    reraise=False,
    retry_error_callback=lambda retry_state: [],
)
def search(name: str, token: str) -> list[ImageCandidate]:
    """Search Genius for an artist and return image URLs."""
    genius = lyricsgenius.Genius(token, timeout=15, retries=1, verbose=False)
    artist = genius.search_artist(name, max_songs=0, get_full_info=True)

    if artist is None:
        logger.warning("Genius: No artist found for '%s'", name)
        return []

    candidates = []

    if artist.header_image_url:
        candidates.append(ImageCandidate(
            url=artist.header_image_url,
            source="genius",
            artist_name=name,
        ))

    if artist.image_url:
        candidates.append(ImageCandidate(
            url=artist.image_url,
            source="genius",
            artist_name=name,
        ))

    # Deduplicate URLs from Genius
    seen = set()
    unique = []
    for c in candidates:
        if c.url not in seen:
            seen.add(c.url)
            unique.append(c)

    logger.info("Genius: Found %d images for '%s'", len(unique), name)
    return unique
