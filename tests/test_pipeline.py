from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from finder.config import Config
from finder.models import (
    BatchResult, DownloadedImage, FilteredImage,
    ImageCandidate, PersonResult,
)
from finder.pipeline import _sanitize_name, process_person, process_batch


class TestSanitizeName:
    def test_basic_name(self):
        assert _sanitize_name("Drake") == "Drake"

    def test_spaces_to_underscores(self):
        assert _sanitize_name("Kendrick Lamar") == "Kendrick_Lamar"

    def test_special_characters_removed(self):
        assert _sanitize_name("Lil' Wayne") == "Lil_Wayne"

    def test_multiple_spaces(self):
        assert _sanitize_name("A  B   C") == "A_B_C"

    def test_empty_string(self):
        assert _sanitize_name("") == "unknown"


def _make_config(tmp_path: Path, target_count: int = 5) -> Config:
    """Create a test config."""
    input_file = tmp_path / "names.txt"
    input_file.write_text("Test Name\n")
    return Config(
        input_file=input_file,
        output_dir=tmp_path / "output",
        target_count=target_count,
        min_resolution=512,
        genius_token="fake",
        spotify_client_id="fake",
        spotify_client_secret="fake",
    )


class TestProcessPerson:
    @patch("finder.pipeline.deduplicate")
    @patch("finder.pipeline.filter_images")
    @patch("finder.pipeline.download_all")
    @patch("finder.pipeline._fetch_all_sources")
    def test_full_pipeline(self, mock_fetch, mock_download, mock_filter, mock_dedup, tmp_path):
        config = _make_config(tmp_path, target_count=2)

        # Setup mock chain
        mock_fetch.return_value = [
            ImageCandidate(url="https://example.com/1.jpg", source="test", artist_name="Test"),
        ]

        # Create real temp files for download results
        img_path = tmp_path / "temp_img.jpg"
        img_path.write_bytes(b"fake image data")
        mock_download.return_value = [
            DownloadedImage(path=img_path, source="test", url="url1", width=1024, height=768),
        ]

        mock_filter.return_value = [
            FilteredImage(path=img_path, source="test", url="url1", width=1024, height=768, face_confidence=0.9),
        ]

        mock_dedup.return_value = [
            FilteredImage(path=img_path, source="test", url="url1", width=1024, height=768, face_confidence=0.9),
        ]

        result = process_person("Test Name", config)

        assert result.name == "Test Name"
        assert result.image_count == 1
        assert result.output_dir.exists()

    @patch("finder.pipeline._fetch_all_sources")
    def test_no_candidates(self, mock_fetch, tmp_path):
        config = _make_config(tmp_path)
        mock_fetch.return_value = []

        result = process_person("Unknown", config)

        assert result.image_count == 0
        assert len(result.errors) > 0

    @patch("finder.pipeline.download_all")
    @patch("finder.pipeline._fetch_all_sources")
    def test_all_downloads_fail(self, mock_fetch, mock_download, tmp_path):
        config = _make_config(tmp_path)
        mock_fetch.return_value = [
            ImageCandidate(url="https://fail.com/1.jpg", source="test", artist_name="Test"),
        ]
        mock_download.return_value = []

        result = process_person("Test", config)

        assert result.image_count == 0
        assert any("downloaded" in e.lower() for e in result.errors)


class TestProcessBatch:
    @patch("finder.pipeline.process_person")
    def test_processes_all_names(self, mock_process, tmp_path):
        config = _make_config(tmp_path)

        mock_process.return_value = PersonResult(
            name="Test", image_count=5,
            output_dir=tmp_path / "output" / "Test",
        )

        names = ["Drake", "Kendrick Lamar", "J. Cole"]
        result = process_batch(names, config)

        assert len(result.results) == 3
        assert mock_process.call_count == 3

    @patch("finder.pipeline.process_person")
    def test_deduplicates_names(self, mock_process, tmp_path):
        config = _make_config(tmp_path)

        mock_process.return_value = PersonResult(
            name="Test", image_count=5,
            output_dir=tmp_path / "output" / "Test",
        )

        names = ["Drake", "drake", "DRAKE"]
        result = process_batch(names, config)

        # Should only process once (case-insensitive dedup)
        assert mock_process.call_count == 1

    @patch("finder.pipeline.process_person")
    def test_handles_blank_lines_in_input(self, mock_process, tmp_path):
        """Names list is pre-cleaned by CLI, but batch should handle empty lists."""
        config = _make_config(tmp_path)
        result = process_batch([], config)
        assert len(result.results) == 0

    @patch("finder.pipeline.process_person")
    def test_continues_after_person_failure(self, mock_process, tmp_path):
        config = _make_config(tmp_path)

        def side_effect(name, cfg):
            if name == "Failing":
                return PersonResult(name=name, image_count=0, output_dir=tmp_path / "out" / name, errors=["Failed"])
            return PersonResult(name=name, image_count=5, output_dir=tmp_path / "out" / name)

        mock_process.side_effect = side_effect

        result = process_batch(["Drake", "Failing", "Kendrick"], config)

        assert len(result.results) == 3
        assert result.results[0].image_count == 5
        assert result.results[1].image_count == 0
        assert result.results[2].image_count == 5
