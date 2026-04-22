import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_pii(text: str):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pii_scan.py")],
        input=text,
        capture_output=True,
        text=True,
    )


def test_detects_email():
    r = run_pii("contact: user.name+tag@example.com for details")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    categories = {f["category"] for f in data["findings"]}
    assert "email" in categories


def test_detects_kr_phone():
    r = run_pii("전화: 010-1234-5678")
    data = json.loads(r.stdout)
    categories = {f["category"] for f in data["findings"]}
    assert "phone" in categories


def test_detects_kr_rrn():
    r = run_pii("주민번호: 900101-1234567")
    data = json.loads(r.stdout)
    categories = {f["category"] for f in data["findings"]}
    assert "rrn" in categories


def test_clean_text_returns_empty_findings():
    r = run_pii("This is a normal feature spec with no personal info.")
    data = json.loads(r.stdout)
    assert data["findings"] == []


def test_masks_sample_in_output():
    r = run_pii("contact: verylongemail.address@example.com")
    data = json.loads(r.stdout)
    sample = data["findings"][0]["sample"]
    assert "*" in sample or "..." in sample
    assert "verylongemail.address@example.com" != sample
