import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent
IMAGE_ONLY = SCRIPTS_DIR / "tests" / "samples" / "image_only.pdf"


pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract not installed; OCR fallback tests skipped",
)


def test_ocr_fallback_produces_text(tmp_path):
    parse_out = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "parse_pdf.py"), str(IMAGE_ONLY), "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert parse_out.returncode == 0
    parse_data = json.loads(parse_out.stdout)
    image_paths = [img["path"] for img in parse_data["images"]]

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ocr_fallback.py"), "--images", *image_paths],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "pages" in data
    assert len(data["pages"]) == len(image_paths)
    page = data["pages"][0]
    assert set(page.keys()) >= {"page_num", "ocr_text"}
    all_text = " ".join(p["ocr_text"] for p in data["pages"]).lower()
    assert "screen" in all_text or "settings" in all_text


def test_ocr_fallback_no_tesseract_gives_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "/nonexistent")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ocr_fallback.py"), "--images", str(tmp_path / "dummy.png")],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "tesseract" in result.stderr.lower()
