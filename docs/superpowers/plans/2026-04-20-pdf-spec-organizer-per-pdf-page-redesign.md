# pdf-spec-organizer Per-PDF Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `pdf-spec-organizer` skill so one PDF becomes one Notion page with features as Toggle blocks, preserving user notes across re-runs, supporting chunked publish, and migrating legacy per-feature pages.

**Architecture:** 5-Phase flow preserved. Phase 4/5 gain toggle-based rendering, chunked Notion publish with sentinel markers, and note-preserving merge by stable `feature_id`. New scripts isolate concerns (feature_id, note extract/merge, publisher, migrator). `draft_registry` gains `page_id`/`publish_state` fields. Slash commands `/spec-update` and `/spec-resume` get new flags and guards.

**Tech Stack:** Python 3.13, pytest, PyYAML, PyPDF2/pdf2image (unchanged), Notion MCP tools (`notion-create-pages`, `notion-update-page`, `notion-fetch`, `notion-search`, `notion-update-data-source`).

**Reference spec:** `docs/superpowers/specs/2026-04-20-pdf-spec-organizer-per-pdf-page-redesign-design.md`

---

## File Structure

### New files

- `skills/pdf-spec-organizer/scripts/feature_id.py` — UUID4 generation, persistence to features.json, name→id resolver.
- `skills/pdf-spec-organizer/scripts/note_extractor.py` — parse `<!-- notes_*_start/end -->` blocks from Notion page body.
- `skills/pdf-spec-organizer/scripts/note_merger.py` — merge extracted notes into new draft toggles by feature_id.
- `skills/pdf-spec-organizer/scripts/page_publisher.py` — chunked append with sentinel markers + exponential backoff on rate limit.
- `skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py` — one-time consolidation of legacy per-feature pages.
- `skills/pdf-spec-organizer/scripts/tests/test_feature_id.py`
- `skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py`
- `skills/pdf-spec-organizer/scripts/tests/test_note_merger.py`
- `skills/pdf-spec-organizer/scripts/tests/test_page_publisher.py`
- `skills/pdf-spec-organizer/scripts/tests/test_migrate_to_per_pdf.py`

### Modified files

- `skills/pdf-spec-organizer/SKILL.md` — Phase 4, Phase 5, Update mode, Resume mode sections.
- `skills/pdf-spec-organizer/references/review-format.md` — draft.md format v2 (toggles + markers).
- `skills/pdf-spec-organizer/references/conflict-policy.md` — new dedup/merge flow, Relation semantics.
- `skills/pdf-spec-organizer/scripts/draft_registry.py` — `page_id`/`publish_state` fields, `partial_success` status, GC policy.
- `skills/pdf-spec-organizer/scripts/tests/test_draft_registry.py` — new fields, statuses.
- `commands/spec-update.md` — `--feature=` flag, root guard, description.
- `commands/spec-resume.md` — root guard, description.

### Unchanged

- `skills/pdf-spec-organizer/scripts/pdf_hash.py`, `parse_pdf.py`, `ocr_fallback.py`, `pii_scan.py`.
- Phase 1, 2, 3 logic (feature extraction + missing checks).

---

## Task 1: Extend `draft_registry.py` schema with `page_id`, `publish_state`, `partial_success`

**Files:**
- Modify: `skills/pdf-spec-organizer/scripts/draft_registry.py`
- Test: `skills/pdf-spec-organizer/scripts/tests/test_draft_registry.py`

- [ ] **Step 1: Write failing test for `partial_success` status**

Add to `test_draft_registry.py`:

```python
def test_record_partial_success_status(tmp_path):
    reg = tmp_path / "registry.json"
    r = run_reg(
        "record", "--hash", "pp1", "--draft-path", "/tmp/pp1.md",
        "--status", "partial_success",
        registry_path=reg,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(reg.read_text())
    assert data["entries"][0]["status"] == "partial_success"


def test_record_with_page_id_and_publish_state(tmp_path):
    reg = tmp_path / "registry.json"
    r = run_reg(
        "record", "--hash", "h", "--draft-path", "/tmp/h.md",
        "--status", "running",
        "--page-id", "abcdef1234",
        "--publish-state", "chunks_appending",
        registry_path=reg,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(reg.read_text())
    assert data["entries"][0]["page_id"] == "abcdef1234"
    assert data["entries"][0]["publish_state"] == "chunks_appending"


def test_update_status_updates_publish_state(tmp_path):
    reg = tmp_path / "registry.json"
    run_reg(
        "record", "--hash", "h", "--draft-path", "/tmp/h.md", "--status", "running",
        "--page-id", "p1", "--publish-state", "page_created",
        registry_path=reg,
    )
    r = run_reg(
        "update-status", "--draft-path", "/tmp/h.md",
        "--status", "partial_success",
        "--publish-state", "chunks_appending",
        registry_path=reg,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(reg.read_text())
    assert data["entries"][0]["status"] == "partial_success"
    assert data["entries"][0]["publish_state"] == "chunks_appending"


def test_partial_success_ttl_longer_than_success(tmp_path):
    reg = tmp_path / "registry.json"
    run_reg(
        "record", "--hash", "p", "--draft-path", "/tmp/p.md",
        "--status", "partial_success", registry_path=reg,
    )
    data = json.loads(reg.read_text())
    # partial_success must be retained at least 3 days
    assert data["entries"][0]["ttl_seconds"] >= 3 * 86400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_draft_registry.py -v`
Expected: 4 new tests FAIL (status choice rejection or missing flags).

- [ ] **Step 3: Extend `draft_registry.py`**

Replace the `ttl_for` function and all places that accept `--status` / parse status choices. Full diff:

```python
VALID_STATUSES = ["running", "success", "failed", "partial_success"]
VALID_PUBLISH_STATES = ["idle", "page_created", "chunks_appending", "complete", "failed"]


def ttl_for(status: str) -> int:
    return {
        "success": 3 * 86400,
        "failed": 7 * 86400,
        "running": 7 * 86400,
        "partial_success": 7 * 86400,  # longer retention so /spec-resume can find it
    }.get(status, 7 * 86400)
```

In `cmd_record`:

```python
def cmd_record(args) -> int:
    data = load(args.registry)
    ttl = args.ttl_seconds if args.ttl_seconds is not None else ttl_for(args.status)
    entry = {
        "hash": args.hash,
        "draft_path": args.draft_path,
        "status": args.status,
        "created_at": time.time(),
        "ttl_seconds": ttl,
    }
    if args.page_id:
        entry["page_id"] = args.page_id
    if args.publish_state:
        entry["publish_state"] = args.publish_state
    data["entries"].append(entry)
    save(args.registry, data)
    json.dump({"recorded": True, "entry": entry}, sys.stdout)
    return 0
```

In `cmd_update_status`:

```python
def cmd_update_status(args) -> int:
    data = load(args.registry)
    updated = 0
    for e in data["entries"]:
        if e["draft_path"] == args.draft_path:
            e["status"] = args.status
            e["ttl_seconds"] = ttl_for(args.status)
            if args.publish_state:
                e["publish_state"] = args.publish_state
            if args.page_id:
                e["page_id"] = args.page_id
            updated += 1
    save(args.registry, data)
    json.dump({"updated": updated}, sys.stdout)
    return 0
```

In `main`, update `p_rec` and `p_u` to accept the new flags:

```python
    p_rec = sub.add_parser("record", parents=[common])
    p_rec.add_argument("--hash", required=True)
    p_rec.add_argument("--draft-path", required=True)
    p_rec.add_argument("--status", required=True, choices=VALID_STATUSES)
    p_rec.add_argument("--ttl-seconds", type=int, default=None)
    p_rec.add_argument("--page-id", default=None)
    p_rec.add_argument("--publish-state", default=None, choices=VALID_PUBLISH_STATES)
    p_rec.set_defaults(func=cmd_record)

    p_u = sub.add_parser("update-status", parents=[common])
    p_u.add_argument("--draft-path", required=True)
    p_u.add_argument("--status", required=True, choices=VALID_STATUSES)
    p_u.add_argument("--publish-state", default=None, choices=VALID_PUBLISH_STATES)
    p_u.add_argument("--page-id", default=None)
    p_u.set_defaults(func=cmd_update_status)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_draft_registry.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/pdf-spec-organizer/scripts/draft_registry.py skills/pdf-spec-organizer/scripts/tests/test_draft_registry.py
git commit -m "feat(registry): add page_id, publish_state fields and partial_success status"
```

---

## Task 2: Add `feature_id.py` — UUID4 generation and name resolution

**Files:**
- Create: `skills/pdf-spec-organizer/scripts/feature_id.py`
- Test: `skills/pdf-spec-organizer/scripts/tests/test_feature_id.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_feature_id.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_feature_id.py -v`
Expected: all FAIL with "No such file or directory" or equivalent.

- [ ] **Step 3: Create `feature_id.py`**

Create `skills/pdf-spec-organizer/scripts/feature_id.py`:

