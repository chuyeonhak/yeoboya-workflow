"""Unit tests for enrich_features.py"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_enrich(args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "enrich_features.py"), *args],
        capture_output=True, text=True,
    )


def _write_features(tmp_path: Path) -> Path:
    p = tmp_path / "features.json"
    p.write_text(json.dumps({
        "features": [
            {"feature_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
             "name": "알림 설정", "platform": ["iOS", "Android"],
             "summary": "on/off 토글", "requirements": ["토글"],
             "excluded": False, "excluded_reason": None},
        ]
    }))
    return p


def test_load_context_truncates_at_500_lines(tmp_path):
    ctx = tmp_path / "ctx.md"
    ctx.write_text("\n".join(f"line {i}" for i in range(1000)))
    r = run_enrich(["load-context", "--path", str(ctx)])
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["truncated"] is True
    assert payload["line_count"] == 500
    assert "line 499" in payload["content"]
    assert "line 500" not in payload["content"]


def test_load_context_missing_file_reports_skip(tmp_path):
    r = run_enrich(["load-context", "--path", str(tmp_path / "nonexistent.md")])
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["skip"] is True
    assert payload["reason"] == "not_found"


def test_load_context_empty_file_reports_skip(tmp_path):
    ctx = tmp_path / "empty.md"
    ctx.write_text("   \n\n  ")
    r = run_enrich(["load-context", "--path", str(ctx)])
    payload = json.loads(r.stdout)
    assert payload["skip"] is True
    assert payload["reason"] == "empty"


def test_merge_metadata_writes_into_features_json(tmp_path):
    features = _write_features(tmp_path)
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
            "estimated_effort": "iOS 2일",
            "external_dependencies": [],
            "planning_gaps": ["gap-1"],
            "cross_team_requests": []
        }
    }))
    r = run_enrich(["merge-metadata", "--features-file", str(features), "--metadata", str(meta)])
    assert r.returncode == 0, r.stderr
    after = json.loads(features.read_text())
    feat = after["features"][0]
    assert feat["metadata"]["estimated_effort"] == "iOS 2일"
    assert feat["metadata"]["planning_gaps"] == ["gap-1"]


def test_merge_metadata_fallback_on_parse_failure(tmp_path):
    features = _write_features(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not json")
    r = run_enrich(["merge-metadata", "--features-file", str(features), "--metadata", str(bad)])
    assert r.returncode == 0, r.stderr
    after = json.loads(features.read_text())
    feat = after["features"][0]
    # fallback = empty structure, no crash
    assert feat["metadata"]["estimated_effort"] == ""
    assert feat["metadata"]["external_dependencies"] == []
    assert feat["metadata"]["planning_gaps"] == []
    assert feat["metadata"]["cross_team_requests"] == []


def test_merge_metadata_skips_excluded_features(tmp_path):
    features = tmp_path / "features.json"
    features.write_text(json.dumps({
        "features": [
            {"feature_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
             "name": "알림", "platform": ["iOS"],
             "excluded": True, "excluded_reason": "web"},
        ]
    }))
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
            "estimated_effort": "should-not-be-applied",
            "external_dependencies": [], "planning_gaps": [], "cross_team_requests": []
        }
    }))
    r = run_enrich(["merge-metadata", "--features-file", str(features), "--metadata", str(meta)])
    assert r.returncode == 0, r.stderr
    after = json.loads(features.read_text())
    # excluded feature untouched (no metadata field inserted)
    assert "metadata" not in after["features"][0]
