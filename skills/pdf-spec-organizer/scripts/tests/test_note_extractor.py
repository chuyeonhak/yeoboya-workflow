import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_ext(stdin_text):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "note_extractor.py")],
        input=stdin_text, capture_output=True, text=True,
    )


FEATURE_BODY = """
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
Overview stuff.

<!-- notes_ios_start -->
### iOS
- ios note line 1
- ios note line 2
<!-- notes_ios_end -->

<!-- notes_android_start -->
### Android
<!-- notes_android_end -->

<!-- notes_common_start -->
### 공통 질문
Common note.
<!-- notes_common_end -->

<!-- publish_sentinel: feature_aaaaaaaa_done -->
"""


def test_extract_returns_notes_by_feature_id():
    r = run_ext(FEATURE_BODY)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    fid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    assert fid in out["features"]
    feat = out["features"][fid]
    assert "ios note line 1" in feat["ios"]
    assert "ios note line 2" in feat["ios"]
    assert feat["android"].strip() == "### Android"
    assert "Common note" in feat["common"]


def test_extract_handles_missing_sections():
    content = """
<!-- feature_id: bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb -->
<!-- notes_ios_start -->
only ios
<!-- notes_ios_end -->
"""
    r = run_ext(content)
    out = json.loads(r.stdout)
    feat = out["features"]["bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"]
    assert "only ios" in feat["ios"]
    assert feat["android"] == ""
    assert feat["common"] == ""


def test_extract_handles_multiple_features():
    content = """
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
<!-- notes_ios_start -->
A-ios
<!-- notes_ios_end -->

<!-- feature_id: bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb -->
<!-- notes_ios_start -->
B-ios
<!-- notes_ios_end -->
"""
    r = run_ext(content)
    out = json.loads(r.stdout)
    assert len(out["features"]) == 2
    assert "A-ios" in out["features"]["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]["ios"]
    assert "B-ios" in out["features"]["bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"]["ios"]


def test_extract_strips_empty_notes():
    content = """
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
<!-- notes_ios_start -->
<empty-block/>
<!-- notes_ios_end -->
"""
    r = run_ext(content)
    out = json.loads(r.stdout)
    feat = out["features"]["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    assert feat["ios"].strip() == ""
    assert feat.get("ios_empty") is True


def test_extract_returns_stray_blocks():
    content = """
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
Overview line.

Stray line that is not inside any notes marker.

<!-- notes_ios_start -->
ios stuff
<!-- notes_ios_end -->

Trailing stray line.

<!-- publish_sentinel: feature_aaaaaaaa_done -->
"""
    r = run_ext(content)
    out = json.loads(r.stdout)
    feat = out["features"]["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    assert "Trailing stray line" in feat["stray"]
