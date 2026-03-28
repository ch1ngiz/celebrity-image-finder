import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    input_file: Path
    output_dir: Path
    target_count: int
    min_resolution: int
    genius_token: str
    spotify_client_id: str
    spotify_client_secret: str


def load_config(
    input_file: Path,
    output_dir: Path = Path("output"),
    target_count: int = 50,
    min_resolution: int = 512,
) -> Config:
    load_dotenv()

    genius_token = os.getenv("GENIUS_TOKEN", "")
    spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
    spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")

    missing = []
    if not genius_token:
        missing.append("GENIUS_TOKEN")
    if not spotify_client_id:
        missing.append("SPOTIFY_CLIENT_ID")
    if not spotify_client_secret:
        missing.append("SPOTIFY_CLIENT_SECRET")

    if missing:
        print(
            f"Error: Missing API keys in .env file: {', '.join(missing)}",
            file=sys.stderr,
        )
        print("See .env.example for required keys.", file=sys.stderr)
        sys.exit(1)

    return Config(
        input_file=input_file,
        output_dir=output_dir,
        target_count=target_count,
        min_resolution=min_resolution,
        genius_token=genius_token,
        spotify_client_id=spotify_client_id,
        spotify_client_secret=spotify_client_secret,
    )
