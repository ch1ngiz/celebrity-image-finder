---
title: "feat: Build celebrity image finder CLI tool"
type: feat
status: active
date: 2026-03-28
origin: docs/brainstorms/2026-03-28-celebrity-image-finder-requirements.md
---

# feat: Build celebrity image finder CLI tool

## Overview

Build a Python CLI tool that accepts a list of celebrity/rapper names and automatically finds, downloads, quality-filters, and deduplicates high-resolution face photos from multiple sources. Output is organized folders of images ready for Higgsfield character creation.

## Problem Frame

Creating characters on Higgsfield requires multiple high-quality face photos from different angles per person. Manually searching, filtering, and downloading images for 50+ rappers doesn't scale. (see origin: docs/brainstorms/2026-03-28-celebrity-image-finder-requirements.md)

## Requirements Trace

- R1. Accept a list of person names as input (text file, one name per line) and process them in batch
- R2. Search multiple image sources per person: Genius API, Spotify API, and DuckDuckGo image search
- R3. Collect 40-69 high-quality images per person that pass quality checks
- R4. Filter images for quality: minimum resolution threshold (512px+ on shortest side), clear face visible, no heavy compression artifacts
- R5. Prefer variety in results: different angles, settings, and lighting conditions rather than near-duplicate shots
- R6. Save results in organized folders: `output/{person_name}/` with numbered image files
- R7. Provide progress output showing which person is being processed and how many qualifying images found
- R8. Handle failures gracefully: if one source is down or rate-limited, continue with remaining sources; if a person yields fewer than the target, report it and move on
- R9. Support a configurable target image count per person (default: 50)

**Note:** R2 updated from origin — Google Custom Search API is closed to new customers and sunsets Jan 2027. Replaced with DuckDuckGo image search as the primary web source.

## Scope Boundaries

- CLI tool only — no web UI or desktop app
- No direct Higgsfield integration — output is local image folders
- No image editing/cropping — finding and downloading only
- No persistent database — run it, get images, done
- Watermark detection deferred — too complex for v1; rely on source quality and resolution filtering
- Focus on rappers/entertainers but works for any public figure by name

## Context & Research

### External References

- **MediaPipe Face Detection** — Google's BlazeFace model, 98.6% AP, confidence scores, fast batch processing, clean pip install on macOS ARM64
- **lyricsgenius** — Python client for Genius API, artist search + image retrieval
- **spotipy** — Python client for Spotify API, Client Credentials flow (no user interaction), artist images
- **duckduckgo-search** — Python library for DuckDuckGo image search, no API key needed, primary source for volume/variety
- **imagehash** — Perceptual hashing for near-duplicate detection across sources
- **tenacity** — Retry/backoff library for resilient API calls

### Institutional Learnings

- None (greenfield project)

## Key Technical Decisions

- **DuckDuckGo replaces Google CSE:** Google Custom Search API is closed to new customers and sunsets Jan 2027. DuckDuckGo image search via `duckduckgo-search` is free, needs no API key, and provides broad web image coverage. This is the primary volume source.
- **MediaPipe for face detection:** Best balance of accuracy (98.6% AP), speed, easy installation, and confidence scores for quality thresholds. OpenCV YuNet is the fallback if needed.
- **Perceptual hashing for deduplication:** `imagehash` with average hash (ahash) at a Hamming distance threshold of ~10 to catch near-duplicates across sources while allowing legitimate angle variations.
- **Client Credentials flow for Spotify:** No user login required — just client ID and secret. Simplest auth for a CLI tool.
- **CLI flags + .env for config:** `argparse` for runtime options (input file, target count, output dir). `.env` file for API keys (Genius token, Spotify client ID/secret). No config file needed for v1.
- **Sequential per-person, concurrent per-source:** Process one person at a time (clear progress), but fetch from all sources concurrently per person for speed.
- **Python 3.10+:** f-strings, match statements, modern type hints.

## Open Questions

### Resolved During Planning

- **Face detection library:** MediaPipe — best accuracy/speed/install trade-off (see research)
- **Deduplication strategy:** imagehash perceptual hashing with ~10 Hamming distance threshold
- **Rate limiting:** tenacity retry/backoff per source, sequential person processing avoids thundering herd
- **Watermark detection:** Skip for v1 — complexity not justified, rely on resolution + face detection filtering
- **Config format:** CLI flags for runtime options, .env for API keys

### Deferred to Implementation

