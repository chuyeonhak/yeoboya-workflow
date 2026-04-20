import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run(*args, stdin=None):
    return subprocess.run(
        [sys.executable, *args], capture_output=True, text=True, input=stdin,
    )


def render_toggle_draft(features, missing):
    """Minimal inline renderer mirroring Phase 4 output (for test only)."""
    lines = []
    lines.append("<!-- plugin-state")
    lines.append("phase: 4")
    lines.append("pdf_hash: test")
    lines.append("source_file: t.pdf")
    lines.append("created_at: 2026-04-20T00:00:00Z")
    lines.append("publish_state: idle")
    lines.append("page_id:")
    lines.append("last_block_sentinel_id:")
    lines.append("-->")
    lines.append("")
    lines.append("# Test PDF")
    lines.append("")
    lines.append("## 피처별 상세")
    lines.append("")
    for i, f in enumerate(features["features"], 1):
        lines.append(f'### {i}. {f["name"]} ' + '{toggle="true"}')
        lines.append(f'\t<!-- feature_id: {f["feature_id"]} -->')
        lines.append(f'\t**플랫폼:** {", ".join(f["platform"])}')
        lines.append("\t")
        lines.append("\t<!-- notes_ios_start -->")
        lines.append("\t### iOS")
        lines.append("\t<empty-block/>")
        lines.append("\t<!-- notes_ios_end -->")
        lines.append("\t")
        lines.append("\t<!-- notes_android_start -->")
        lines.append("\t### Android")
        lines.append("\t<empty-block/>")
        lines.append("\t<!-- notes_android_end -->")
        lines.append("\t")
        lines.append("\t<!-- notes_common_start -->")
        lines.append("\t### 공통 질문")
        lines.append("\t<empty-block/>")
        lines.append("\t<!-- notes_common_end -->")
        short = f["feature_id"][:8]
        lines.append(f'\t<!-- publish_sentinel: feature_{short}_done -->')
        lines.append("")
    return "\n".join(lines)


def test_full_pipeline_produces_valid_chunks(tmp_path):
    # features.json with 3 features, no feature_ids yet
    features_file = tmp_path / "features.json"
    features_file.write_text(json.dumps({
        "features": [
            {"id": 1, "name": "A", "platform": ["공통"], "summary": "", "screens": [], "requirements": []},
            {"id": 2, "name": "B", "platform": ["iOS"], "summary": "", "screens": [], "requirements": []},
            {"id": 3, "name": "C", "platform": ["Android"], "summary": "", "screens": [], "requirements": []},
        ]
    }))
    missing_file = tmp_path / "missing.json"
    missing_file.write_text(json.dumps({"features": []}))

    # 1) assign feature_ids
    r = run(str(SCRIPTS_DIR / "feature_id.py"), "assign",
            "--features-file", str(features_file))
    assert r.returncode == 0, r.stderr

    features = json.loads(features_file.read_text())
    for f in features["features"]:
        assert f.get("feature_id")

    # 2) render draft
    draft = render_toggle_draft(features, {})
    draft_file = tmp_path / "draft.md"
    draft_file.write_text(draft)

    # 3) merge empty notes (should be no-op)
    notes_file = tmp_path / "notes.json"
    notes_file.write_text(json.dumps({"features": {}}))
    r = run(str(SCRIPTS_DIR / "note_merger.py"),
            "--draft", str(draft_file), "--notes", str(notes_file))
    assert r.returncode == 0, r.stderr

    # 4) chunk
    r = run(str(SCRIPTS_DIR / "page_publisher.py"), "chunk",
            "--input", str(draft_file), "--max-blocks", "100")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert len(out["chunks"]) >= 1
    for c in out["chunks"]:
        assert c["block_count"] <= 100
        assert "publish_sentinel" in c["markdown"]

    # 5) verify feature_ids survive round-trip via extract
    r = run(str(SCRIPTS_DIR / "feature_id.py"), "extract-from-stdin",
            stdin=draft)
    extracted = json.loads(r.stdout)
    expected_ids = {f["feature_id"] for f in features["features"]}
    assert set(extracted["feature_ids"]) == expected_ids
