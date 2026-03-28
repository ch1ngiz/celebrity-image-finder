from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImageCandidate:
    url: str
    source: str
    artist_name: str


@dataclass
class DownloadedImage:
    path: Path
    source: str
    url: str
    width: int
    height: int


@dataclass
class FilteredImage:
    path: Path
    source: str
    url: str
    width: int
    height: int
    face_confidence: float


@dataclass
class PersonResult:
    name: str
    image_count: int
    output_dir: Path
    errors: list[str] = field(default_factory=list)


@dataclass
class BatchResult:
    results: list[PersonResult] = field(default_factory=list)
    total_images: int = 0
