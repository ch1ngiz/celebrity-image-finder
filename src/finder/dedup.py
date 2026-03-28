import logging

from PIL import Image
import imagehash

from finder.models import FilteredImage

logger = logging.getLogger(__name__)


def deduplicate(
    images: list[FilteredImage],
    threshold: int = 10,
) -> list[FilteredImage]:
    """Remove near-duplicate images using perceptual hashing."""
    if not images:
        return []

    # Compute hashes
    hashed: list[tuple[FilteredImage, imagehash.ImageHash]] = []
    for img in images:
        try:
            pil_img = Image.open(img.path)
            h = imagehash.average_hash(pil_img)
            pil_img.close()
            hashed.append((img, h))
        except Exception as e:
            logger.debug("Failed to hash %s: %s", img.path.name, e)

    # Group duplicates — keep the best from each group
    keep: list[FilteredImage] = []
    used = set()

    for i, (img_a, hash_a) in enumerate(hashed):
        if i in used:
            continue

        # Find all duplicates of this image
        group = [(img_a, i)]
        for j, (img_b, hash_b) in enumerate(hashed):
            if j <= i or j in used:
                continue
            if hash_a - hash_b <= threshold:
                group.append((img_b, j))
                used.add(j)

        # Keep the best image from the group (highest confidence, then resolution)
        best = max(
            group,
            key=lambda g: (g[0].face_confidence, g[0].width * g[0].height),
        )
        keep.append(best[0])
        used.add(i)

    logger.info("Dedup: %d -> %d images (removed %d duplicates)", len(images), len(keep), len(images) - len(keep))
    return keep
