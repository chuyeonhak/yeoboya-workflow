"""Run Tesseract OCR on a list of images.

Usage: ocr_fallback.py --images <img1> <img2> ...

Output (stdout): JSON
{ "pages": [{"page_num": N, "ocr_text": "...", "source_image": "path"}] }

Exit codes:
  0: success
  1: tesseract not found or OCR failed
  2: usage error
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import pytesseract
from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", nargs="+", required=True, type=Path)
    parser.add_argument("--lang", default="eng+kor", help="Tesseract languages")
    args = parser.parse_args()

    if shutil.which("tesseract") is None:
        print(
            "tesseract not found. Install: 'brew install tesseract tesseract-lang' (macOS)",
            file=sys.stderr,
        )
        return 1

    pages = []
    for page_num, img_path in enumerate(args.images, start=1):
        if not img_path.is_file():
            print(f"warning: image not found: {img_path}", file=sys.stderr)
            pages.append({"page_num": page_num, "ocr_text": "", "source_image": str(img_path)})
            continue
        try:
            text = pytesseract.image_to_string(Image.open(img_path), lang=args.lang)
        except pytesseract.TesseractError as exc:
            print(f"ocr failed for {img_path}: {exc}", file=sys.stderr)
            return 1
        pages.append({"page_num": page_num, "ocr_text": text.strip(), "source_image": str(img_path)})

    json.dump({"pages": pages}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
