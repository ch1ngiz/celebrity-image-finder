import logging

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
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
def search(name: str, client_id: str, client_secret: str) -> list[ImageCandidate]:
    """Search Spotify for an artist and return image URLs."""
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    sp = spotipy.Spotify(auth_manager=auth_manager, requests_timeout=15)

    results = sp.search(q=f"artist:{name}", type="artist", limit=5)
    items = results.get("artists", {}).get("items", [])

    if not items:
        logger.warning("Spotify: No artist found for '%s'", name)
        return []

    # Take the highest-popularity match
    artist = max(items, key=lambda a: a.get("popularity", 0))

    candidates = []
    for img in artist.get("images", []):
        url = img.get("url")
        if url:
            candidates.append(ImageCandidate(
                url=url,
                source="spotify",
                artist_name=name,
            ))

    logger.info("Spotify: Found %d images for '%s'", len(candidates), name)
    return candidates
