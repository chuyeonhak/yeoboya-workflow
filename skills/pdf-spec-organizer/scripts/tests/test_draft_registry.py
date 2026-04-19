import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_reg(*args, registry_path):
    env_args = ["--registry", str(registry_path)]
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "draft_registry.py"), *args, *env_args],
        capture_output=True,
        text=True,
    )


def test_record_and_query_recent(tmp_path):
    reg = tmp_path / "registry.json"
    r = run_reg("record", "--hash", "abc123", "--draft-path", str(tmp_path / "d.md"), "--status", "running", registry_path=reg)
    assert r.returncode == 0, r.stderr

    r2 = run_reg("query-recent", "--hash", "abc123", "--within-seconds", "300", registry_path=reg)
    assert r2.returncode == 0
    data = json.loads(r2.stdout)
    assert data["found"] is True
    assert data["entry"]["hash"] == "abc123"


def test_query_recent_expired(tmp_path):
    reg = tmp_path / "registry.json"
    run_reg("record", "--hash", "xyz", "--draft-path", "/tmp/x.md", "--status", "running", registry_path=reg)
    time.sleep(2)
    r = run_reg("query-recent", "--hash", "xyz", "--within-seconds", "1", registry_path=reg)
    data = json.loads(r.stdout)
    assert data["found"] is False


def test_list_latest(tmp_path):
    reg = tmp_path / "registry.json"
    run_reg("record", "--hash", "h1", "--draft-path", "/tmp/1.md", "--status", "failed", registry_path=reg)
    time.sleep(0.1)
    run_reg("record", "--hash", "h2", "--draft-path", "/tmp/2.md", "--status", "running", registry_path=reg)
    r = run_reg("list-latest", "--count", "5", registry_path=reg)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert len(data["entries"]) == 2
    assert data["entries"][0]["hash"] == "h2"


def test_gc_removes_expired(tmp_path):
    reg = tmp_path / "registry.json"
    run_reg("record", "--hash", "old", "--draft-path", "/tmp/old.md", "--status", "success", "--ttl-seconds", "1", registry_path=reg)
    time.sleep(2)
    r = run_reg("gc", registry_path=reg)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["removed"] >= 1

    r2 = run_reg("list-latest", "--count", "5", registry_path=reg)
    assert json.loads(r2.stdout)["entries"] == []
