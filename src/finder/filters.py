import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import requests
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from PIL import Image

from finder.models import DownloadedImage, FilteredImage

logger = logging.getLogger(__name__)

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
MODEL_DIR = Path.home() / ".cache" / "celebrity-image-finder"
MODEL_PATH = MODEL_DIR / "blaze_face_short_range.tflite"

_detector = None


def _ensure_model() -> Path:
    """Download the face detection model if not cached."""
    if MODEL_PATH.exists():
        return MODEL_PATH

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading face detection model (first run only)...")
    resp = requests.get(MODEL_URL, timeout=30)
    resp.raise_for_status()
    MODEL_PATH.write_bytes(resp.content)
    logger.info("Model saved to %s", MODEL_PATH)
    return MODEL_PATH


def _get_detector(min_confidence: float = 0.5) -> vision.FaceDetector:
    """Get or create a shared FaceDetector instance."""
    global _detector
    if _detector is None:
        model_path = _ensure_model()
        base_options = mp_python.BaseOptions(
            model_asset_path=str(model_path)
        )
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=min_confidence,
        )
        _detector = vision.FaceDetector.create_from_options(options)
    return _detector


@dataclass
class FaceResult:
    face_count: int
    best_confidence: float
    best_face_ratio: float


def _detect_faces(image_path: Path) -> FaceResult:
    """Detect all faces in an image."""
    try:
        pil_img = Image.open(image_path).convert("RGB")
        rgb_array = np.asarray(pil_img)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_array)

        detector = _get_detector()
        result = detector.detect(image)

        if not result.detections:
            return FaceResult(face_count=0, best_confidence=0.0, best_face_ratio=0.0)

        image_area = image.width * image.height
        best = max(result.detections, key=lambda d: d.categories[0].score)
        confidence = best.categories[0].score
        bbox = best.bounding_box
        face_area = bbox.width * bbox.height
        face_ratio = face_area / image_area if image_area > 0 else 0

        return FaceResult(
            face_count=len(result.detections),
            best_confidence=confidence,
            best_face_ratio=face_ratio,
        )

    except Exception as e:
        logger.debug("Face detection failed for %s: %s", image_path, e)
        return FaceResult(face_count=0, best_confidence=0.0, best_face_ratio=0.0)


def filter_images(
    images: list[DownloadedImage],
    min_resolution: int = 512,
) -> list[FilteredImage]:
    """Basic filtering: resolution and has at least one face."""
    filtered = []

    for img in images:
        shortest_side = min(img.width, img.height)
        if shortest_side < min_resolution:
            continue

        face = _detect_faces(img.path)

        if face.face_count == 0:
            continue

        if face.best_face_ratio < 0.03:
            continue

        filtered.append(FilteredImage(
            path=img.path,
            source=img.source,
            url=img.url,
            width=img.width,
            height=img.height,
            face_confidence=face.best_confidence,
        ))

    logger.info("Filtered: %d/%d images have a face at sufficient resolution", len(filtered), len(images))
    return filtered
