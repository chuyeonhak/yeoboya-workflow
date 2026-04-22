"""Compute short SHA-256 hash (first 12 hex chars) of a PDF file."""
import hashlib
import sys
from pathlib import Path


def short_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: pdf_hash.py <pdf-path>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    print(short_hash(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