- **Optimal MediaPipe confidence threshold:** Start at 0.5, may need tuning based on real results. Adjust if too many good images rejected or bad ones accepted.
- **DuckDuckGo rate limits in practice:** Unknown until real batch runs. May need to add delays between searches.
- **imagehash threshold tuning:** Hamming distance ~10 is a starting point. May need adjustment based on how aggressively it deduplicates.

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
Pipeline per person:
  1. Search all sources concurrently:
     - Genius API → artist photos (2-5 images)
     - Spotify API → artist images (1-3 images)
     - DuckDuckGo → web images (~100 candidate URLs)
  2. Download candidate images (skip failures)
  3. Quality filter pipeline (sequential per image):
     a. Validate image format (JPEG/PNG/WebP)
     b. Check resolution (512px+ shortest side)
     c. Face detection (MediaPipe confidence >= threshold)
     d. Face size check (face bbox >= 15% of image area)
  4. Deduplication (imagehash across all passed images)
  5. Select top N images (by face confidence score)
  6. Save to output/{person_name}/ with numbered filenames
```

## Implementation Units

- [ ] **Unit 1: Project scaffolding and CLI**

  **Goal:** Set up the Python project structure, dependencies, and CLI entry point that accepts a names file and configuration flags.

  **Requirements:** R1, R9

  **Dependencies:** None

  **Files:**
  - Create: `pyproject.toml`
  - Create: `src/finder/__init__.py`
  - Create: `src/finder/cli.py`
  - Create: `src/finder/config.py`
  - Create: `.env.example`
  - Create: `.gitignore`
  - Test: `tests/test_cli.py`

  **Approach:**
  - Use `pyproject.toml` with setuptools for project definition
  - `cli.py`: argparse with `--input` (names file path), `--output` (output directory, default: `output/`), `--count` (target images per person, default: 50), `--min-resolution` (minimum shortest side, default: 512)
  - `config.py`: Load `.env` file for API keys (GENIUS_TOKEN, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET), validate they exist before running
  - `.env.example`: Template showing required keys
  - Entry point: `finder` command via pyproject.toml scripts

  **Patterns to follow:**
  - Standard Python project layout with `src/` directory
  - `python-dotenv` for .env loading

  **Test scenarios:**
  - Happy path: CLI parses valid input file path, output dir, and count flag correctly
  - Happy path: Config loads all required API keys from .env
  - Error path: CLI exits with clear error when input file doesn't exist
  - Error path: Config raises clear error when API keys are missing from .env
  - Edge case: CLI uses default values when optional flags are omitted

  **Verification:**
  - `finder --help` prints usage with all flags
  - `finder --input names.txt` fails gracefully with clear message when .env is missing

- [ ] **Unit 2: Image source — Genius API**

  **Goal:** Search Genius for an artist by name and retrieve all available artist photo URLs.

  **Requirements:** R2, R8

  **Dependencies:** Unit 1

  **Files:**
  - Create: `src/finder/sources/genius.py`
  - Create: `src/finder/sources/__init__.py`
  - Test: `tests/test_sources_genius.py`

  **Approach:**
  - Use `lyricsgenius` library to search for artist by name
  - Extract artist header image and any additional artist images from the API response
  - Return list of image URLs with source metadata
  - Wrap API calls with tenacity retry/backoff
  - Return empty list on failure (don't crash the pipeline)

  **Patterns to follow:**
  - Each source module exposes a `search(name: str) -> list[ImageCandidate]` interface
  - `ImageCandidate` is a simple dataclass with `url`, `source`, `artist_name` fields

  **Test scenarios:**
  - Happy path: Search for a known rapper name returns a list of image URLs
  - Error path: Search for a nonexistent name returns empty list without raising
  - Error path: API timeout or rate limit triggers retry then returns empty list
  - Edge case: Artist found but has no images — returns empty list

  **Verification:**
  - Given a valid Genius token and a known rapper name, returns at least one image URL
  - Given an invalid token, fails gracefully with logged warning

- [ ] **Unit 3: Image source — Spotify API**

  **Goal:** Search Spotify for an artist by name and retrieve artist image URLs.

  **Requirements:** R2, R8

  **Dependencies:** Unit 1

  **Files:**
  - Create: `src/finder/sources/spotify.py`
  - Test: `tests/test_sources_spotify.py`

  **Approach:**
  - Use `spotipy` with Client Credentials flow (SpotifyClientCredentials)
  - Search for artist by name, take the top match
  - Extract image URLs from artist object (Spotify provides multiple resolutions)
  - Return list of ImageCandidate objects
  - Wrap with tenacity retry/backoff
  - Return empty list on failure

  **Patterns to follow:**
  - Same `search(name: str) -> list[ImageCandidate]` interface as Genius source

  **Test scenarios:**
  - Happy path: Search for a known artist returns image URLs at multiple resolutions
  - Error path: Invalid credentials trigger graceful failure with warning
  - Error path: Artist not found returns empty list
  - Edge case: Multiple artists with similar names — takes highest-popularity match

  **Verification:**
  - Given valid Spotify credentials and a known rapper name, returns image URLs

- [ ] **Unit 4: Image source — DuckDuckGo**

  **Goal:** Search DuckDuckGo Images for a person's name and retrieve candidate image URLs. This is the primary volume source.

  **Requirements:** R2, R5, R8

  **Dependencies:** Unit 1

  **Files:**
  - Create: `src/finder/sources/duckduckgo.py`
  - Test: `tests/test_sources_duckduckgo.py`

  **Approach:**
  - Use `duckduckgo-search` library's `DDGS().images()` method
  - Search query: `"{person_name}" rapper portrait face` (optimize for face photos)
  - Request up to 150 candidate URLs to have enough after quality filtering
  - Filter by size parameter (prefer "Large" or "Wallpaper" size)
  - Return list of ImageCandidate objects
  - Add small delay between searches to avoid rate limiting
  - Wrap with tenacity retry/backoff, return empty list on failure

  **Patterns to follow:**
  - Same `search(name: str) -> list[ImageCandidate]` interface

  **Test scenarios:**
  - Happy path: Search for a known rapper returns 100+ candidate image URLs
  - Error path: DuckDuckGo rate limit triggers backoff then returns partial results or empty list
  - Edge case: Ambiguous name returns mixed results — filtering handles this downstream
  - Edge case: Very obscure name returns few results — returns whatever is available

  **Verification:**
  - Given a known rapper name, returns a substantial list of candidate URLs

- [ ] **Unit 5: Image downloader**

  **Goal:** Download images from URLs concurrently, validate they are real images, and save to a temp staging area.

  **Requirements:** R3, R8

  **Dependencies:** Unit 1

  **Files:**
  - Create: `src/finder/downloader.py`
  - Test: `tests/test_downloader.py`

  **Approach:**
  - Accept a list of ImageCandidate URLs, download concurrently (ThreadPoolExecutor, ~10 workers)
  - Validate each download: check Content-Type is image, file is valid image (Pillow can open it), file size is reasonable (>10KB, <50MB)
  - Save valid images to a temp directory with unique filenames
  - Return list of downloaded file paths with metadata
  - Skip failed downloads silently (log warning), don't crash on individual failures
  - Use requests with timeout (10s connect, 30s read)

  **Patterns to follow:**
  - `download_all(candidates: list[ImageCandidate], temp_dir: Path) -> list[DownloadedImage]`
  - `DownloadedImage` dataclass with `path`, `source`, `url`, `width`, `height`

  **Test scenarios:**
  - Happy path: Downloads multiple valid images concurrently, returns file paths
  - Error path: Invalid URL returns no result without crashing batch
  - Error path: Timeout on slow server skips that image
  - Edge case: Non-image file (HTML error page) with image URL is rejected
  - Edge case: Truncated/corrupt image file is rejected

  **Verification:**
  - Given a list of real image URLs, downloads and validates the majority successfully

- [ ] **Unit 6: Quality filter pipeline**

  **Goal:** Filter downloaded images for face quality using MediaPipe face detection and resolution checks.

  **Requirements:** R4, R5

  **Dependencies:** Unit 5

  **Files:**
  - Create: `src/finder/filters.py`
  - Test: `tests/test_filters.py`

  **Approach:**
  - Resolution check: reject if shortest side < 512px (configurable)
  - Face detection: use MediaPipe FaceDetector with model_selection=1 (full-range)
  - Accept images where at least one face detection has confidence >= 0.5
  - Face size check: face bounding box must be >= 15% of image area (ensures face is prominent, not a tiny face in a crowd shot)
  - Return filtered images with face confidence scores attached (useful for ranking later)
  - Process images sequentially (MediaPipe is fast enough, simpler than managing detector instances)

  **Patterns to follow:**
  - `filter_images(images: list[DownloadedImage], min_resolution: int) -> list[FilteredImage]`
  - `FilteredImage` extends DownloadedImage with `face_confidence` score

  **Test scenarios:**
  - Happy path: Clear face photo at high resolution passes all checks
  - Edge case: Image with face but below resolution threshold is rejected
  - Edge case: High-res image with no detectable face (back of head, logo) is rejected
  - Edge case: Group photo where all faces are tiny (< 15% area) is rejected
  - Edge case: Image with multiple faces — passes if at least one meets criteria
  - Happy path: Face confidence score is attached to passing images

  **Verification:**
  - Given a mix of good face photos and non-face images, correctly accepts faces and rejects non-faces

- [ ] **Unit 7: Deduplication**

  **Goal:** Remove near-duplicate images across all sources using perceptual hashing.

  **Requirements:** R5

  **Dependencies:** Unit 6

  **Files:**
  - Create: `src/finder/dedup.py`
  - Test: `tests/test_dedup.py`

  **Approach:**
  - Compute average hash (ahash) for each filtered image using `imagehash`
  - Compare all pairs — if Hamming distance <= 10, mark as duplicate
  - Keep the higher-confidence or higher-resolution copy from each duplicate group
  - Return deduplicated list

  **Patterns to follow:**
  - `deduplicate(images: list[FilteredImage], threshold: int = 10) -> list[FilteredImage]`

  **Test scenarios:**
  - Happy path: Two very similar images (same photo, different crops) — one is removed
  - Happy path: Two different angles of same person — both kept
  - Edge case: Identical image from two sources — one copy removed, higher quality kept
  - Edge case: All images are unique — nothing removed
  - Edge case: Empty input — returns empty list

  **Verification:**
  - Given images with known duplicates, reduces count while preserving unique angles

- [ ] **Unit 8: Orchestrator and batch processing**

  **Goal:** Tie all components together into the main pipeline that processes a list of names end-to-end with progress reporting.

  **Requirements:** R1, R3, R6, R7, R8, R9

  **Dependencies:** Units 2-7

  **Files:**
  - Create: `src/finder/pipeline.py`
  - Modify: `src/finder/cli.py` (wire CLI to pipeline)
  - Test: `tests/test_pipeline.py`

  **Approach:**
  - Read names file, strip whitespace, skip blank lines
  - For each person:
    1. Print progress: "Processing {name} ({n}/{total})..."
    2. Run all sources concurrently (asyncio.gather or ThreadPoolExecutor)
    3. Merge candidate lists
    4. Download candidates
    5. Run quality filter pipeline
    6. Run deduplication
    7. Rank by face confidence, take top N (configurable target count)
    8. Copy final images to `output/{person_name}/001.jpg`, `002.jpg`, etc.
    9. Print summary: "Found {count} images for {name}" (warn if below target)
  - After all names: print final summary with per-person counts
  - Sanitize person names for folder names (replace spaces with underscores, remove special chars)
  - Clean up temp files after each person

  **Patterns to follow:**
  - `process_person(name: str, config: Config) -> PersonResult`
  - `process_batch(names: list[str], config: Config) -> BatchResult`

  **Test scenarios:**
  - Happy path: Processing a single name produces an organized output folder with numbered images
  - Happy path: Processing a batch of names produces one folder per person
  - Error path: One person fails entirely — skipped with warning, others still processed
  - Error path: One source fails for a person — other sources still used
  - Edge case: Person yields fewer images than target — warning printed, continues
  - Edge case: Names file has blank lines and whitespace — handled cleanly
  - Edge case: Duplicate names in input — processed once or idempotent
  - Integration: Full pipeline from name to output folder produces images that pass face detection

  **Verification:**
  - Given a names file with 2-3 known rappers, produces organized output folders with face-verified images
  - Progress output shows processing status for each person

## System-Wide Impact

- **Interaction graph:** Linear pipeline — CLI -> sources -> downloader -> filters -> dedup -> output. No callbacks or observers.
- **Error propagation:** Errors in individual sources or image downloads are caught and logged, never crash the batch. Only fatal errors (missing API keys, no input file) should halt execution.
- **State lifecycle risks:** Temp files accumulate during processing. Must clean up temp directory after each person to avoid disk exhaustion on large batches.
- **API surface parity:** N/A — single CLI interface.
- **Integration coverage:** The orchestrator unit's integration test validates the full pipeline end-to-end.

## Risks & Dependencies

- **DuckDuckGo scraping fragility:** `duckduckgo-search` scrapes DDG's frontend and may break if they change it. Accepted risk per origin doc. Mitigation: tenacity retries, graceful fallback to other sources.
- **API key management:** User must obtain Genius and Spotify API keys. Mitigation: clear .env.example and error messages.
- **MediaPipe model download:** MediaPipe downloads model files on first use (~5MB). Mitigation: document this in README, handle gracefully if download fails.
- **Rate limits at scale:** Processing 50+ people hits APIs heavily. Mitigation: sequential per-person processing, delays between DuckDuckGo searches, tenacity backoff.
- **Disk space:** 50 people x 50 images x ~500KB avg = ~1.25GB. Not huge but worth noting.

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-28-celebrity-image-finder-requirements.md](docs/brainstorms/2026-03-28-celebrity-image-finder-requirements.md)
- External: [MediaPipe Face Detection](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector)
- External: [lyricsgenius](https://github.com/johnwmillr/LyricsGenius)
- External: [spotipy](https://spotipy.readthedocs.io/)
- External: [duckduckgo-search](https://github.com/deedy5/duckduckgo_search)
- External: [imagehash](https://github.com/JohannesBuchner/imagehash)
- External: [tenacity](https://github.com/jd/tenacity)
