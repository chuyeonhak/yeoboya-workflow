import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
SAMPLE = SCRIPTS_DIR / "tests" / "samples" / "minimal.pdf"


def test_pdf_hash_returns_12_char_hex():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(SAMPLE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    hash_value = result.stdout.strip()
    assert len(hash_value) == 12
    assert all(c in "0123456789abcdef" for c in hash_value)


def test_pdf_hash_deterministic():
    r1 = subprocess.run([sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(SAMPLE)], capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(SAMPLE)], capture_output=True, text=True)
    assert r1.stdout == r2.stdout


def test_pdf_hash_missing_file_exits_nonzero(tmp_path):
    missing = tmp_path / "does_not_exist.pdf"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(missing)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "not found" in result.stderr.lower() or "no such" in result.stderr.lower()
