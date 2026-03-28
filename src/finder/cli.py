import argparse
import sys
from pathlib import Path

from finder.config import load_config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="finder",
        description="Find and download high-quality face images of celebrities.",
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        help="Path to text file with one name per line",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("output"),
        help="Output directory for downloaded images (default: output/)",
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=50,
        help="Target number of images per person (default: 50)",
    )
    parser.add_argument(
        "--min-resolution",
        type=int,
        default=512,
        help="Minimum resolution on shortest side in pixels (default: 512)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    config = load_config(
        input_file=args.input,
        output_dir=args.output,
        target_count=args.count,
        min_resolution=args.min_resolution,
    )

    from finder.pipeline import process_batch

    names = [
        line.strip()
        for line in config.input_file.read_text().splitlines()
        if line.strip()
    ]

    if not names:
        print("Error: Input file is empty or contains only blank lines.", file=sys.stderr)
        sys.exit(1)

    process_batch(names, config)


if __name__ == "__main__":
    main()
