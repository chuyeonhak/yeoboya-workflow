"""Extract text and image references from a PDF.

Usage: parse_pdf.py <pdf-path> --out-dir <dir>

Output (stdout): JSON
{
  "pages": [
    {"page_num": 1, "text": "...", "has_text": true}
  ],
  "images": [
    {"page_num": 1, "idx": 0, "path": "/tmp/.../page_1_img_0.png"}
  ],
  "meta": {"total_pages": N, "encrypted": false}
}

Exit codes:
  0: success
  1: file not found or corrupt
  2: usage error
  3: pdf encrypted (no password support in v1)
"""
import argparse
import json
import sys
from pathlib import Path

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError, DependencyError
from pdf2image import convert_from_path

TEXT_MIN_CHARS = 10


def extract_pages(reader: PdfReader) -> list[dict]:
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append({
            "page_num": i,
            "text": text,
            "has_text": len(text.strip()) >= TEXT_MIN_CHARS,
        })
    return pages


def extract_page_images(pdf_path: Path, out_dir: Path, pages_info: list[dict]) -> list[dict]:
    """Render each page as PNG and return references.

    For v1 we save one image per page (not per-image in page) to keep downstream
    simple. Phase 5 can attach visual context in Notion regardless.
    """
    images = []
    try:
        pil_images = convert_from_path(str(pdf_path), dpi=150)
    except Exception as exc:
        print(f"warning: image rendering failed: {exc}", file=sys.stderr)
        return images
    for i, pil_img in enumerate(pil_images, start=1):
        img_path = out_dir / f"page_{i}_img_0.png"
        pil_img.save(img_path, "PNG")
        images.append({"page_num": i, "idx": 0, "path": str(img_path)})
    return images


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.pdf_path.is_file():
        print(f"file not found: {args.pdf_path}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(args.pdf_path))
    except PdfReadError as exc:
        print(f"failed to read pdf: {exc}", file=sys.stderr)
        return 1
    except DependencyError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 1

    if reader.is_encrypted:
        print("pdf is encrypted", file=sys.stderr)
        return 3

    pages = extract_pages(reader)
    images = extract_page_images(args.pdf_path, args.out_dir, pages)
    output = {
        "pages": pages,
        "images": images,
        "meta": {"total_pages": len(pages), "encrypted": False},
    }
    json.dump(output, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