```python
"""Feature ID generation and resolution.

Subcommands:
  assign            --features-file PATH
                    Assign UUID4 feature_id to every feature missing one.
  resolve           --features-file PATH --name NAME
                    Resolve a feature name (case-insensitive) to its feature_id.
                    Exits non-zero on no-match or ambiguous match.
  extract-from-stdin
                    Read markdown from stdin, extract all
                    <!-- feature_id: <uuid> --> values, print as JSON list.
"""
import argparse
import json
import re
import sys
import uuid
from pathlib import Path

FEATURE_ID_MARKER_RE = re.compile(
    r"<!--\s*feature_id:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*-->"
)


def cmd_assign(args) -> int:
    path = Path(args.features_file)
    data = json.loads(path.read_text())
    changed = False
    for f in data.get("features", []):
        if not f.get("feature_id"):
            f["feature_id"] = str(uuid.uuid4())
            changed = True
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    json.dump({"changed": changed}, sys.stdout)
    return 0


def cmd_resolve(args) -> int:
    path = Path(args.features_file)
    data = json.loads(path.read_text())
    target = args.name.strip().lower()
    matches = [
        f for f in data.get("features", [])
        if f.get("name", "").strip().lower() == target
    ]
    if not matches:
        print(f"ERROR: feature name not found: {args.name!r}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        lines = ["ERROR: ambiguous name; candidates:"]
        for m in matches:
            lines.append(f"  {m.get('feature_id', '<no-id>')}  {m.get('name')}")
        print("\n".join(lines), file=sys.stderr)
        return 1
    f = matches[0]
    json.dump({"feature_id": f["feature_id"], "name": f["name"]}, sys.stdout)
    return 0


def cmd_extract_from_stdin(args) -> int:
    text = sys.stdin.read()
    ids = FEATURE_ID_MARKER_RE.findall(text)
    json.dump({"feature_ids": ids}, sys.stdout)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_a = sub.add_parser("assign")
    p_a.add_argument("--features-file", required=True)
    p_a.set_defaults(func=cmd_assign)

    p_r = sub.add_parser("resolve")
    p_r.add_argument("--features-file", required=True)
    p_r.add_argument("--name", required=True)
    p_r.set_defaults(func=cmd_resolve)

    p_e = sub.add_parser("extract-from-stdin")
    p_e.set_defaults(func=cmd_extract_from_stdin)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_feature_id.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/pdf-spec-organizer/scripts/feature_id.py skills/pdf-spec-organizer/scripts/tests/test_feature_id.py
git commit -m "feat(scripts): add feature_id generator and name resolver"
```

---

## Task 3: Add `note_extractor.py` — parse notes markers from Notion content

**Files:**
- Create: `skills/pdf-spec-organizer/scripts/note_extractor.py`
- Test: `skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_note_extractor.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_note_extractor.py -v`
Expected: all FAIL.

- [ ] **Step 3: Create `note_extractor.py`**

```python
"""Extract user-authored notes from a Notion PDF-page's markdown body.

Reads markdown from stdin. For every feature_id marker, locates its notes_ios,
notes_android, notes_common start/end blocks, and any stray (non-marker) content
between the feature start and the next feature/sentinel.

Output JSON:
{
  "features": {
    "<feature_id>": {
      "ios": "...", "ios_empty": bool,
      "android": "...", "android_empty": bool,
      "common": "...", "common_empty": bool,
      "stray": "..."
    }
  }
}
"""
import json
import re
import sys

FEATURE_ID_RE = re.compile(
    r"<!--\s*feature_id:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*-->"
)
SENTINEL_RE = re.compile(r"<!--\s*publish_sentinel:[^>]*-->")

SECTION_NAMES = ("ios", "android", "common")


def _section_re(name: str) -> re.Pattern:
    return re.compile(
        rf"<!--\s*notes_{name}_start\s*-->(.*?)<!--\s*notes_{name}_end\s*-->",
        re.DOTALL,
    )


def _is_empty(text: str) -> bool:
    stripped = re.sub(r"<empty-block/>", "", text).strip()
    stripped = re.sub(r"^#+\s.*$", "", stripped, flags=re.MULTILINE).strip()
    return stripped == ""


def _strip_known_blocks(segment: str) -> str:
    out = segment
    for name in SECTION_NAMES:
        out = _section_re(name).sub("", out)
    out = SENTINEL_RE.sub("", out)
    out = FEATURE_ID_RE.sub("", out)
    return out.strip()


def extract(text: str) -> dict:
    result = {"features": {}}
    # Split body into chunks at each feature_id marker
    positions = [(m.start(), m.group(1)) for m in FEATURE_ID_RE.finditer(text)]
    positions.append((len(text), None))  # sentinel

    for i in range(len(positions) - 1):
        start, fid = positions[i]
        end = positions[i + 1][0]
        segment = text[start:end]
        feat = {}
        for name in SECTION_NAMES:
            m = _section_re(name).search(segment)
            content = m.group(1).strip() if m else ""
            feat[name] = content
            feat[f"{name}_empty"] = _is_empty(content)
        # stray = everything except feature_id marker, note sections, sentinels, and the first line after feature_id
        stray = _strip_known_blocks(segment)
        feat["stray"] = stray
        result["features"][fid] = feat
    return result


def main() -> int:
    text = sys.stdin.read()
    json.dump(extract(text), sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_note_extractor.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/pdf-spec-organizer/scripts/note_extractor.py skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py
git commit -m "feat(scripts): add note_extractor to parse notes by feature_id from Notion body"
```

---

## Task 4: Add `note_merger.py` — merge extracted notes into new draft

**Files:**
- Create: `skills/pdf-spec-organizer/scripts/note_merger.py`
- Test: `skills/pdf-spec-organizer/scripts/tests/test_note_merger.py`

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_note_merger.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_merge(draft_path, notes_path):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "note_merger.py"),
         "--draft", str(draft_path), "--notes", str(notes_path)],
        capture_output=True, text=True,
    )


