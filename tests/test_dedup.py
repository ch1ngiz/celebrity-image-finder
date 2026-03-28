import io
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from finder.dedup import deduplicate
from finder.models import FilteredImage


import random


def _make_test_image_file(tmp_path: Path, name: str, seed: int = 0, size: tuple = (100, 100)) -> Path:
    """Create a real image file for hashing with random noise from a seed."""
    path = tmp_path / name
    rng = random.Random(seed)
    img = Image.new("RGB", size)
    pixels = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            pixels[x, y] = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
    img.save(path, format="JPEG")
    return path


def _make_filtered(tmp_path: Path, name: str, confidence: float = 0.8,
                   seed: int = 0, width: int = 1024, height: int = 768) -> FilteredImage:
    """Create a FilteredImage with a real image file."""
    path = _make_test_image_file(tmp_path, name, seed=seed, size=(width, height))
    return FilteredImage(
        path=path, source="test", url=f"https://example.com/{name}",
        width=width, height=height, face_confidence=confidence,
    )


class TestDeduplicate:
    def test_removes_identical_images(self, tmp_path):
        # Two images from the same seed (identical content)
        img1 = _make_filtered(tmp_path, "a.jpg", confidence=0.9, seed=42)
        img2 = _make_filtered(tmp_path, "b.jpg", confidence=0.7, seed=42)

        results = deduplicate([img1, img2], threshold=10)
        assert len(results) == 1
        assert results[0].face_confidence == 0.9  # Keeps higher confidence

    def test_keeps_different_images(self, tmp_path):
        # Two images with very different random noise
        img1 = _make_filtered(tmp_path, "img1.jpg", seed=1)
        img2 = _make_filtered(tmp_path, "img2.jpg", seed=9999)

        results = deduplicate([img1, img2], threshold=10)
        assert len(results) == 2

    def test_empty_input(self, tmp_path):
        results = deduplicate([], threshold=10)
        assert results == []

    def test_single_image(self, tmp_path):
        img = _make_filtered(tmp_path, "single.jpg", seed=1)
        results = deduplicate([img], threshold=10)
        assert len(results) == 1

    def test_keeps_higher_resolution_on_tie(self, tmp_path):
        # Create a small image, then upscale it — same visual content, different resolution
        rng = random.Random(42)
        base = Image.new("RGB", (64, 64))
        pixels = base.load()
        for x in range(64):
            for y in range(64):
                pixels[x, y] = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))

        small_path = tmp_path / "small.jpg"
        base.resize((512, 512)).save(small_path, format="JPEG")
        large_path = tmp_path / "large.jpg"
        base.resize((1024, 1024)).save(large_path, format="JPEG")

        img_small = FilteredImage(path=small_path, source="test", url="small", width=512, height=512, face_confidence=0.8)
        img_large = FilteredImage(path=large_path, source="test", url="large", width=1024, height=1024, face_confidence=0.8)

        results = deduplicate([img_small, img_large], threshold=10)
        assert len(results) == 1
        assert results[0].width == 1024
