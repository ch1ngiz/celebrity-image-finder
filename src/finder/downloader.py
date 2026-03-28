import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from PIL import Image

from finder.models import DownloadedImage, ImageCandidate

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
MIN_FILE_SIZE = 10 * 1024       # 10 KB
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_WORKERS = 10


def _download_one(candidate: ImageCandidate, temp_dir: Path) -> DownloadedImage | None:
    """Download a single image and validate it."""
    try:
        resp = requests.get(
            candidate.url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={"User-Agent": "CelebrityImageFinder/0.1"},
            stream=True,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return None

        data = resp.content
        if len(data) < MIN_FILE_SIZE or len(data) > MAX_FILE_SIZE:
            return None

        # Determine extension from content type
        ext = ".jpg"
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"

        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = temp_dir / filename
        filepath.write_bytes(data)

        # Validate it's a real image Pillow can open
        img = Image.open(filepath)
        img.verify()
        # Re-open after verify (verify closes the file)
        img = Image.open(filepath)
        width, height = img.size
        img.close()

        return DownloadedImage(
            path=filepath,
            source=candidate.source,
            url=candidate.url,
            width=width,
            height=height,
        )

    except Exception as e:
        logger.debug("Failed to download %s: %s", candidate.url, e)
        return None


def download_all(
    candidates: list[ImageCandidate],
    temp_dir: Path,
    max_workers: int = MAX_WORKERS,
) -> list[DownloadedImage]:
    """Download images concurrently, returning valid downloads."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_download_one, c, temp_dir): c
            for c in candidates
        }
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)

    logger.info("Downloaded %d/%d images", len(results), len(candidates))
    return results