def test_merge_injects_preserved_notes_into_matching_feature(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- notes_ios_start -->
<empty-block/>
<!-- notes_ios_end -->

<!-- notes_android_start -->
<empty-block/>
<!-- notes_android_end -->

<!-- notes_common_start -->
<empty-block/>
<!-- notes_common_end -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                "ios": "preserved iOS text", "ios_empty": False,
                "android": "", "android_empty": True,
                "common": "preserved common", "common_empty": False,
                "stray": "",
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "preserved iOS text" in merged
    assert "preserved common" in merged
    # empty sections stay as <empty-block/> placeholder
    assert merged.count("<empty-block/>") == 1  # only android remains empty


def test_merge_orphans_preserved_notes_for_removed_features(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "ccccccccc-cccc-4ccc-8ccc-cccccccccccc": {
                "ios": "orphan iOS note", "ios_empty": False,
                "android": "", "android_empty": True,
                "common": "", "common_empty": True,
                "stray": "",
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "이전 노트" in merged
    assert "orphan iOS note" in merged


def test_merge_preserves_stray_blocks_at_toggle_tail(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- notes_ios_start -->
<empty-block/>
<!-- notes_ios_end -->

<!-- notes_android_start -->
<empty-block/>
<!-- notes_android_end -->

<!-- notes_common_start -->
<empty-block/>
<!-- notes_common_end -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                "ios": "", "ios_empty": True,
                "android": "", "android_empty": True,
                "common": "", "common_empty": True,
                "stray": "manual user addition",
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "<!-- stray: preserved -->" in merged
    assert "manual user addition" in merged
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_note_merger.py -v`
Expected: all FAIL.

- [ ] **Step 3: Create `note_merger.py`**

```python
"""Merge extracted notes into a draft.md so user-authored content is preserved.

Usage:
  note_merger.py --draft DRAFT_PATH --notes NOTES_JSON_PATH

Rewrites DRAFT_PATH in place:
  - For each feature_id present in both notes and draft:
    - Replace notes_ios / notes_android / notes_common sections with preserved
      text (if not empty). Empty sections stay as <empty-block/> placeholder.
  - Append stray content at end of matching toggle under a
    <!-- stray: preserved --> wrapper.
  - feature_ids present in notes but missing from draft → append an
    "이전 노트 (제거된 피처)" section at end of file with preserved text.
"""
import argparse
import json
import re
from pathlib import Path

SECTION_NAMES = ("ios", "android", "common")


def _replace_section(segment: str, name: str, new_inner: str) -> str:
    pat = re.compile(
        rf"(<!--\s*notes_{name}_start\s*-->)(.*?)(<!--\s*notes_{name}_end\s*-->)",
        re.DOTALL,
    )
    replacement = f"\\1\n{new_inner}\n\\3" if new_inner.strip() else "\\1\n<empty-block/>\n\\3"
    return pat.sub(replacement, segment, count=1)


def _find_feature_positions(text: str):
    fid_re = re.compile(
        r"<!--\s*feature_id:\s*([0-9a-fA-F-]{36})\s*-->"
    )
    return [(m.start(), m.end(), m.group(1)) for m in fid_re.finditer(text)]


def merge(draft: str, notes: dict) -> str:
    positions = _find_feature_positions(draft)
    positions_sorted = sorted(positions, key=lambda p: p[0])
    segments = []
    last = 0
    for i, (start, end, fid) in enumerate(positions_sorted):
        prev_text = draft[last:start]
        next_start = positions_sorted[i + 1][0] if i + 1 < len(positions_sorted) else len(draft)
        feat_segment = draft[start:next_start]
        n = notes.get("features", {}).get(fid)
        if n:
            for name in SECTION_NAMES:
                if not n.get(f"{name}_empty", True):
                    feat_segment = _replace_section(feat_segment, name, n[name])
            if n.get("stray", "").strip():
                # Append stray at the very end of the feature segment
                feat_segment = feat_segment.rstrip() + (
                    "\n\n<!-- stray: preserved -->\n" + n["stray"].strip() + "\n"
                )
        segments.append(prev_text + feat_segment)
        last = next_start
    merged = "".join(segments) + draft[last:]

    # Orphan notes: features in notes but not in draft
    in_draft = {fid for _, _, fid in positions_sorted}
    orphan_ids = [fid for fid in notes.get("features", {}) if fid not in in_draft]
    if orphan_ids:
        merged = merged.rstrip() + "\n\n## 이전 노트 (제거된 피처)\n"
        for fid in orphan_ids:
            feat = notes["features"][fid]
            merged += f"\n### feature_id: {fid}\n"
            for name in SECTION_NAMES:
                if not feat.get(f"{name}_empty", True):
                    merged += f"\n**{name}:**\n{feat[name].strip()}\n"
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--notes", required=True)
    args = ap.parse_args()

    draft_path = Path(args.draft)
    notes = json.loads(Path(args.notes).read_text())
    merged = merge(draft_path.read_text(), notes)
    draft_path.write_text(merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_note_merger.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/pdf-spec-organizer/scripts/note_merger.py skills/pdf-spec-organizer/scripts/tests/test_note_merger.py
git commit -m "feat(scripts): add note_merger for draft + preserved-notes merge"
```

---

## Task 5: Add `page_publisher.py` — chunked block appender with sentinels

**Files:**
- Create: `skills/pdf-spec-organizer/scripts/page_publisher.py`
- Test: `skills/pdf-spec-organizer/scripts/tests/test_page_publisher.py`

**Context:** This script does NOT call Notion MCP directly (MCP tools are invoked by the Claude agent running SKILL.md). Instead, it prepares chunked block payloads as JSON and tracks sentinel strings, so SKILL.md can feed chunks to `notion-create-pages` / `notion-update-page` and log results.

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_page_publisher.py`:

```python
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
\tline1
\tline2
\tline3
### 2. Bar {toggle="true"}
\tline1
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_page_publisher.py -v`
Expected: all FAIL.

- [ ] **Step 3: Create `page_publisher.py`**

```python
"""Prepare chunked block payloads for Notion publish + sentinel-based resume.

Subcommands:
  chunk --input MD_PATH --max-blocks N
    Split a markdown body into chunks no larger than N blocks. Output:
      {"chunks": [{"index": 0, "block_count": 42, "markdown": "..."}, ...]}
    Each chunk's markdown ends with a `<!-- publish_sentinel: chunk_<N>_done -->`
    line. Chunk boundaries never split inside a toggle (tab-indented children).

  find-sentinel --input MD_PATH
    Scan body content for `<!-- publish_sentinel: chunk_N_done -->` markers.
    Output: {"last_chunk_index": <int-or--1>, "complete": <bool>}
"""
import argparse
import json
import re
import sys
from pathlib import Path

SENTINEL_DONE_RE = re.compile(r"<!--\s*publish_sentinel:\s*chunk_(\d+)_done\s*-->")
SENTINEL_COMPLETE_RE = re.compile(r"<!--\s*publish_sentinel:\s*complete\s*-->")


def _count_blocks(markdown: str) -> int:
    """Rough estimate: one block per non-empty, non-indented line."""
    lines = [l for l in markdown.splitlines() if l.strip()]
    return len(lines)


def _split_lines(markdown: str):
    """Yield (line, is_toggle_child) pairs preserving original text."""
    for line in markdown.splitlines(keepends=True):
        yield line, line.startswith("\t")


def chunk_markdown(markdown: str, max_blocks: int) -> list[dict]:
    chunks = []
    current: list[str] = []
    current_count = 0
    in_toggle = False

    for line, is_child in _split_lines(markdown):
        if is_child:
            in_toggle = True
        else:
            # non-indented line — safe boundary if current is big enough
            if current and current_count >= max_blocks and not in_toggle:
                chunks.append("".join(current))
                current = []
                current_count = 0
            in_toggle = False
        current.append(line)
        if line.strip():
            current_count += 1

    if current:
        chunks.append("".join(current))

    annotated = []
    for i, ch in enumerate(chunks):
        sentinel = f"\n\n<!-- publish_sentinel: chunk_{i}_done -->\n"
        full = ch.rstrip() + sentinel
        annotated.append({
            "index": i,
            "block_count": _count_blocks(full),
            "markdown": full,
        })
    return annotated


def cmd_chunk(args) -> int:
    text = Path(args.input).read_text()
    chunks = chunk_markdown(text, args.max_blocks)
    json.dump({"chunks": chunks}, sys.stdout, ensure_ascii=False)
    return 0


def cmd_find_sentinel(args) -> int:
    text = Path(args.input).read_text()
    complete = bool(SENTINEL_COMPLETE_RE.search(text))
    indices = [int(m.group(1)) for m in SENTINEL_DONE_RE.finditer(text)]
    last = max(indices) if indices else -1
    json.dump({"last_chunk_index": last, "complete": complete}, sys.stdout)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_c = sub.add_parser("chunk")
    p_c.add_argument("--input", required=True)
    p_c.add_argument("--max-blocks", type=int, default=80)
    p_c.set_defaults(func=cmd_chunk)

    p_s = sub.add_parser("find-sentinel")
    p_s.add_argument("--input", required=True)
    p_s.set_defaults(func=cmd_find_sentinel)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_page_publisher.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/pdf-spec-organizer/scripts/page_publisher.py skills/pdf-spec-organizer/scripts/tests/test_page_publisher.py
git commit -m "feat(scripts): add page_publisher for chunked publish + sentinel tracking"
```

---

## Task 6: Update `references/review-format.md` — draft.md v2 structure

**Files:**
- Modify: `skills/pdf-spec-organizer/references/review-format.md`

- [ ] **Step 1: Read the current file**

Run: `cat skills/pdf-spec-organizer/references/review-format.md`
Note the current "## `/tmp/spec-draft-<hash>-<ts>.md` 초안 파일 구조" section that describes the per-feature section format.

- [ ] **Step 2: Replace file content with v2 format**

Full file content:

````markdown
# 터미널 / 미리보기 포맷 규약

Phase 4 의 미리보기 md 파일과 터미널 출력은 일관된 포맷을 따른다. v2 부터는 **PDF 1개 = 초안 1개 = Notion 페이지 1개** 구조이며, 피처는 Toggle 블록으로 배치된다.

## `/tmp/spec-draft-<hash>-<ts>/draft.md` 초안 파일 구조

````markdown
<!-- plugin-state
phase: 4
pdf_hash: <short-hash>
source_file: <filename>
created_at: <iso8601>
publish_state: idle
page_id:
last_block_sentinel_id:
-->

# <PDF 제목>

## 개요
<Claude 가 생성한 PDF 전체 요약 — 1~2문단>

## 피처별 상세

### 1. <피처명> {toggle="true"}
	<!-- feature_id: <uuid> -->
	<callout color="yellow_bg">🟡 Draft</callout>

	**플랫폼:** 공통 / iOS / Android

	**개요:** ...

	**화면:**
	![원본: <local-path>](https://placehold.co/...)

	**요구사항:**
	- 요구사항 1
	- 요구사항 2

	**누락 체크:**
	- [ ] 에러 케이스 — 명시 없음
	- [x] 빈 상태 — 명시됨

	<!-- notes_ios_start -->
	### iOS
	<empty-block/>
	<!-- notes_ios_end -->

	<!-- notes_android_start -->
	### Android
	<empty-block/>
	<!-- notes_android_end -->

	<!-- notes_common_start -->
	### 공통 질문
	<empty-block/>
	<!-- notes_common_end -->

	<!-- publish_sentinel: feature_<short-id>_done -->

### 2. <피처명 2> {toggle="true"}
	<!-- feature_id: <uuid> -->
	...

## 메타
- 원본 PDF: <filename>
- PDF 해시: <short-hash>
- 생성자: <user>
- 생성일: <iso8601>
````

### 왜 마커가 많은가?

- `<!-- feature_id: ... -->` — Toggle rename/reorder 후에도 노트 보존 병합이 가능한 안정적 식별자.
- `<!-- notes_*_start|end -->` — `/spec-update` 시 해당 섹션만 정확히 교체/추출.
- `<!-- publish_sentinel: ... -->` — Phase 5 chunked publish 재개용 커서.
- `<!-- plugin-state ... -->` — `/spec-resume` phase 판정용. Notion 퍼블리시 시에는 필터링 후 제거.

## Phase 5 에서 추가되는 sentinel

Chunked publish 가 진행됨에 따라 페이지 하단에 `<!-- publish_sentinel: chunk_N_done -->` 블록이 append 된다. 마지막 chunk 뒤에는 `<!-- publish_sentinel: complete -->` 가 들어간다.

## 터미널 출력 규약

각 Phase 시작/종료를 간결히 표시:

```
[Phase 1/5] PDF 파싱 중...
[Phase 1/5] 완료 (12 페이지, 12 이미지 추출)

[Phase 2/5] 구조화 중...
[Phase 2/5] 완료

피처 7개 추출됨:
  1. 앱 시작 플로우 개방 (공통)
  2. 메인화면 비로그인 UI 제어 (공통)
  ...

이대로 진행할까요?
  y) 진행
  s N) 피처 N번 쪼개기
  m N,M) 피처 N,M 합치기
  r N) 피처 N번 리네이밍
  t N) 피처 N번 플랫폼 변경
  e) 에디터에서 수정
  c) 취소
>
```

Phase 5 진행 중에는 chunk 별 진행도 표시:

```
[Phase 5/5] 퍼블리시 중...
  ✓ shell 페이지 생성 (page_id: 34820097...)
  ✓ chunk 0/3 append 완료 (42 blocks)
  ✓ chunk 1/3 append 완료 (38 blocks)
  ✓ chunk 2/3 append 완료 (29 blocks)
  ✓ complete sentinel 기록
```
````

- [ ] **Step 3: Verify file saves**

Run: `head -20 skills/pdf-spec-organizer/references/review-format.md`
Expected: new content visible.

- [ ] **Step 4: Commit**

```bash
git add skills/pdf-spec-organizer/references/review-format.md
git commit -m "docs(skill): update review-format for v2 toggle-based draft structure"
```

---

## Task 7: Update `references/conflict-policy.md` — v2 dedup, merge, Relation semantics

**Files:**
- Modify: `skills/pdf-spec-organizer/references/conflict-policy.md`

- [ ] **Step 1: Replace file content**

Full replacement:

````markdown
# 충돌 처리 정책 (v2)

Phase 5 퍼블리시 전 dedup 단계에서 적용된다. v2 부터는 **PDF 1개 = Notion 페이지 1개** 구조이므로 충돌 감지 기준도 피처명이 아니라 **PDF 해시 또는 파일명**이다.

## Dedup 순서

```
1. Notion DB 에서 PDF 해시 동일 페이지 검색
   ├─ 있음 → "동일 PDF 재실행" 경로
   └─ 없음 → 파일명 동일 페이지 검색
             ├─ 있음 → "업데이트된 PDF" 경로
             └─ 없음 → 새 페이지 생성
```

## "동일 PDF 재실행" (hash 일치)

```
Notion 에 동일 PDF 페이지가 이미 존재합니다:
  제목: <PDF 제목>
  페이지: <url>
  최근 편집자: <user>  최근 편집: <date>

어떻게 할까요?
  [1] 덮어쓰기 (노트 보존)     ← 기본
  [2] 새 버전 (이전_버전 Relation 으로 연결)
  [3] 건너뛰기
>
```

## "업데이트된 PDF" (파일명 동일, 해시 다름)

```
같은 파일명의 기존 PDF 페이지가 있습니다 (내용은 다름):
  제목: <PDF 제목>
  기존 해시: <old>   현재 해시: <new>
  페이지: <url>

어떻게 할까요?
  [1] 덮어쓰기 (노트 보존)     ← 기본
  [2] 새 버전 (이전_버전 Relation 으로 연결)
  [3] 건너뛰기
>
```

## 덮어쓰기 = 노트 보존 (기본값)

기본 덮어쓰기는 **요구사항 / 화면 / 누락 체크만 재렌더** 하고 노트는 무조건 보존한다. 파괴적 덮어쓰기가 필요한 경우에만 `--force-overwrite` 숨김 플래그를 사용한다(사용자가 직접 입력해야 하며 `--fast` 에서도 자동 선택되지 않음).

구현:

1. `mcp__claude_ai_Notion__notion-fetch` 로 기존 페이지 본문 가져옴
2. `scripts/note_extractor.py` 로 `feature_id` 별 iOS/Android/공통 노트 및 stray 추출
3. `scripts/note_merger.py` 로 새 draft 에 병합
4. 대상 페이지에서 제거된 feature_id 의 노트 → 새 draft 하단 "이전 노트 (제거된 피처)" 섹션에 모음
5. Property (`플랫폼`, `누락 항목`) 는 fresh union 으로 항상 치환

## 새 버전

새 페이지를 생성하고 그 페이지의 `이전_버전` Relation 에 기존 페이지를 연결. 기존 페이지는 건드리지 않는다. v2 부터 이 Relation 은 **PDF 페이지 단위**만 의미가 있다 (피처 단위 Relation 은 사용하지 않음).

## 건너뛰기

아무것도 하지 않음. 초안은 그대로 유지 → 사용자가 `/spec-resume` 로 재시도 가능.

## 동시 실행 경고 (기존 로직 유지)

5분 내 **같은 PDF 해시**로 다른 사용자가 실행한 기록이 있으면 경고:

```
⚠️  5분 내 동일 PDF 를 다른 실행이 처리했습니다:
  실행자: <user>  시작: <N분 전>

덮어쓰기 전에 조율하세요. 계속 진행할까요? (y/n)
```

## `/spec-update` 의 concurrent-edit 보호

`/spec-update` 는 노트만 갱신하지만 여러 사용자가 동시에 같은 PDF 페이지에 돌릴 수 있다.

1. 세션 시작 시 `last_edited_time` 캡처 (T0). 선택적으로 5분짜리 소프트 락 주석 블록 `<!-- editing_lock: <user@email> <iso8601> -->` 을 페이지 말미에 삽입
2. 사용자가 `$EDITOR` 로 초안 편집
3. 퍼블리시 직전 페이지 refetch → `last_edited_time` 비교 (T1)
4. T1 > T0 → 3-way merge:
   - fresh 노트(현재 Notion), draft 노트(내 편집), base 노트(T0 캡처) 추출
   - 같은 sub-section 을 양쪽이 편집 → [내 편집 유지 / fresh 유지 / 에디터에서 merge] 프롬프트
   - 한쪽만 편집 → 그 편집 채택
5. 퍼블리시 후 락 주석 제거 또는 만료

락은 **advisory** (강제 아님) — 같은 페이지에 동시 접근한 다른 사용자에게 경고 목적.

## `--fast` 플래그 동작

- `[1] 덮어쓰기(노트 보존)` 는 자동 선택 (노트 보존이 기본이라 파괴적이지 않음)
- `[2] 새 버전` / `[3] 건너뛰기` / `--force-overwrite` 는 항상 프롬프트

## 이미지 업로드 전략 (기존 유지)

Notion API 는 로컬 파일 경로 직접 업로드를 지원하지 않는다. Phase 5 는 각 이미지를 placeholder URL (`https://placehold.co/...`) 로 대체하고, 캡션에 원본 로컬 경로를 주석으로 표기한다. v0.2 에서 외부 호스팅 중계 업로더 추가 예정.

## `이전_버전` Relation 마이그레이션

v1 피처 페이지의 `이전_버전` Relation 값들은 `migrate_to_per_pdf.py` 가 **carry-forward 하지 않는다**. v1 의 피처 단위 버전 체인은 v2 의 PDF 단위 모델에서 의미가 사라지기 때문. 마이그레이션 후 `이전_버전` Relation 은 v2 에서 새로 만들어지는 PDF 페이지간 체인에만 사용된다.
````

- [ ] **Step 2: Commit**

```bash
git add skills/pdf-spec-organizer/references/conflict-policy.md
git commit -m "docs(skill): rewrite conflict-policy for v2 PDF-level dedup and note preservation"
```

---

## Task 8: Update SKILL.md Phase 4 — toggle-based draft render

**Files:**
- Modify: `skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Read current Phase 4 section**

Run: `grep -n "## Phase 4" skills/pdf-spec-organizer/SKILL.md`
Note the line range to replace.

- [ ] **Step 2: Replace Phase 4 section**

Find the section starting `## Phase 4 — 개발자 노트 + 미리보기 + 개입 ②` and replace through the end of `### 4-5. 취소 / 에디터 재진입 처리` with:

````markdown
## Phase 4 — 개발자 노트 + 미리보기 + 개입 ②

**왜:** 기술 판단(iOS/Android 구현 차이, 엣지케이스, 팀 간 질문거리) 은 Claude 가 대신할 수 없는 영역. 이 단계가 스킬의 핵심 가치 — 팀 지식을 축적하는 지점. v2 부터는 PDF 1개 = 초안 1개 = Notion 페이지 1개 구조이므로 모든 피처 노트를 **한 파일 안에서** 한 번에 작성한다.

### 4-1. feature_id 할당

```bash
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/feature_id.py" \
  assign --features-file "${WORK_DIR}/features.json"
```

- 새 피처에 UUID4 를 부여한다
- 이미 `feature_id` 가 있는 피처는 건드리지 않음 (Phase 2 의 rename/merge/split 이후에도 id 는 유지)

### 4-2. 초안 md 파일 렌더

`features.json` + `missing.json` + `parsed.json` 을 통합해 `${DRAFT_PATH}` 로 저장. 포맷은 `references/review-format.md` 의 "초안 파일 구조" 를 엄격히 따른다.

**중요:**
- `<!-- plugin-state -->` 헤더에 `phase: 4`, `pdf_hash`, `source_file`, `created_at`, `publish_state: idle`, `page_id:` (빈 값), `last_block_sentinel_id:` (빈 값) 포함
- 각 피처는 Toggle heading (`### N. <name> {toggle="true"}`) 로 렌더
- 각 Toggle 첫 줄 아래에 `<!-- feature_id: <uuid> -->` 주석 삽입
- iOS / Android / 공통 노트 섹션은 `<!-- notes_*_start/end -->` 마커로 감싸고 **빈 상태** (`<empty-block/>`) 로 렌더
- 각 Toggle 끝에 `<!-- publish_sentinel: feature_<short-id>_done -->` 삽입
- `--fast` 플래그여도 이 Phase 는 생략되지 않음

### 4-3. 사용자에게 노트 작성 프롬프트

```
다음 단계: 개발자 노트 작성

초안 파일: /tmp/spec-draft-<hash>-<ts>/draft.md
(피처 7개가 Toggle 블록으로 들어있습니다. 담당 플랫폼 섹션만 채우세요.)

어떻게 할까요?
  e) 에디터($EDITOR)로 열기  ← 권장
  s) 건너뛰기 (빈 노트로 퍼블리시)
  c) 취소
>
```

`e` 선택 시 `$EDITOR` 로 열기. 값이 없으면 `code` / `vim` 순으로 시도.

### 4-4. 저장 후 검증

에디터 종료 후:
- 파일 존재 확인
- `plugin-state` 헤더 파싱 → `phase` 를 5 로 업데이트
- 노트 섹션이 전부 비어도 경고만 표시 (계속 가능):
  ```
  ℹ️  노트가 비어있습니다. Phase 5 로 계속할까요? (y/n/e)
  ```
  `e` 는 다시 에디터 열기.

### 4-5. 최종 미리보기

```
미리보기:

  PDF: <filename>
  피처 7개, 누락 항목 35개, 노트:
    - 앱 시작 플로우 개방: iOS ✓, Android ✗, 공통 ✗
    - 메인화면 비로그인 UI 제어: iOS ✓, Android ✓, 공통 ✗
    ...

  Notion 에 퍼블리시할까요?
    y) 퍼블리시
    e) 에디터로 다시 열기
    c) 취소
>
```

### 4-6. 취소 / 에디터 재진입 처리

- `c` → Phase 5 진입 전 정리 (`draft_registry update-status --status failed`)
- `e` → 4-3 으로 돌아감
````

- [ ] **Step 3: Commit**

```bash
git add skills/pdf-spec-organizer/SKILL.md
git commit -m "feat(skill): rewrite Phase 4 for v2 toggle-based single-draft render"
```

---

## Task 9: Update SKILL.md Phase 5 — chunked publish with note preservation

**Files:**
- Modify: `skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Locate Phase 5 section**

Run: `grep -n "## Phase 5" skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 2: Replace Phase 5 section**

Replace from `## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③` through `### 5-5. GC 트리거` with:

````markdown
## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

**왜:** v2 는 PDF 1개 = 페이지 1개. 동일 PDF 재실행·업데이트 PDF·동시 편집 같은 상황을 안전하게 처리해야 한다. 또한 Notion API 의 per-call block 제한 때문에 chunked publish + sentinel 기반 resume 이 필수.

### 5-1. DB ID / 파일명 확보

- Notion DB data source ID: Precondition 2 에서 읽은 `notion_database_id` 와 config 의 `notion_data_source_id` 사용
- `PDF_FILENAME=$(basename "$PDF_PATH")` 만 저장 (홈 경로 노출 방지)

### 5-2. Dedup 조회

1. `mcp__claude_ai_Notion__notion-search` 로 `data_source_url=collection://<data_source_id>`, query=`<PDF 해시>` 검색 (title + PDF 해시 property 매칭)
2. 해시 일치 페이지 있음 → 1a. "동일 PDF 재실행" 프롬프트 (`references/conflict-policy.md` 참조)
3. 해시 불일치 + 같은 파일명 페이지 있음 → 1b. "업데이트된 PDF" 프롬프트
4. 모두 없음 → 5-3 새 페이지 플로우

### 5-3. 새 페이지 퍼블리시 (신규 경로)

```bash
# 1) shell 페이지 생성 (제목/properties/개요만)
# mcp__claude_ai_Notion__notion-create-pages 호출 → page_id 획득

# 2) draft.md 본문을 chunks 로 분할
python3 "${SCRIPTS}/page_publisher.py" chunk \
  --input "${DRAFT_PATH}" --max-blocks 80 > "${WORK_DIR}/chunks.json"

# 3) plugin-state 업데이트
#    publish_state=page_created
#    page_id=<notion page id>
python3 "${SCRIPTS}/draft_registry.py" update-status \
  --draft-path "${DRAFT_PATH}" \
  --status running \
  --page-id "${PAGE_ID}" \
  --publish-state page_created

# 4) chunk 순차 append:
#    각 chunk 에 대해 mcp__claude_ai_Notion__notion-update-page
#    command=update_content, content_updates=[ { old_str: <last_sentinel>, new_str: <chunk_markdown> } ]
#    (첫 chunk 는 shell 페이지의 overview 말미를 anchor 로 사용)
#    성공 후 draft 의 plugin-state 에 last_block_sentinel_id 갱신
#    ${WORK_DIR}/publish.log 에 timestamped 로그 기록
#    Rate limit 발생 시 exponential backoff (1, 2, 4, 8 초, max 3 retries)

# 5) 모든 chunk 성공 → publish_sentinel: complete append
# 6) draft_registry update-status --status success --publish-state complete
```

### 5-4. 덮어쓰기 (노트 보존) 경로

```bash
# 1) 기존 페이지 본문 fetch
# mcp__claude_ai_Notion__notion-fetch id=${EXISTING_PAGE_ID}
# 결과를 ${WORK_DIR}/existing_body.md 로 저장

# 2) 노트 추출
python3 "${SCRIPTS}/note_extractor.py" \
  < "${WORK_DIR}/existing_body.md" > "${WORK_DIR}/preserved_notes.json"

# 3) 새 draft 에 병합
python3 "${SCRIPTS}/note_merger.py" \
  --draft "${DRAFT_PATH}" \
  --notes "${WORK_DIR}/preserved_notes.json"

# 4) 덮어쓰기: replace_content 로 전체 교체
# mcp__claude_ai_Notion__notion-update-page command=replace_content new_str=<draft body>
# (chunk 제한이 문제되면 5-3 의 shell+chunks 경로를 동일하게 사용)

# 5) properties fresh union 으로 갱신
# mcp__claude_ai_Notion__notion-update-page command=update_properties ...
```

### 5-5. 새 버전 경로

1. 5-3 새 페이지 플로우 동일
2. 단, create-page 시 `이전_버전` Relation 에 기존 페이지 URL 포함
3. 기존 페이지는 건드리지 않음

### 5-6. 실행 기록 갱신

성공:
```bash
python3 "${SCRIPTS}/draft_registry.py" update-status \
  --draft-path "${DRAFT_PATH}" \
  --status success \
  --publish-state complete
```

부분 실패 (chunk 도중 중단):
```bash
python3 "${SCRIPTS}/draft_registry.py" update-status \
  --draft-path "${DRAFT_PATH}" \
  --status partial_success \
  --publish-state chunks_appending
```
터미널:
```
⚠️  3 chunk 중 2 chunk 만 append 됐습니다:
  ✓ chunk 0/2
  ✓ chunk 1/2
  ✗ chunk 2/2 (Notion API timeout)

이어서 시도: /spec-resume --resume-latest
초안: <draft_path>  페이지: <notion_url>
```

### 5-7. 결과 요약 + GC

성공:
```
✓ 퍼블리시 완료:
  <PDF 제목>: https://notion.so/...

초안은 3일 후 자동 삭제됩니다: <draft_path>
```

GC 트리거:
```bash
python3 "${SCRIPTS}/draft_registry.py" gc
```
`partial_success` 는 7일 보존 (GC 대상 아님) 이므로 자연스럽게 `/spec-resume` 시나리오 보호.
````

- [ ] **Step 3: Commit**

```bash
git add skills/pdf-spec-organizer/SKILL.md
git commit -m "feat(skill): rewrite Phase 5 for chunked publish + note preservation"
```

---

## Task 10: Update SKILL.md Resume mode — publish_state-aware resume

**Files:**
- Modify: `skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Replace `## Resume 모드` section**

````markdown
## Resume 모드

`/spec-resume` 가 호출되면 이 Skill 이 다른 모드로 진입.

### R-1. 초안 선택

- `--resume-latest`: `draft_registry list-latest --count 10` 결과에서 **`status` 가 `running` / `partial_success` / `failed`** 인 최신 항목 자동 선택. 없으면 사용자에게 리스트 보여주고 선택받기.
- `--resume <path>`: 지정된 경로 사용. 없으면 중단.

### R-2. 상태 복구

초안의 `<!-- plugin-state -->` 헤더 파싱.

#### R-2-a. 레거시 v1 draft 감지

`publish_state` 필드 자체가 없으면 v1 초안:
```
ℹ️  v1 초안이 감지됐습니다. 전체 재퍼블리시로 진행합니다.
  (Phase 1 부터 다시 실행됨 — 구 피처별 페이지 모델로의 resume 은 지원되지 않음)
```
→ Phase 4 부터 v2 플로우로 재시작.

#### R-2-b. v2 draft 의 `publish_state` 별 분기

- `idle` / `<empty>`: Phase 5 진입 (Phase 4 도 필요하면 사용자 선택)
- `page_created`: chunks_appending 단계부터 재개. 필요하면 shell 페이지 재검증 (R-3)
- `chunks_appending`: shell 페이지 재검증 후 sentinel-based 재개 (R-3)
- `complete`: "이미 완료된 초안입니다. 새 실행을 원하시나요?" 프롬프트
- `failed`: publish.log 마지막 에러 출력 → 재시도/취소 프롬프트

### R-3. 페이지 재검증 및 sentinel 재개

```bash
# 1) 페이지 존재 확인
# mcp__claude_ai_Notion__notion-fetch id=${PAGE_ID}
# 404 → 프롬프트:
#   ⚠️  page_id <id> 가 더 이상 존재하지 않습니다.
#   어떻게 할까요?
#     [1] 새 페이지로 퍼블리시
#     [2] 취소
#   >

# 2) 페이지 본문 fetch → sentinel 스캔
python3 "${SCRIPTS}/page_publisher.py" find-sentinel \
  --input "${WORK_DIR}/existing_body.md" > "${WORK_DIR}/sentinel.json"

# 3) last_chunk_index 읽기:
#    LAST=$(jq -r .last_chunk_index "${WORK_DIR}/sentinel.json")
# 4) chunks.json 의 (LAST+1) 번째부터 append 재개
# 5) complete sentinel 을 스캔했으면 publish_state=complete, status=success 로 갱신하고 종료
```

#### R-3-a. 페이지 수동 수정 감지

- sentinel 이 예상 순서로 존재하지 않거나 중간 sentinel 이 누락됐다면:
  ```
  ⚠️  페이지가 수동 수정된 것 같습니다 (sentinel 순서 불일치).
  어떻게 할까요?
    [1] 새 버전으로 퍼블리시
    [2] 현재 위치에서 강제 재개 (중복 위험)
    [3] 취소
  >
  ```

### R-4. 실행

해당 Phase/지점부터 본 워크플로우와 동일하게 진행. 마지막에 `update-status` 갱신.
````

- [ ] **Step 2: Commit**

```bash
git add skills/pdf-spec-organizer/SKILL.md
git commit -m "feat(skill): v2 Resume mode with publish_state and sentinel-based re-entry"
```

---

## Task 11: Update SKILL.md Update mode — toggle-level edit via feature_id

**Files:**
- Modify: `skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Replace `## Update 모드 (/spec-update)` section**

````markdown
## Update 모드 (`/spec-update`)

기존 Notion 페이지의 노트를 수정. v2 부터 PDF 페이지 1개 안에 여러 피처가 들어있으므로 **전체 페이지** 또는 **특정 피처 1개 Toggle** 단위 편집이 가능하다.

진입 조건:
- `$NOTION_PAGE_URL` 필수
- `$FEATURE_NAME` (선택): 지정되면 해당 Toggle 만 편집

### U-1. 페이지 조회 및 초안 생성

```bash
# 1) 페이지 fetch
# mcp__claude_ai_Notion__notion-fetch id=$NOTION_PAGE_URL
# 결과를 ${WORK_DIR}/existing_body.md 로 저장
# last_edited_time 캡처 → ${WORK_DIR}/T0.txt

# 2) 페이지 → draft.md 역변환 (features + notes 를 features.json 스키마로 복원)
# features.json: 각 Toggle 의 feature_id/이름/platform/요구사항/누락 을 복원
# draft.md: review-format.md 포맷으로 재렌더 (preserved 노트 포함)
```

### U-2. feature_name → feature_id 해상

`$FEATURE_NAME` 이 지정된 경우:

```bash
python3 "${SCRIPTS}/feature_id.py" resolve \
  --features-file "${WORK_DIR}/features.json" \
  --name "$FEATURE_NAME" > "${WORK_DIR}/resolved.json" 2> "${WORK_DIR}/resolve_err.txt"

# 실패 시:
# - not found → features.json 에서 피처명 목록 출력, 중단
# - ambiguous → 후보 목록 출력, 사용자에게 feature_id 직접 지정 요청
```

미지정 시: 전체 페이지 편집 모드.

### U-3. 소프트 락 설치 (optional, best-effort)

```bash
# 페이지 말미에 <!-- editing_lock: <user@email> <iso8601> --> 블록 append
# 이미 <5분 이내> 다른 유저 락이 있으면 경고:
#   ⚠️  <user> 가 <N>분 전부터 편집 중입니다. 계속할까요? (y/n)
```

### U-4. 에디터 편집

- 전체 모드: `${DRAFT_PATH}` 를 `$EDITOR` 로 열기
- 부분 모드: 해당 Toggle 블록만 임시 파일로 추출 → `$EDITOR` → 저장 후 원 draft 에 역병합

### U-5. 퍼블리시 전 concurrent-edit 체크

```bash
# 1) 페이지 refetch, last_edited_time 캡처 → T1
# 2) T1 > T0 → 3-way merge:
#    - base 노트: T0 캡처본에서 추출
#    - fresh 노트: T1 (방금 fetch) 에서 추출
#    - draft 노트: 사용자 편집본에서 추출
#    - 각 feature_id × sub-section(ios|android|common) 조합에 대해:
#      * 양쪽 모두 편집 → 프롬프트 [내 편집 / fresh / 에디터 merge]
#      * 한쪽만 편집 → 그 편집 채택
# 3) T1 == T0 → 바로 퍼블리시
```

### U-6. 병합 퍼블리시

- Phase 5 의 "덮어쓰기(노트 보존)" 경로만 사용. 새 버전은 이 모드에서 허용하지 않음
- 부분 모드 (`FEATURE_NAME` 지정) 면:
  - `notion-update-page command=update_content` 로 해당 Toggle 블록만 검색-교체
  - old_str 은 기존 Toggle 의 `<!-- feature_id: <uuid> -->` 부터 다음 Toggle 의 `<!-- feature_id: ... -->` (또는 페이지 끝) 까지
- 전체 모드:
  - 5-4 (덮어쓰기 노트 보존) 와 동일

### U-7. 락 해제

정상 종료 → `editing_lock` 주석 블록 제거. 예외 종료 시 TTL 5분 후 자동 만료 (다음 `/spec-update` 진입 시 판별).
````

- [ ] **Step 2: Commit**

```bash
git add skills/pdf-spec-organizer/SKILL.md
git commit -m "feat(skill): v2 Update mode with feature-level edit and concurrent-edit merge"
```

---

## Task 12: Update `commands/spec-update.md` — --feature flag, root guard

**Files:**
- Modify: `commands/spec-update.md`

- [ ] **Step 1: Replace file content**

```markdown
---
name: spec-update
description: 기존 Notion 피처 페이지의 iOS/Android/공통 노트를 갱신한다. 전체 페이지 또는 특정 피처 Toggle 단위 편집 가능.
argument-hint: <notion-page-url> [--feature="<name>"]
allowed-tools: Bash Read Write Edit mcp__claude_ai_Notion__*
---

# /spec-update

기존 Notion PDF 페이지의 노트 섹션을 수정한다. 새 PDF 를 돌리지 않고 노트만 append/교체한다. 피처 이름을 지정하면 해당 Toggle 만, 미지정 시 전체 페이지 편집.

## 사용법

```
/spec-update https://www.notion.so/.../<page>                                   # 전체
/spec-update https://www.notion.so/.../<page> --feature="로그인 유도 팝업(A/B)"   # 해당 피처만
```

## 동작

1. Notion URL 에서 page ID 추출
2. `--feature=` 플래그 파싱 (공백/괄호/슬래시 포함 가능)
3. `pdf-spec-organizer` Skill 을 **Update 모드**로 실행

## 인자 처리

```bash
# CLAUDE_PLUGIN_ROOT 가드 (미설정 시 커맨드 파일 상대경로로 폴백)
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  export CLAUDE_PLUGIN_ROOT
fi

URL=""
FEATURE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --feature=*) FEATURE="${1#--feature=}"; shift;;
    --feature) FEATURE="$2"; shift 2;;
    *)
      if [ -z "$URL" ]; then URL="$1"; shift
      else echo "❌ 알 수 없는 인자: $1" >&2; exit 2
      fi
      ;;
  esac
done

if [ -z "$URL" ]; then
  echo "❌ Notion 페이지 URL 이 필요합니다." >&2
  exit 2
fi

# page ID 추출: URL 끝의 32자 hex 또는 UUID 형식
PAGE_ID=$(echo "$URL" | grep -oE "[0-9a-f]{32}" | tail -1)
if [ -z "$PAGE_ID" ]; then
  PAGE_ID=$(echo "$URL" | grep -oE "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" | tail -1)
fi

if [ -z "$PAGE_ID" ]; then
  echo "❌ URL 에서 페이지 ID 를 추출할 수 없습니다: $URL" >&2
  exit 1
fi

export NOTION_PAGE_ID="$PAGE_ID"
export NOTION_PAGE_URL="$URL"
export FEATURE_NAME="$FEATURE"
export MODE="update"
```

이후 Skill 을 진입점으로 호출. Skill 은 `MODE=update` + (`FEATURE_NAME` 유무) 로 전체/부분 모드를 판별.
```

- [ ] **Step 2: Commit**

```bash
git add commands/spec-update.md
git commit -m "feat(cmd): add --feature flag and CLAUDE_PLUGIN_ROOT guard to /spec-update"
```

---

## Task 13: Update `commands/spec-resume.md` — root guard, description

**Files:**
- Modify: `commands/spec-resume.md`

- [ ] **Step 1: Replace file content**

```markdown
---
name: spec-resume
description: 중단된 /spec-from-pdf 세션을 이어받는다. 퍼블리시 도중 중단된 부분 append (partial_success) 도 재개 가능.
argument-hint: [--resume-latest | <draft-path>]
allowed-tools: Bash Read Write Edit mcp__claude_ai_Notion__*
---

# /spec-resume

중단된 세션을 Phase 진행 상태부터 이어받는다. Phase 5 도중 chunked publish 가 부분 실패한 경우에도 sentinel 기반으로 재개.

## 사용법

```
/spec-resume --resume-latest
/spec-resume /tmp/spec-draft-abc123-1700000000/draft.md
```

## 동작

1. 초안 경로 결정 (최근 실행 or 명시된 경로)
2. 초안의 `<!-- plugin-state -->` 헤더에서 `phase`, `publish_state`, `page_id` 읽기
3. `pdf-spec-organizer` Skill 을 **Resume 모드**로 진입 (해당 지점부터 재실행)

## 인자 처리

```bash
# CLAUDE_PLUGIN_ROOT 가드
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  export CLAUDE_PLUGIN_ROOT
fi

ARG="$1"

if [ -z "$ARG" ]; then
  echo "❌ --resume-latest 또는 초안 경로가 필요합니다." >&2
  exit 2
fi

if [ "$ARG" = "--resume-latest" ]; then
  LATEST=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" list-latest --count 10 \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
# prefer partial_success / failed / running
priority = {'partial_success': 0, 'failed': 1, 'running': 2}
candidates = [e for e in data['entries'] if e.get('status') in priority]
if not candidates:
    sys.exit(1)
candidates.sort(key=lambda e: (priority.get(e['status'], 99), -e['created_at']))
print(candidates[0]['draft_path'])
")
  if [ -z "$LATEST" ]; then
    echo "❌ 이어받을 초안이 없습니다." >&2
    exit 1
  fi
  DRAFT_PATH="$LATEST"
else
  DRAFT_PATH=$(python3 -c "import sys, os; print(os.path.realpath(os.path.expanduser(sys.argv[1])))" "$ARG")
fi

if [ ! -f "$DRAFT_PATH" ]; then
  echo "❌ 초안 파일이 없습니다: $DRAFT_PATH" >&2
  exit 1
fi

export DRAFT_PATH
export MODE="resume"
```

Skill 은 `MODE=resume` 를 인식해 Resume 모드 로직 실행. 초안의 `plugin-state` 헤더에서 `phase` + `publish_state` 를 읽어 이어받기.
```

- [ ] **Step 2: Commit**

```bash
git add commands/spec-resume.md
git commit -m "feat(cmd): add CLAUDE_PLUGIN_ROOT guard and partial_success priority to /spec-resume"
```

---

## Task 14: Add `migrate_to_per_pdf.py` — legacy pages consolidation

**Files:**
- Create: `skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py`
- Test: `skills/pdf-spec-organizer/scripts/tests/test_migrate_to_per_pdf.py`

**Context:** The script operates on a JSON dump of the DB's feature pages (because direct Notion MCP calls are invoked by the SKILL.md orchestration layer, not by this script). Input shape mirrors `notion-search` output for a data source.

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_migrate_to_per_pdf.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_migrate_to_per_pdf.py -v`
Expected: all FAIL (missing script).

- [ ] **Step 3: Create `migrate_to_per_pdf.py`**

```python
"""Plan migration from per-feature pages to per-PDF pages.

Dry-run is the default and safest mode: it reads a JSON dump of the current
DB's feature pages (as produced by the SKILL orchestration layer via
notion-search + notion-fetch) and outputs a plan. Apply mode is NOT implemented
here — the SKILL.md is responsible for executing the plan via MCP tool calls,
so this script's job ends with a deterministic plan.

Input (--pages-file PATH):
{
  "pages": [
    {
      "id": "<notion page id>",
      "title": "<feature name>",
      "properties": {
        "PDF 해시": "<12-char hash or ''>",
        "원본 PDF": "<filename or ''>",
        "플랫폼": ["iOS", "Android", "공통"],
        "누락 항목": ["error_cases", ...],
        "archived": bool
      },
      "content": "<markdown body>",
      "last_edited_time": "<iso8601>"
    },
    ...
  ]
}

Output (stdout JSON):
{
  "groups": [
    {
      "pdf_hash": "<hash or null>",
      "pdf_filename": "<filename>",
      "match_mode": "hash" | "filename+date",
      "source_page_ids": ["p1", "p2"],
      "union_platform": [...],
      "union_missing": [...],
      "features": [{id, name, platform, content}, ...]
    }
  ],
  "orphans": [{"id", "title", "reason"}, ...],
  "skipped_archived": <int>
}

Also writes a human-readable report to --report PATH.
"""
import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path


def _iso_to_date(s: str) -> dt.date | None:
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _group_by_hash(pages: list[dict]):
    by_hash: dict[str, list[dict]] = defaultdict(list)
    remaining: list[dict] = []
    for p in pages:
        h = p["properties"].get("PDF 해시", "").strip()
        if h:
            by_hash[h].append(p)
        else:
            remaining.append(p)
    return by_hash, remaining


def _group_by_filename_date(pages: list[dict]):
    """Group pages lacking hash by (filename, ±1-day window)."""
    groups: list[list[dict]] = []
    orphans: list[dict] = []
    # bucket by filename first
    by_fn: dict[str, list[dict]] = defaultdict(list)
    for p in pages:
        fn = p["properties"].get("원본 PDF", "").strip()
        if not fn:
            orphans.append({"id": p["id"], "title": p["title"],
                            "reason": "no PDF 해시 and no 원본 PDF"})
            continue
        by_fn[fn].append(p)

    for fn, items in by_fn.items():
        # sort by last_edited_time; cluster into windows ±1 day
        items.sort(key=lambda x: x.get("last_edited_time", ""))
        current: list[dict] = []
        for p in items:
            d = _iso_to_date(p.get("last_edited_time", ""))
            if not current:
                current = [p]
                continue
            prev_d = _iso_to_date(current[-1].get("last_edited_time", ""))
            if d and prev_d and abs((d - prev_d).days) <= 1:
                current.append(p)
            else:
                groups.append(current)
                current = [p]
        if current:
            groups.append(current)

    return groups, orphans


def _build_group_record(pages: list[dict], match_mode: str, pdf_hash: str | None) -> dict:
    union_platform = sorted({pl for p in pages for pl in p["properties"].get("플랫폼", [])})
    union_missing = sorted({m for p in pages for m in p["properties"].get("누락 항목", [])})
    features = []
    for p in pages:
        features.append({
            "id": p["id"],
            "name": p["title"],
            "platform": p["properties"].get("플랫폼", []),
            "missing": p["properties"].get("누락 항목", []),
            "content": p.get("content", ""),
            "last_edited_time": p.get("last_edited_time", ""),
        })
    return {
        "pdf_hash": pdf_hash,
        "pdf_filename": pages[0]["properties"].get("원본 PDF", ""),
        "match_mode": match_mode,
        "source_page_ids": sorted(p["id"] for p in pages),
        "union_platform": union_platform,
        "union_missing": union_missing,
        "features": features,
    }


def plan(pages: list[dict]) -> dict:
    live = [p for p in pages if not p["properties"].get("archived")]
    skipped = len(pages) - len(live)

    by_hash, remaining = _group_by_hash(live)
    groups: list[dict] = []
    for h, items in by_hash.items():
        groups.append(_build_group_record(items, "hash", h))

    fn_groups, orphans = _group_by_filename_date(remaining)
    for items in fn_groups:
        groups.append(_build_group_record(items, "filename+date", None))

    return {"groups": groups, "orphans": orphans, "skipped_archived": skipped}


def render_report(planned: dict) -> str:
    lines = ["# Migration Plan", ""]
    lines.append(f"Groups: {len(planned['groups'])}")
    lines.append(f"Orphans: {len(planned['orphans'])}")
    lines.append(f"Skipped (archived): {planned['skipped_archived']}")
    lines.append("")
    lines.append("## Groups")
    for i, g in enumerate(planned["groups"], 1):
        lines.append(f"### Group {i}")
        lines.append(f"- match_mode: `{g['match_mode']}`")
        lines.append(f"- pdf_hash: `{g['pdf_hash'] or '(none)'}`")
        lines.append(f"- pdf_filename: {g['pdf_filename']}")
        lines.append(f"- source pages: {', '.join(g['source_page_ids'])}")
        lines.append(f"- union 플랫폼: {', '.join(g['union_platform'])}")
        lines.append(f"- union 누락: {', '.join(g['union_missing'])}")
        lines.append("- features:")
        for f in g["features"]:
            lines.append(f"  - {f['name']} ({', '.join(f['platform']) or '-'})")
        lines.append("")
    if planned["orphans"]:
        lines.append("## Orphans (manual action required)")
        for o in planned["orphans"]:
            lines.append(f"- `{o['id']}` {o['title']} — {o['reason']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-file", required=True)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.pages_file).read_text())
    planned = plan(data["pages"])

    # Always emit report + JSON
    Path(args.report).write_text(render_report(planned), encoding="utf-8")
    json.dump(planned, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_migrate_to_per_pdf.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py skills/pdf-spec-organizer/scripts/tests/test_migrate_to_per_pdf.py
git commit -m "feat(scripts): add migrate_to_per_pdf planner (dry-run only)"
```

---

## Task 15: Add migration-tool section to SKILL.md

**Files:**
- Modify: `skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Append migration section**

Append at end of `SKILL.md`:

````markdown

## 마이그레이션 (`migrate_to_per_pdf.py`)

v1→v2 전환 시 **1회성** 도구. 기존 피처 페이지들을 PDF 단위 페이지로 통합한다.

### 1. 준비

- 사용 전 Notion DB 에 property 추가 필요:
  - `migrated_to` (URL)
  - `archived` (Checkbox)
- 한 번만 추가하면 이후 실행에 계속 활용. 명령:
  ```
  mcp__claude_ai_Notion__notion-update-data-source
    data_source_id: <id>
    statements: 'ADD COLUMN "migrated_to" URL; ADD COLUMN "archived" CHECKBOX'
  ```

### 2. 페이지 덤프 수집

현재 DB 의 모든 피처 페이지를 JSON 으로 덤프:

```bash
# Claude 오케스트레이션:
# 1) mcp__claude_ai_Notion__notion-fetch id=collection://<data_source_id>
# 2) 페이지마다 mcp__claude_ai_Notion__notion-fetch id=<page_id>, body 저장
# 3) 모든 결과를 ${WORK_DIR}/pages.json 으로 통합
#    형식: { "pages": [ { "id", "title", "properties", "content", "last_edited_time" } ] }
```

### 3. 드라이런

```bash
python3 "${SCRIPTS}/migrate_to_per_pdf.py" \
  --pages-file "${WORK_DIR}/pages.json" \
  --dry-run \
  --report "${WORK_DIR}/migration-report.md"
```

`migration-report.md` 를 검토해 그룹 묶임/orphan 판정 여부 확인.

### 4. Apply (Claude 오케스트레이션)

드라이런 결과를 소비해 Claude 가 각 그룹에 대해:

1. Toggle 블록 조립 (기존 피처 페이지 본문 → v2 draft 포맷)
2. 노트 섹션 보존 + 작성자 메타 주석 (`<!-- author: <user>, <date> -->`)
3. 새 feature_id 부여 (`feature_id.py assign`)
4. 새 PDF 페이지 생성 (`notion-create-pages`)
5. 각 소스 페이지의 property 갱신:
   - `migrated_to` ← 새 페이지 URL
   - `archived` ← true

### 5. idempotency

스크립트는 `archived=true` 페이지를 `skipped_archived` 로 카운트. 2회 이상 실행해도 동일 그룹이 중복 생성되지 않는다.

### 6. orphan 처리

해시/파일명 모두 없는 페이지는 `migration-report.md` 에 목록으로 출력. 수동으로 새 PDF 페이지에 통합하거나 archived 처리.
````

- [ ] **Step 2: Commit**

```bash
git add skills/pdf-spec-organizer/SKILL.md
git commit -m "docs(skill): document migrate_to_per_pdf workflow"
```

---

## Task 16: Update SKILL.md Phase 2 — `feature_id` assignment hook

**Files:**
- Modify: `skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Locate Phase 2 end**

Phase 2 currently ends with "### 2-4. 중단 정리". We add a 2-5 step right after that.

- [ ] **Step 2: Insert `### 2-5. feature_id 확정`**

Add at the end of Phase 2 section (before "## Phase 3"):

```markdown
### 2-5. feature_id 확정

Phase 2 의 모든 분기(split/merge/rename) 가 확정되면 `feature_id.py assign` 으로 UUID 부여:

```bash
python3 "${SCRIPTS}/feature_id.py" assign \
  --features-file "${WORK_DIR}/features.json"
```

`feature_id` 는 해당 피처의 라이프타임 동안 변하지 않는다:
- **rename**: 기존 id 유지
- **split**: 원본 id 는 남은 피처가 가져감, 분리된 새 피처는 새 id
- **merge**: 병합된 id 중 하나 채택, 다른 id 는 features.json 의 `merged_into` 필드에 기록 (추후 Relation 생성 시 참조)

Phase 5 퍼블리시 시 각 Toggle 상단에 `<!-- feature_id: <uuid> -->` 주석으로 고정된다.
```

- [ ] **Step 3: Commit**

```bash
git add skills/pdf-spec-organizer/SKILL.md
git commit -m "feat(skill): add feature_id assignment step at end of Phase 2"
```

---

## Task 17: End-to-end smoke test via a fixture PDF

**Files:**
- Create: `skills/pdf-spec-organizer/scripts/tests/test_e2e_toggle_render.py`

**Context:** This is an integration test of the data-path scripts (no Notion MCP). It feeds a fixture features.json + missing.json through `feature_id.py assign`, a hand-written toggle-renderer helper (defined inline), `note_merger`, and `page_publisher chunk`, verifying the final chunks are well-formed.

- [ ] **Step 1: Write failing test**

Create `scripts/tests/test_e2e_toggle_render.py`:

```python
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
            "--input", str(draft_file), "--max-blocks", "50")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert len(out["chunks"]) >= 1
    for c in out["chunks"]:
        assert c["block_count"] <= 50
        assert "publish_sentinel" in c["markdown"]

    # 5) verify feature_ids survive round-trip via extract
    r = run(str(SCRIPTS_DIR / "feature_id.py"), "extract-from-stdin",
            stdin=draft)
    extracted = json.loads(r.stdout)
    expected_ids = {f["feature_id"] for f in features["features"]}
    assert set(extracted["feature_ids"]) == expected_ids
```

- [ ] **Step 2: Run test**

Run: `cd skills/pdf-spec-organizer && python3 -m pytest scripts/tests/test_e2e_toggle_render.py -v`
Expected: PASS (all helpers already built in earlier tasks).

- [ ] **Step 3: Commit**

```bash
git add skills/pdf-spec-organizer/scripts/tests/test_e2e_toggle_render.py
git commit -m "test: e2e pipeline from features.json through chunked draft"
```

---

## Task 18: Update README.md — v2 behavior + migration instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README**

Run: `head -60 README.md` to understand scope.

- [ ] **Step 2: Append v2 section**

Append at end of `README.md` (preserve existing content; add after last section):

````markdown

## v2 변경사항 (2026-04-20)

### 1 PDF = 1 Notion 페이지

기존: 피처마다 개별 페이지 생성 → DB 가 혼잡.
v2: PDF 1개 = 페이지 1개. 피처는 Toggle 블록으로 접혀있음. 필요할 때만 펼쳐서 확인.

### 노트 보존

`/spec-from-pdf` 를 같은 PDF 로 다시 실행해도 iOS/Android/공통 노트는 보존된다. `feature_id` 기반 병합으로 피처 rename 후에도 노트 매칭됨.

### 부분 퍼블리시 재개

Phase 5 도중 실패한 경우 `/spec-resume --resume-latest` 로 **중단된 chunk 부터** 이어서 publish. 전체 재실행 불필요.

### `/spec-update` 피처 단위 편집

```
/spec-update <page-url> --feature="<피처명>"
```
해당 Toggle 블록만 열어서 편집 + 병합. 공백/괄호/슬래시(`(A/B)`) 피처명도 안전.

### 마이그레이션

v1 에서 이미 생성된 피처 페이지가 있다면:

1. DB 에 property 추가 (`migrated_to`, `archived`)
2. `/spec-resume` 또는 새 `/spec-migrate` (해당 workflow) 에서 안내대로 진행
3. 자세한 내용: `skills/pdf-spec-organizer/SKILL.md` 의 "마이그레이션" 섹션

### 기존 커맨드는 동일

`/spec-from-pdf`, `/spec-update`, `/spec-resume` 슬래시 이름은 유지. 동작만 v2 로 바뀜.
````

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): document v2 per-PDF page behavior and migration"
```

---

## Task 19: Update CHANGELOG.md — v0.2.0 entry

**Files:**
- Modify: `CHANGELOG.md` (or create if absent)

- [ ] **Step 1: Check existence**

Run: `ls CHANGELOG.md 2>/dev/null`
If absent, create with standard "# Changelog" header.

- [ ] **Step 2: Prepend v0.2.0 entry**

Add near top:

```markdown
## v0.2.0 — 2026-04-20

### Changed
- `pdf-spec-organizer`: 1 PDF = 1 Notion page (with features as Toggle blocks). v1 per-feature page behavior removed.
- `/spec-update`: new `--feature="<name>"` flag for toggle-level edit.
- `/spec-resume`: partial-append resume via `publish_state` + sentinel markers.
- Notion page body format updated: `feature_id`, `notes_*_start|end`, `publish_sentinel` markers.

### Added
- `scripts/feature_id.py` — UUID4 generation + name resolution.
- `scripts/note_extractor.py` — parse notes by `feature_id`.
- `scripts/note_merger.py` — inject preserved notes into new draft.
- `scripts/page_publisher.py` — chunked block payload + sentinel-based resume cursor.
- `scripts/migrate_to_per_pdf.py` — one-time consolidation planner (dry-run).
- `draft_registry.py`: `page_id`, `publish_state` fields, `partial_success` status.

### Migration
- v1 per-feature pages are consolidated via `migrate_to_per_pdf.py` dry-run + SKILL-orchestrated apply.
- New DB properties required: `migrated_to` (URL), `archived` (Checkbox).
- v1 drafts (`phase: 4`) fall back to full re-publish on `/spec-resume`.
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): v0.2.0 entry for per-PDF page redesign"
```

---

## Task 20: Run full test suite

**Files:** none

- [ ] **Step 1: Run all pdf-spec-organizer tests**

```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer && \
  python3 -m pytest scripts/tests/ -v
```
Expected: all PASS. No regressions in existing `test_pdf_hash.py`, `test_ocr_fallback.py`, etc.

- [ ] **Step 2: If any test fails**

Fix the root cause in source (not the test) before proceeding. Commit fix separately.

- [ ] **Step 3: Tag milestone (optional)**

```bash
git tag v0.2.0-plan-complete
```

---

## Post-implementation

After all 20 tasks are complete, the implementation matches the spec. Before merging:

1. Manually run `/spec-from-pdf` against a fixture PDF to verify end-to-end behavior through the Notion MCP (the scripts' tests don't exercise MCP; a smoke test in a throwaway Notion DB is recommended).
2. Run `migrate_to_per_pdf.py --dry-run` against the team's actual DB dump to verify orphan list is empty or understood.
3. Apply migration (SKILL-orchestrated).
4. Open the migrated pages and confirm notes, feature_id markers, and sentinel blocks round-trip correctly.
