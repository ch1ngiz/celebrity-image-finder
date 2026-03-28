import logging
import json
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import requests as http_requests

from finder.models import ImageCandidate

logger = logging.getLogger(__name__)

BING_URL = "https://www.bing.com/images/search"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=False,
    retry_error_callback=lambda retry_state: [],
)
def search(name: str, max_results: int = 150) -> list[ImageCandidate]:
    """Search Bing Images for a person and return candidate URLs."""
    query = f"{name} rapper photo portrait -cartoon -drawing -anime -emoji -fan-art"
    candidates = []
    seen_urls = set()
    offset = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    while len(candidates) < max_results:
        params = {
            "q": query,
            "first": offset,
            "count": 50,
            "qft": "+filterui:imagesize-large",
            "form": "IRFLTR",
        }

        resp = http_requests.get(BING_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # Extract image URLs from Bing's murl field in HTML
        # Bing encodes quotes as &quot; in the page source
        import re
        urls = re.findall(r'&quot;murl&quot;:&quot;(https?://[^&]+)', html)

        if not urls:
            break

        new_count = 0
        for url in urls:
            if url not in seen_urls and len(candidates) < max_results:
                seen_urls.add(url)
                candidates.append(ImageCandidate(
                    url=url,
                    source="bing",
                    artist_name=name,
                ))
                new_count += 1

        if new_count == 0:
            break

        offset += 50

    logger.info("Bing: Found %d images for '%s'", len(candidates), name)
    return candidates
