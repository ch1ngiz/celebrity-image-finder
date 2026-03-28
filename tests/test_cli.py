import os
from pathlib import Path
from unittest.mock import patch

import pytest

from finder.cli import parse_args


def test_parse_args_with_all_flags():
    args = parse_args(["--input", "names.txt", "--output", "out", "--count", "40", "--min-resolution", "256"])
    assert args.input == Path("names.txt")
    assert args.output == Path("out")
    assert args.count == 40
    assert args.min_resolution == 256


def test_parse_args_defaults():
    args = parse_args(["--input", "names.txt"])
    assert args.input == Path("names.txt")
    assert args.output == Path("output")
    assert args.count == 50
    assert args.min_resolution == 512


def test_parse_args_short_flags():
    args = parse_args(["-i", "names.txt", "-o", "out", "-c", "30"])
    assert args.input == Path("names.txt")
    assert args.output == Path("out")
    assert args.count == 30


def test_parse_args_missing_input():
    with pytest.raises(SystemExit):
        parse_args([])


def test_config_loads_env_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GENIUS_TOKEN=test_genius\n"
        "SPOTIFY_CLIENT_ID=test_id\n"
        "SPOTIFY_CLIENT_SECRET=test_secret\n"
    )
    from finder.config import load_config

    with patch.dict(os.environ, {
        "GENIUS_TOKEN": "test_genius",
        "SPOTIFY_CLIENT_ID": "test_id",
        "SPOTIFY_CLIENT_SECRET": "test_secret",
    }):
        config = load_config(input_file=tmp_path / "names.txt")
        assert config.genius_token == "test_genius"
        assert config.spotify_client_id == "test_id"
        assert config.spotify_client_secret == "test_secret"
        assert config.target_count == 50
        assert config.min_resolution == 512


def test_config_missing_keys():
    with patch("finder.config.load_dotenv"):  # Prevent .env from being loaded
        with patch.dict(os.environ, {}, clear=True):
            from finder.config import load_config
            with pytest.raises(SystemExit):
                load_config(input_file=Path("names.txt"))
