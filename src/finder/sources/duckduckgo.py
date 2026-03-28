import logging
import time

from ddgs import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from finder.models import ImageCandidate

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=3, min=5, max=60),
    retry=retry_if_exception_type(Exception),
    reraise=False,
    retry_error_callback=lambda retry_state: [],
)
def search(name: str, max_results: int = 150) -> list[ImageCandidate]:
    """Search DuckDuckGo Images for a person and return candidate URLs."""
    query = f"{name} rapper photo portrait -cartoon -drawing -anime -emoji"

    ddgs = DDGS()
    results = ddgs.images(
        keywords=query,
        max_results=max_results,
    )

    candidates = []
    seen_urls = set()

    for r in results:
        url = r.get("image", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            candidates.append(ImageCandidate(
                url=url,
                source="duckduckgo",
                artist_name=name,
            ))

    logger.info("DuckDuckGo: Found %d images for '%s'", len(candidates), name)

    # Delay to avoid rate limiting between searches
    time.sleep(5)

    return candidates
