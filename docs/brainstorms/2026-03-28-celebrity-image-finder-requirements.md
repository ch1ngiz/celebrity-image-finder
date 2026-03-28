---
date: 2026-03-28
topic: celebrity-image-finder
---

# Celebrity Image Finder

## Problem Frame

Creating characters on Higgsfield requires multiple high-quality face photos from different angles for each person. When working with 50+ rappers/entertainers at a time, manually searching Google Images, filtering out low-res/watermarked results, and downloading one-by-one is painfully slow and doesn't scale.

## Requirements

- R1. Accept a list of person names as input (text file, one name per line) and process them in batch
- R2. Search multiple image sources per person: Genius API, Spotify API, Google Custom Search API, and DuckDuckGo image search
- R3. Collect 40-69 high-quality images per person that pass quality checks
- R4. Filter images for quality: minimum resolution threshold (512px+ on shortest side), clear face visible, no watermarks/logos, no heavy compression artifacts
- R5. Prefer variety in results: different angles, settings, and lighting conditions rather than near-duplicate shots
- R6. Save results in organized folders: `output/{person_name}/` with numbered image files
- R7. Provide progress output showing which person is being processed and how many qualifying images found
- R8. Handle failures gracefully: if one source is down or rate-limited, continue with remaining sources; if a person yields fewer than the target, report it and move on
- R9. Support a configurable target image count per person (default: 50)

## Success Criteria

- Can process a list of 50+ rapper names and produce organized image folders with minimal manual intervention
- Majority of downloaded images are usable for Higgsfield character creation (clear face, good resolution, varied angles)
- Full batch completes in a reasonable time without manual babysitting

## Scope Boundaries

- CLI tool only — no web UI or desktop app
- No direct integration with Higgsfield (output is local image folders the user uploads manually)
- No image editing/cropping — just finding and downloading
- Not building a persistent database or search index — run it, get images, done
- Focus on rappers/entertainers but should work for any public figure by name

## Key Decisions

- **Multi-source over single source:** No single source reliably provides 40-69 varied, high-quality images per person. Combining Genius + Spotify + Google CSE + DuckDuckGo gives best coverage.
- **APIs preferred over raw scraping where possible:** Genius and Spotify APIs provide reliable, high-quality images. Google CSE is an API. DuckDuckGo scraping is the only fragile piece, used as a supplementary source.
- **Quality filtering is automated, not manual:** At 50+ people x 50 images, manual curation doesn't scale. Automated resolution checks and face detection handle the bulk filtering.
- **Python as implementation language:** Rich ecosystem for image processing (Pillow, face_recognition), HTTP/API clients (requests, httpx), and CLI tools.

## Dependencies / Assumptions

- User will obtain API keys for: Genius API, Spotify API, Google Custom Search API
- Face detection library (e.g., face_recognition, OpenCV, or mediapipe) available for quality filtering
- Internet connection with reasonable bandwidth for batch image downloads
- DuckDuckGo scraping may break if they change their frontend — this is an accepted fragility

## Outstanding Questions

### Resolve Before Planning

(none)

### Deferred to Planning

- [Affects R4][Needs research] Best face detection library for this use case — face_recognition vs mediapipe vs OpenCV cascades. Trade-off between accuracy and setup complexity.
- [Affects R5][Technical] Deduplication strategy — perceptual hashing (e.g., imagehash) to avoid near-duplicate images across sources?
- [Affects R2][Technical] Rate limiting strategy across APIs — sequential vs concurrent requests, backoff policies
- [Affects R4][Needs research] Watermark detection approach — heuristic (check for semi-transparent overlays) vs ML-based vs skip for v1
- [Affects R9][Technical] Config format — CLI flags, config file, or both

## Next Steps

-> `/ce:plan` for structured implementation planning
