import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
MINIMAL = SCRIPTS_DIR / "tests" / "samples" / "minimal.pdf"
IMAGE_ONLY = SCRIPTS_DIR / "tests" / "samples" / "image_only.pdf"


def run_parse(pdf_path: Path, out_dir: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "parse_pdf.py"), str(pdf_path), "--out-dir", str(out_dir)],
        capture_output=True,
        text=True,
    )


def test_parse_pdf_outputs_json_with_pages(tmp_path):
    result = run_parse(MINIMAL, tmp_path)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "pages" in data
    assert isinstance(data["pages"], list)
    assert len(data["pages"]) >= 1
    page = data["pages"][0]
    assert set(page.keys()) >= {"page_num", "text", "has_text"}
    assert "Notification" in page["text"] or "notification" in page["text"].lower()
    assert page["has_text"] is True


def test_parse_pdf_image_only_pdf_has_text_false(tmp_path):
    result = run_parse(IMAGE_ONLY, tmp_path)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    if data["pages"]:
        assert not data["pages"][0]["text"].strip() or data["pages"][0]["has_text"] is False


def test_parse_pdf_missing_file_exits_nonzero(tmp_path):
    missing = tmp_path / "missing.pdf"
    result = run_parse(missing, tmp_path)
    assert result.returncode != 0
