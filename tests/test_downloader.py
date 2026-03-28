import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from finder.downloader import download_all, _download_one
from finder.models import ImageCandidate


def _make_test_image(width=800, height=600, fmt="JPEG") -> bytes:
    """Create a valid test image in memory large enough to pass min file size."""
    import random
    random.seed(42)
    img = Image.new("RGB", (width, height))
    # Fill with random noise so JPEG doesn't compress below 10KB
    pixels = img.load()
    for x in range(width):
        for y in range(height):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestDownloadOne:
    @patch("finder.downloader.requests.get")
    def test_downloads_valid_image(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_resp.content = _make_test_image()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        candidate = ImageCandidate(url="https://example.com/test.jpg", source="test", artist_name="Test")
        result = _download_one(candidate, tmp_path)

        assert result is not None
        assert result.width == 800
        assert result.height == 600
        assert result.path.exists()

    @patch("finder.downloader.requests.get")
    def test_rejects_non_image_content_type(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "text/html"}
        mock_resp.content = b"<html>Not an image</html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        candidate = ImageCandidate(url="https://example.com/page.html", source="test", artist_name="Test")
        result = _download_one(candidate, tmp_path)
        assert result is None

    @patch("finder.downloader.requests.get")
    def test_rejects_tiny_files(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_resp.content = b"tiny"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        candidate = ImageCandidate(url="https://example.com/tiny.jpg", source="test", artist_name="Test")
        result = _download_one(candidate, tmp_path)
        assert result is None

    @patch("finder.downloader.requests.get")
    def test_handles_timeout(self, mock_get, tmp_path):
        import requests
        mock_get.side_effect = requests.Timeout("Connection timed out")

        candidate = ImageCandidate(url="https://example.com/slow.jpg", source="test", artist_name="Test")
        result = _download_one(candidate, tmp_path)
        assert result is None

    @patch("finder.downloader.requests.get")
    def test_handles_corrupt_image(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_resp.content = b"x" * 20000  # Enough bytes but not a real image
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        candidate = ImageCandidate(url="https://example.com/corrupt.jpg", source="test", artist_name="Test")
        result = _download_one(candidate, tmp_path)
        assert result is None


class TestDownloadAll:
    @patch("finder.downloader._download_one")
    def test_downloads_multiple(self, mock_dl, tmp_path):
        from finder.models import DownloadedImage
        mock_dl.side_effect = [
            DownloadedImage(path=tmp_path / "1.jpg", source="test", url="url1", width=800, height=600),
            None,  # Failed download
            DownloadedImage(path=tmp_path / "2.jpg", source="test", url="url3", width=1024, height=768),
        ]

        candidates = [
            ImageCandidate(url=f"https://example.com/{i}.jpg", source="test", artist_name="Test")
            for i in range(3)
        ]

        results = download_all(candidates, tmp_path, max_workers=2)
        assert len(results) == 2
