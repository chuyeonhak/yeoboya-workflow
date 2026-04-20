import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_mig(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "migrate_to_per_pdf.py"), *args],
        capture_output=True, text=True,
    )


def write_pages_file(tmp_path, pages):
    p = tmp_path / "pages.json"
    p.write_text(json.dumps({"pages": pages}))
    return p


def test_dry_run_groups_by_pdf_hash(tmp_path):
    pages = write_pages_file(tmp_path, [
        {
            "id": "p1", "title": "피처 A",
            "properties": {"PDF 해시": "aaa111", "원본 PDF": "spec.pdf",
                           "플랫폼": ["iOS"], "누락 항목": ["error_cases"]},
            "content": "## 개요\nalpha\n## 개발자 노트\n### iOS\nnote a\n",
            "last_edited_time": "2026-04-15T10:00:00Z",
        },
        {
            "id": "p2", "title": "피처 B",
            "properties": {"PDF 해시": "aaa111", "원본 PDF": "spec.pdf",
                           "플랫폼": ["Android"], "누락 항목": ["empty_state"]},
            "content": "## 개요\nbeta\n## 개발자 노트\n### Android\nnote b\n",
            "last_edited_time": "2026-04-15T10:00:00Z",
        },
        {
            "id": "p3", "title": "피처 C",
            "properties": {"PDF 해시": "bbb222", "원본 PDF": "other.pdf",
                           "플랫폼": ["공통"], "누락 항목": []},
            "content": "## 개요\ngamma\n",
            "last_edited_time": "2026-04-16T10:00:00Z",
        },
    ])
    report = tmp_path / "report.md"
    r = run_mig("--pages-file", str(pages), "--dry-run",
                "--report", str(report))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert len(out["groups"]) == 2
    aaa = [g for g in out["groups"] if g["pdf_hash"] == "aaa111"][0]
    assert sorted(aaa["source_page_ids"]) == ["p1", "p2"]
    assert sorted(aaa["union_platform"]) == ["Android", "iOS"]
    assert sorted(aaa["union_missing"]) == ["empty_state", "error_cases"]


def test_dry_run_writes_report(tmp_path):
    pages = write_pages_file(tmp_path, [
        {
            "id": "p1", "title": "X",
            "properties": {"PDF 해시": "h1", "원본 PDF": "x.pdf", "플랫폼": ["iOS"], "누락 항목": []},
            "content": "", "last_edited_time": "2026-04-15T10:00:00Z",
        }
    ])
    report = tmp_path / "report.md"
    run_mig("--pages-file", str(pages), "--dry-run", "--report", str(report))
    content = report.read_text()
    assert "h1" in content
    assert "x.pdf" in content


def test_dry_run_flags_orphans_when_no_hash_and_no_filename(tmp_path):
    pages = write_pages_file(tmp_path, [
        {
            "id": "p1", "title": "orphan",
            "properties": {"PDF 해시": "", "원본 PDF": "", "플랫폼": [], "누락 항목": []},
            "content": "", "last_edited_time": "2026-04-15T10:00:00Z",
        }
    ])
    report = tmp_path / "report.md"
    r = run_mig("--pages-file", str(pages), "--dry-run", "--report", str(report))
    out = json.loads(r.stdout)
    assert len(out["orphans"]) == 1
    assert out["orphans"][0]["id"] == "p1"


def test_dry_run_uses_filename_fallback_for_missing_hash(tmp_path):
    pages = write_pages_file(tmp_path, [
        {
            "id": "p1", "title": "A",
            "properties": {"PDF 해시": "", "원본 PDF": "shared.pdf",
                           "플랫폼": ["iOS"], "누락 항목": []},
            "content": "", "last_edited_time": "2026-04-15T10:00:00Z",
        },
        {
            "id": "p2", "title": "B",
            "properties": {"PDF 해시": "", "원본 PDF": "shared.pdf",
                           "플랫폼": ["Android"], "누락 항목": []},
            "content": "", "last_edited_time": "2026-04-15T10:30:00Z",
        },
    ])
    report = tmp_path / "report.md"
    r = run_mig("--pages-file", str(pages), "--dry-run", "--report", str(report))
    out = json.loads(r.stdout)
    groups = [g for g in out["groups"] if g.get("match_mode") == "filename+date"]
    assert len(groups) == 1
    assert sorted(groups[0]["source_page_ids"]) == ["p1", "p2"]


def test_dry_run_skips_archived_pages(tmp_path):
    pages = write_pages_file(tmp_path, [
        {
            "id": "p1", "title": "X",
            "properties": {"PDF 해시": "h1", "원본 PDF": "x.pdf",
                           "플랫폼": [], "누락 항목": [], "archived": True},
            "content": "", "last_edited_time": "2026-04-15T10:00:00Z",
        }
    ])
    report = tmp_path / "report.md"
    r = run_mig("--pages-file", str(pages), "--dry-run", "--report", str(report))
    out = json.loads(r.stdout)
    assert out["groups"] == []
    assert out["skipped_archived"] == 1
