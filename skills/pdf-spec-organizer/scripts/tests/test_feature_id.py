import json
import subprocess
import sys
import uuid
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_fid(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "feature_id.py"), *args],
        capture_output=True,
        text=True,
    )


def test_assign_generates_uuid4_for_new_features(tmp_path):
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({
        "features": [
            {"id": 1, "name": "A", "platform": ["공통"], "summary": "", "screens": [], "requirements": []},
            {"id": 2, "name": "B", "platform": ["공통"], "summary": "", "screens": [], "requirements": []},
        ]
    }))
    r = run_fid("assign", "--features-file", str(features_file))
    assert r.returncode == 0, r.stderr
    data = json.loads(features_file.read_text())
    for f in data["features"]:
        assert "feature_id" in f
        uuid.UUID(f["feature_id"])  # validates format


def test_assign_preserves_existing_ids(tmp_path):
    existing = "11111111-1111-4111-8111-111111111111"
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({
        "features": [
            {"id": 1, "name": "A", "feature_id": existing,
             "platform": ["공통"], "summary": "", "screens": [], "requirements": []}
        ]
    }))
    run_fid("assign", "--features-file", str(features_file))
    data = json.loads(features_file.read_text())
    assert data["features"][0]["feature_id"] == existing


def test_resolve_by_name_exact_match(tmp_path):
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({
        "features": [
            {"id": 1, "name": "로그인 유도 팝업(A/B)",
             "feature_id": "abc11111-1111-4111-8111-111111111111",
             "platform": ["공통"], "summary": "", "screens": [], "requirements": []}
        ]
    }))
    r = run_fid("resolve", "--features-file", str(features_file),
                "--name", "로그인 유도 팝업(A/B)")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["feature_id"] == "abc11111-1111-4111-8111-111111111111"


def test_resolve_case_insensitive(tmp_path):
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({
        "features": [
            {"id": 1, "name": "Feature Alpha",
             "feature_id": "abc11111-1111-4111-8111-111111111111",
             "platform": ["공통"], "summary": "", "screens": [], "requirements": []}
        ]
    }))
    r = run_fid("resolve", "--features-file", str(features_file), "--name", "feature alpha")
    out = json.loads(r.stdout)
    assert out["feature_id"] == "abc11111-1111-4111-8111-111111111111"


def test_resolve_no_match_returns_error(tmp_path):
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({"features": []}))
    r = run_fid("resolve", "--features-file", str(features_file), "--name", "missing")
    assert r.returncode != 0
    assert "not found" in r.stderr.lower()


def test_resolve_ambiguous_lists_candidates(tmp_path):
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({
        "features": [
            {"id": 1, "name": "Foo",
             "feature_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
             "platform": [], "summary": "", "screens": [], "requirements": []},
            {"id": 2, "name": "Foo",
             "feature_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
             "platform": [], "summary": "", "screens": [], "requirements": []},
        ]
    }))
    r = run_fid("resolve", "--features-file", str(features_file), "--name", "Foo")
    assert r.returncode != 0
    assert "ambiguous" in r.stderr.lower()
    assert "aaaaaaaa" in r.stderr
    assert "bbbbbbbb" in r.stderr


def test_extract_from_content_finds_markers():
    content = """
## 피처별 상세
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

### 2. Bar
<!-- feature_id: bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb -->
body
"""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "feature_id.py"), "extract-from-stdin"],
        input=content, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert set(out["feature_ids"]) == {
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    }
