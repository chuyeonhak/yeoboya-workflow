import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_pp(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "page_publisher.py"), *args],
        capture_output=True, text=True,
    )


def test_chunk_markdown_produces_chunks_under_limit(tmp_path):
    md = "\n\n".join([f"paragraph {i}" for i in range(200)])
    md_file = tmp_path / "body.md"
    md_file.write_text(md)
    r = run_pp("chunk", "--input", str(md_file), "--max-blocks", "80")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert len(out["chunks"]) >= 3
    for c in out["chunks"]:
        assert c["block_count"] <= 80


def test_chunk_appends_sentinel_per_chunk(tmp_path):
    md_file = tmp_path / "body.md"
    md_file.write_text("short body")
    r = run_pp("chunk", "--input", str(md_file), "--max-blocks", "80")
    out = json.loads(r.stdout)
    assert len(out["chunks"]) == 1
    ch = out["chunks"][0]
    assert "publish_sentinel" in ch["markdown"]
    assert "chunk_0_done" in ch["markdown"]


def test_chunk_never_splits_inside_toggle(tmp_path):
    body = """### 1. Foo {toggle="true"}
	line1
	line2
	line3
### 2. Bar {toggle="true"}
	line1
""" * 40  # guarantee multi-chunk
    md_file = tmp_path / "body.md"
    md_file.write_text(body)
    r = run_pp("chunk", "--input", str(md_file), "--max-blocks", "40")
    out = json.loads(r.stdout)
    # toggle children are tab-indented; a chunk must never start with a tab line
    for c in out["chunks"]:
        first_line = c["markdown"].splitlines()[0]
        assert not first_line.startswith("\t"), f"chunk starts mid-toggle: {first_line!r}"


def test_next_sentinel_cursor_returns_last_done(tmp_path):
    body = """
some content
<!-- publish_sentinel: chunk_0_done -->
more content
<!-- publish_sentinel: chunk_1_done -->
even more
"""
    md_file = tmp_path / "body.md"
    md_file.write_text(body)
    r = run_pp("find-sentinel", "--input", str(md_file))
    out = json.loads(r.stdout)
    assert out["last_chunk_index"] == 1


def test_next_sentinel_cursor_returns_minus_one_for_no_sentinels(tmp_path):
    md_file = tmp_path / "body.md"
    md_file.write_text("no sentinels here")
    r = run_pp("find-sentinel", "--input", str(md_file))
    out = json.loads(r.stdout)
    assert out["last_chunk_index"] == -1
