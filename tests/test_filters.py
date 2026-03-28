from pathlib import Path
from unittest.mock import patch, MagicMock

from finder.filters import FaceResult, filter_images, _is_drawn  # noqa: F401
from finder.models import DownloadedImage

from PIL import Image
import numpy as np


def _make_image(tmp_path, name="test.jpg", width=800, height=600):
    """Helper to create a DownloadedImage for testing."""
    path = tmp_path / name
    path.touch()
    return DownloadedImage(
        path=path, source="test", url=f"https://example.com/{name}",
        width=width, height=height,
    )


def _make_photo(tmp_path, name="photo.jpg", width=256, height=256):
    """Create a realistic-ish photo with noise (high color variety)."""
    rng = np.random.RandomState(42)
    arr = rng.randint(0, 256, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(arr, "RGB")
    path = tmp_path / name
    img.save(path, format="JPEG")
    return path


def _make_cartoon(tmp_path, name="cartoon.png", width=256, height=256):
    """Create a cartoon-like image with very few flat colors."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:height // 2, :] = [255, 0, 0]       # top half solid red
    arr[height // 2:, :] = [0, 0, 255]        # bottom half solid blue
    arr[height // 4:height // 4 + 10, :] = [0, 0, 0]  # thin black line
    img = Image.fromarray(arr, "RGB")
    path = tmp_path / name
    img.save(path, format="PNG")
    return path


class TestFilterImages:
    def test_rejects_low_resolution(self, tmp_path):
        img = _make_image(tmp_path, width=400, height=300)
        with patch("finder.filters._detect_faces", return_value=FaceResult(1, 0.9, 0.2)):
            with patch("finder.filters._is_drawn", return_value=False):
                results = filter_images([img], min_resolution=512)
        assert len(results) == 0

    @patch("finder.filters._is_drawn", return_value=False)
    @patch("finder.filters._detect_faces", return_value=FaceResult(1, 0.85, 0.2))
    def test_accepts_single_face_photo(self, mock_face, mock_drawn, tmp_path):
        img = _make_image(tmp_path, width=1024, height=768)
        results = filter_images([img], min_resolution=512)
        assert len(results) == 1
        assert results[0].face_confidence == 0.85

    @patch("finder.filters._is_drawn", return_value=False)
    @patch("finder.filters._detect_faces", return_value=FaceResult(0, 0.0, 0.0))
    def test_rejects_no_face(self, mock_face, mock_drawn, tmp_path):
        img = _make_image(tmp_path, width=1024, height=768)
        results = filter_images([img], min_resolution=512)
        assert len(results) == 0

    @patch("finder.filters._is_drawn", return_value=False)
    @patch("finder.filters._detect_faces", return_value=FaceResult(3, 0.9, 0.1))
    def test_rejects_multiple_faces(self, mock_face, mock_drawn, tmp_path):
        img = _make_image(tmp_path, width=1024, height=768)
        results = filter_images([img], min_resolution=512)
        assert len(results) == 0

    @patch("finder.filters._detect_faces", return_value=FaceResult(1, 0.9, 0.2))
    @patch("finder.filters._is_drawn", return_value=True)
    def test_rejects_drawn_images(self, mock_drawn, mock_face, tmp_path):
        img = _make_image(tmp_path, width=1024, height=768)
        results = filter_images([img], min_resolution=512)
        assert len(results) == 0

    @patch("finder.filters._is_drawn", return_value=False)
    @patch("finder.filters._detect_faces", return_value=FaceResult(1, 0.9, 0.02))
    def test_rejects_tiny_face(self, mock_face, mock_drawn, tmp_path):
        img = _make_image(tmp_path, width=1024, height=768)
        results = filter_images([img], min_resolution=512)
        assert len(results) == 0


class TestIsDrawn:
    def test_photo_not_detected_as_drawn(self, tmp_path):
        path = _make_photo(tmp_path)
        assert _is_drawn(path) is False

    def test_cartoon_detected_as_drawn(self, tmp_path):
        path = _make_cartoon(tmp_path)
        assert _is_drawn(path) is True
