import logging
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from finder.config import Config
from finder.dedup import deduplicate
from finder.downloader import download_all
from finder.filters import filter_images
from finder.models import BatchResult, ImageCandidate, PersonResult
from finder.review import review_and_select
from finder.sources import bing, duckduckgo, genius, spotify

logger = logging.getLogger(__name__)


def _sanitize_name(name: str) -> str:
    """Convert a person name to a safe folder name."""
    sanitized = re.sub(r"[^\w\s-]", "", name)
    sanitized = re.sub(r"\s+", "_", sanitized.strip())
    return sanitized or "unknown"


def _fetch_all_sources(name: str, config: Config) -> list[ImageCandidate]:
    """Fetch image candidates from all sources concurrently."""
    candidates = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(genius.search, name, config.genius_token): "genius",
            executor.submit(spotify.search, name, config.spotify_client_id, config.spotify_client_secret): "spotify",
            executor.submit(duckduckgo.search, name): "duckduckgo",
            executor.submit(bing.search, name): "bing",
        }

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                results = future.result()
                candidates.extend(results)
            except Exception as e:
                logger.warning("Source %s failed for '%s': %s", source_name, name, e)

    return candidates


def process_person(name: str, config: Config) -> PersonResult:
    """Process a single person: search, download, filter, dedup, then review."""
    person_dir = config.output_dir / _sanitize_name(name)
    person_dir.mkdir(parents=True, exist_ok=True)

    errors = []

    # Step 1: Fetch candidates from all sources
    candidates = _fetch_all_sources(name, config)
    if not candidates:
        msg = "No image candidates found from any source"
        errors.append(msg)
        logger.warning("%s: %s", name, msg)
        return PersonResult(name=name, image_count=0, output_dir=person_dir, errors=errors)

    logger.info("%s: Found %d candidates from all sources", name, len(candidates))

    # Step 2: Download candidates to temp directory
    with tempfile.TemporaryDirectory(prefix="finder_") as temp_dir:
        temp_path = Path(temp_dir)
        downloaded = download_all(candidates, temp_path)

        if not downloaded:
            msg = "No images downloaded successfully"
            errors.append(msg)
            logger.warning("%s: %s", name, msg)
            return PersonResult(name=name, image_count=0, output_dir=person_dir, errors=errors)

        logger.info("%s: Downloaded %d images", name, len(downloaded))

        # Step 3: Basic quality filter (resolution + has a face)
        filtered = filter_images(downloaded, min_resolution=config.min_resolution)

        if not filtered:
            msg = "No images passed quality filtering"
            errors.append(msg)
            logger.warning("%s: %s", name, msg)
            return PersonResult(name=name, image_count=0, output_dir=person_dir, errors=errors)

        logger.info("%s: %d images passed basic filters", name, len(filtered))

        # Step 4: Deduplication
        unique = deduplicate(filtered)
        logger.info("%s: %d unique images after dedup", name, len(unique))

        # Step 5: Sort by face confidence
        unique.sort(key=lambda img: img.face_confidence, reverse=True)

        # Step 6: Open review gallery — user selects which to keep
        image_count = review_and_select(name, unique, person_dir)

    if image_count < config.target_count:
        msg = f"Selected {image_count}/{config.target_count} images (below target)"
        errors.append(msg)

    return PersonResult(
        name=name,
        image_count=image_count,
        output_dir=person_dir,
        errors=errors,
    )


def process_batch(names: list[str], config: Config) -> BatchResult:
    """Process a batch of names sequentially with manual review."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    # Deduplicate names (case-insensitive)
    seen = set()
    unique_names = []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            unique_names.append(name)

    config.output_dir.mkdir(parents=True, exist_ok=True)

    total = len(unique_names)
    result = BatchResult()

    print(f"\nProcessing {total} names...\n")

    for i, name in enumerate(unique_names, start=1):
        print(f"[{i}/{total}] Processing: {name}")
        person_result = process_person(name, config)
        result.results.append(person_result)
        result.total_images += person_result.image_count

        if person_result.errors:
            for err in person_result.errors:
                print(f"  Warning: {err}")
        print(f"  -> Saved {person_result.image_count} images\n")

    # Final summary
    print("=" * 50)
    print(f"DONE! Processed {total} people, {result.total_images} total images")
    print(f"Output directory: {config.output_dir}")
    print()
    for pr in result.results:
        status = "OK" if pr.image_count >= config.target_count else "LOW"
        print(f"  [{status}] {pr.name}: {pr.image_count} images")

    return result
