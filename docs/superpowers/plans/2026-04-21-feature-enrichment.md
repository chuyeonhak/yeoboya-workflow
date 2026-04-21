# Feature Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pdf-spec-organizer` v0.4.0 으로 올리며, Phase 3 (누락 체크) 직후 "피처 메타 정보 생성" 단계 (Phase 3.5) 를 추가한다. Claude 가 `project-context.md` + `Explore` subagent 탐색 결과를 바탕으로 각 피처에 **예상 기간 / 타팀 의존성 / 기획 누락 / 타팀 요청사항** 메타를 생성하고, Phase 4 초안 Toggle 에 `<!-- meta_start|end -->` 블록으로 주입한다. Phase 5 에서 Notion 페이지 본문에 "📊 개발 계획 메타" 섹션으로 퍼블리시된다.

**Architecture:**
- Python 레이어: `enrich_features.py` (신규) 가 I/O (config 로드, project-context 절삭, features.json metadata 병합, Claude JSON 파싱) 담당. `note_extractor.py` / `note_merger.py` 는 `<!-- meta_start|end -->` 블록도 추출/병합하도록 확장.
- SKILL.md 레이어: Phase 3.5 신규 섹션이 Claude 에게 Explore subagent spawn → 메타 JSON 생성 → `enrich_features.py` 호출로 features.json 에 병합 지시. Phase 4 초안 렌더러는 meta 섹션 포함 포맷 사용.
- 데이터 레이어: `features.json` 의 각 피처에 `metadata` 객체 (estimated_effort / external_dependencies / planning_gaps / cross_team_requests) 추가. 초안 md 본문에 `<!-- meta_start|end -->` 블록 포함.

**Tech Stack:** Python 3 (PyYAML 이미 사용 중), pytest, Markdown, Bash. Claude Code 내장 `Explore` subagent + `superpowers:dispatching-parallel-agents` 원칙.

**Spec reference:** `docs/superpowers/specs/2026-04-21-feature-enrichment-design.md`

---

## File Structure Overview

| 경로 | 유형 | 이번 플랜에서 |
|---|---|---|
| `skills/pdf-spec-organizer/scripts/enrich_features.py` | 신규 | Python CLI. project-context 로드 + features.json metadata 병합 |
| `skills/pdf-spec-organizer/scripts/tests/test_enrich_features.py` | 신규 | pytest |
| `skills/pdf-spec-organizer/scripts/note_extractor.py` | 수정 | `<!-- meta_start|end -->` 블록도 feature_id 별 추출 |
| `skills/pdf-spec-organizer/scripts/note_merger.py` | 수정 | meta 섹션도 병합 (사용자 편집 우선) |
| `skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py` | 수정 | meta 추출 테스트 추가 |
| `skills/pdf-spec-organizer/scripts/tests/test_note_merger.py` | 수정 | meta 병합 테스트 추가 |
| `skills/pdf-spec-organizer/references/project-context-template.md` | 신규 | 사용자가 복사해서 쓸 템플릿 |
| `skills/pdf-spec-organizer/references/review-format.md` | 수정 | "메타 섹션 포맷" + Phase 3.5 UI 예시 추가 |
| `skills/pdf-spec-organizer/SKILL.md` | 수정 | Phase 3.5 섹션 신규 + Phase 4/5/Resume/Update 확장 |
| `yeoboya-workflow.config.json.example` | 수정 | `project_context_path` + `codebase_roots` 예시 |
| `.claude-plugin/plugin.json` | 수정 | version 0.3.0 → 0.4.0 |
| `CHANGELOG.md` | 수정 | `[0.4.0] - 2026-04-21` 엔트리 |
| `README.md` | 수정 | "프로젝트 컨텍스트 셋업" 섹션 + `--diff` 관련 설명 없음 (이 feature 에는 없음) |

**Commit 전략:** 7개 논리 커밋. 각 커밋 후 pytest green 유지 (총 18 → 신규 추가).

---

## Commit 1 — `enrich_features.py` 뼈대 + 단위 테스트 (TDD)

### Task 1: 실패하는 테스트 `test_enrich_features.py` 작성

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_enrich_features.py`

- [ ] **Step 1: 테스트 파일 작성**

아래 내용을 Write 도구로 `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_enrich_features.py` 에 저장:

```python
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
    ctx.write_text("# Project Context\n" + "\n".join(f"line {i}" for i in range(1000)))
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest tests/test_enrich_features.py -v 2>&1 | tail -20
```

Expected: 전체 실패. "ModuleNotFoundError" 또는 "FileNotFoundError: enrich_features.py" 등.

### Task 2: `enrich_features.py` 신규 작성

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/enrich_features.py`

- [ ] **Step 1: 스크립트 작성**

Write 도구로 `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/enrich_features.py` 에 저장:

```python
"""Feature metadata enrichment helper for pdf-spec-organizer.

Two subcommands:

  load-context --path <project-context.md>
    Loads a project-context.md, truncates at 500 lines, and emits JSON
    describing the content. Used by SKILL.md's Phase 3.5-a.

  merge-metadata --features-file <features.json> --metadata <meta.json>
    Merges a Claude-generated metadata map into features.json. Accepts
    malformed metadata JSON and falls back to an empty metadata shape
    per affected feature so Phase 4 can continue.

The Explore subagent orchestration and the Claude metadata-generation
prompt live in SKILL.md — this script handles filesystem I/O only.
"""
import argparse
import json
import sys
from pathlib import Path

EMPTY_METADATA = {
    "estimated_effort": "",
    "external_dependencies": [],
    "planning_gaps": [],
    "cross_team_requests": [],
}

MAX_CONTEXT_LINES = 500


def cmd_load_context(args) -> int:
    path = Path(args.path).expanduser()
    if not path.exists():
        print(json.dumps({"skip": True, "reason": "not_found", "path": str(path)}, ensure_ascii=False))
        return 0
    raw = path.read_text()
    if not raw.strip():
        print(json.dumps({"skip": True, "reason": "empty", "path": str(path)}, ensure_ascii=False))
        return 0
    lines = raw.splitlines()
    truncated = len(lines) > MAX_CONTEXT_LINES
    kept = lines[:MAX_CONTEXT_LINES]
    print(json.dumps({
        "skip": False,
        "truncated": truncated,
        "line_count": len(kept),
        "total_line_count": len(lines),
        "content": "\n".join(kept),
        "path": str(path),
    }, ensure_ascii=False))
    return 0


def _parse_metadata(meta_text: str) -> tuple[dict, bool]:
    """Return (metadata_map, parsed_ok). On failure returns ({}, False)."""
    try:
        data = json.loads(meta_text)
    except json.JSONDecodeError:
        return {}, False
    if not isinstance(data, dict):
        return {}, False
    return data, True


def _normalise_entry(raw) -> dict:
    if not isinstance(raw, dict):
        return dict(EMPTY_METADATA)
    out = dict(EMPTY_METADATA)
    if isinstance(raw.get("estimated_effort"), str):
        out["estimated_effort"] = raw["estimated_effort"]
    if isinstance(raw.get("external_dependencies"), list):
        out["external_dependencies"] = raw["external_dependencies"]
    if isinstance(raw.get("planning_gaps"), list):
        out["planning_gaps"] = raw["planning_gaps"]
    if isinstance(raw.get("cross_team_requests"), list):
        out["cross_team_requests"] = raw["cross_team_requests"]
    return out


def cmd_merge_metadata(args) -> int:
    features_path = Path(args.features_file).expanduser()
    meta_path = Path(args.metadata).expanduser()
    features = json.loads(features_path.read_text())
    meta_text = meta_path.read_text() if meta_path.exists() else ""
    meta_map, parsed_ok = _parse_metadata(meta_text)
    touched = 0
    fallback = 0
    for feat in features.get("features", []):
        if feat.get("excluded"):
            continue
        fid = feat.get("feature_id")
        if not fid:
            continue
        if parsed_ok and fid in meta_map:
            feat["metadata"] = _normalise_entry(meta_map[fid])
            touched += 1
        else:
            feat["metadata"] = dict(EMPTY_METADATA)
            fallback += 1
    features_path.write_text(json.dumps(features, ensure_ascii=False, indent=2))
    print(json.dumps({
        "parsed_ok": parsed_ok,
        "touched": touched,
        "fallback": fallback,
    }, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="enrich_features")
    sub = ap.add_subparsers(dest="cmd", required=True)

    lc = sub.add_parser("load-context")
    lc.add_argument("--path", required=True)
    lc.set_defaults(func=cmd_load_context)

    mm = sub.add_parser("merge-metadata")
    mm.add_argument("--features-file", required=True)
    mm.add_argument("--metadata", required=True)
    mm.set_defaults(func=cmd_merge_metadata)

    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 테스트 실행 — 전부 통과**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest tests/test_enrich_features.py -v 2>&1 | tail -20
```

Expected: `6 passed` (5개 case + 1개 fallback case).

### Task 3: 기존 pytest 전체 회귀 확인

- [ ] **Step 1: 전체 테스트 실행**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest -v 2>&1 | tail -10
```

Expected: 이전 18 + 신규 6 = **24 passed**. 기존 테스트 모두 green 유지.

### Task 4: Commit 1

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/enrich_features.py skills/pdf-spec-organizer/scripts/tests/test_enrich_features.py && git commit -m "$(cat <<'EOF'
feat(skill): enrich_features.py CLI for Phase 3.5 metadata I/O

Two subcommands wired for SKILL.md orchestration:
- load-context: read project-context.md, cap at 500 lines, emit JSON
- merge-metadata: inject Claude-generated metadata into features.json,
  fall back to empty structure on parse failure, skip excluded features

Explore subagent orchestration and the Claude prompt live in SKILL.md;
this script is the I/O seam only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Commit 2 — `note_extractor.py` / `note_merger.py` meta 섹션 지원 (TDD)

### Task 5: `test_note_extractor.py` 에 meta 추출 케이스 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py`

- [ ] **Step 1: 파일 끝에 새 테스트 2개 append**

Edit 도구 사용. `old_string` 으로 파일의 **마지막 테스트** 마지막 줄 (예: `assert feat["android_empty"] is True`) 을 잡고, `new_string` 으로 그 줄 + 아래 신규 테스트를 붙여서 교체:

`old_string`:
```python
    out = json.loads(r.stdout)
    feat = out["features"]["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    assert feat["android_empty"] is True
```

`new_string`:
```python
    out = json.loads(r.stdout)
    feat = out["features"]["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    assert feat["android_empty"] is True


def test_extract_captures_meta_block():
    content = """
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
<!-- meta_start -->
#### 📊 개발 계획 메타
**예상 기간:** iOS 2일
<!-- meta_end -->

<!-- notes_ios_start -->
ios stuff
<!-- notes_ios_end -->
"""
    r = run_ext(content)
    out = json.loads(r.stdout)
    feat = out["features"]["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    assert "예상 기간" in feat["meta"]
    assert feat["meta_empty"] is False


def test_extract_flags_empty_meta_block():
    content = """
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
<!-- meta_start -->
<empty-block/>
<!-- meta_end -->
"""
    r = run_ext(content)
    out = json.loads(r.stdout)
    feat = out["features"]["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    assert feat["meta_empty"] is True
    assert feat["meta"].strip() == ""
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest tests/test_note_extractor.py -v 2>&1 | tail -20
```

Expected: 신규 2 테스트 실패 (`KeyError: 'meta'` 또는 `feat["meta_empty"]`). 기존 6개는 pass.

### Task 6: `note_extractor.py` 에 meta 섹션 지원 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/note_extractor.py`

- [ ] **Step 1: `SECTION_NAMES` 확장 + meta 정규표현식 추가**

Edit 도구:

`old_string`:
```python
SECTION_NAMES = ("ios", "android", "common")


def _section_re(name: str) -> re.Pattern:
    return re.compile(
        rf"<!--\s*notes_{name}_start\s*-->(.*?)<!--\s*notes_{name}_end\s*-->",
        re.DOTALL,
    )
```

`new_string`:
```python
SECTION_NAMES = ("ios", "android", "common")
META_RE = re.compile(
    r"<!--\s*meta_start\s*-->(.*?)<!--\s*meta_end\s*-->",
    re.DOTALL,
)


def _section_re(name: str) -> re.Pattern:
    return re.compile(
        rf"<!--\s*notes_{name}_start\s*-->(.*?)<!--\s*notes_{name}_end\s*-->",
        re.DOTALL,
    )
```

- [ ] **Step 2: `_strip_known_blocks` 에 META 도 제거**

Edit 도구:

`old_string`:
```python
def _strip_known_blocks(segment: str) -> str:
    out = segment
    for name in SECTION_NAMES:
        out = _section_re(name).sub("", out)
    out = SENTINEL_RE.sub("", out)
    out = FEATURE_ID_RE.sub("", out)
    return out.strip()
```

`new_string`:
```python
def _strip_known_blocks(segment: str) -> str:
    out = segment
    for name in SECTION_NAMES:
        out = _section_re(name).sub("", out)
    out = META_RE.sub("", out)
    out = SENTINEL_RE.sub("", out)
    out = FEATURE_ID_RE.sub("", out)
    return out.strip()
```

- [ ] **Step 3: `extract` 함수에서 meta 섹션도 뽑아 각 feature 에 저장**

Edit 도구:

`old_string`:
```python
        feat = {}
        for name in SECTION_NAMES:
            m = _section_re(name).search(segment)
            content = m.group(1).strip() if m else ""
            is_empty = _is_empty(content)
            # If marked as empty, strip the empty-block tag and clear content
            if is_empty:
                content = re.sub(r"<empty-block/>", "", content).strip()
            feat[name] = content
            feat[f"{name}_empty"] = is_empty
        # stray = everything except feature_id marker, note sections, sentinels, and the first line after feature_id
        stray = _strip_known_blocks(segment)
        feat["stray"] = stray
        result["features"][fid] = feat
```

`new_string`:
```python
        feat = {}
        for name in SECTION_NAMES:
            m = _section_re(name).search(segment)
            content = m.group(1).strip() if m else ""
            is_empty = _is_empty(content)
            # If marked as empty, strip the empty-block tag and clear content
            if is_empty:
                content = re.sub(r"<empty-block/>", "", content).strip()
            feat[name] = content
            feat[f"{name}_empty"] = is_empty
        # meta: the <!-- meta_start|end --> block. Empty if absent OR only
        # contains the <empty-block/> placeholder.
        m = META_RE.search(segment)
        if m:
            meta_inner = m.group(1).strip()
            meta_empty = _is_empty(meta_inner)
            if meta_empty:
                meta_inner = re.sub(r"<empty-block/>", "", meta_inner).strip()
            feat["meta"] = meta_inner
            feat["meta_empty"] = meta_empty
        else:
            feat["meta"] = ""
            feat["meta_empty"] = True
        # stray = everything except feature_id marker, note sections, meta, sentinels
        stray = _strip_known_blocks(segment)
        feat["stray"] = stray
        result["features"][fid] = feat
```

- [ ] **Step 4: 테스트 재실행 — 전부 통과**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest tests/test_note_extractor.py -v 2>&1 | tail -20
```

Expected: `8 passed` (기존 6 + 신규 2).

### Task 7: `test_note_merger.py` 에 meta 병합 케이스 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_note_merger.py`

- [ ] **Step 1: 파일 끝에 테스트 2개 append**

Edit 도구:

`old_string`:
```python
    assert "<!-- stray: preserved -->" in merged
    assert "manual user addition" in merged
```

`new_string`:
```python
    assert "<!-- stray: preserved -->" in merged
    assert "manual user addition" in merged


def test_merge_injects_preserved_meta_section(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- meta_start -->
<empty-block/>
<!-- meta_end -->

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
                "stray": "",
                "meta": "**예상 기간:** iOS 2일", "meta_empty": False,
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "**예상 기간:** iOS 2일" in merged


def test_merge_leaves_empty_meta_as_placeholder(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- meta_start -->
<empty-block/>
<!-- meta_end -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                "ios": "", "ios_empty": True,
                "android": "", "android_empty": True,
                "common": "", "common_empty": True,
                "stray": "",
                "meta": "", "meta_empty": True,
            }
        }
    }))
    r = run_merge(draft, notes)
    merged = draft.read_text()
    # meta block remains as empty-block placeholder
    assert "<!-- meta_start -->" in merged
    assert "<!-- meta_end -->" in merged
    assert "<empty-block/>" in merged
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest tests/test_note_merger.py -v 2>&1 | tail -20
```

Expected: 신규 `test_merge_injects_preserved_meta_section` 실패 (preserved 메타 텍스트가 draft 에 없음), 기존 3개는 pass.

### Task 8: `note_merger.py` 에 meta 병합 로직 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/note_merger.py`

- [ ] **Step 1: `SECTION_NAMES` 위에 meta 교체 헬퍼 추가**

Edit 도구:

`old_string`:
```python
SECTION_NAMES = ("ios", "android", "common")


def _replace_section(segment: str, name: str, new_inner: str) -> str:
    pat = re.compile(
        rf"(<!--\s*notes_{name}_start\s*-->)(.*?)(<!--\s*notes_{name}_end\s*-->)",
        re.DOTALL,
    )
    replacement = f"\\1\n{new_inner}\n\\3" if new_inner.strip() else "\\1\n<empty-block/>\n\\3"
    return pat.sub(replacement, segment, count=1)
```

`new_string`:
```python
SECTION_NAMES = ("ios", "android", "common")

META_PAT = re.compile(
    r"(<!--\s*meta_start\s*-->)(.*?)(<!--\s*meta_end\s*-->)",
    re.DOTALL,
)


def _replace_section(segment: str, name: str, new_inner: str) -> str:
    pat = re.compile(
        rf"(<!--\s*notes_{name}_start\s*-->)(.*?)(<!--\s*notes_{name}_end\s*-->)",
        re.DOTALL,
    )
    replacement = f"\\1\n{new_inner}\n\\3" if new_inner.strip() else "\\1\n<empty-block/>\n\\3"
    return pat.sub(replacement, segment, count=1)


def _replace_meta(segment: str, new_inner: str) -> str:
    replacement = f"\\1\n{new_inner}\n\\3" if new_inner.strip() else "\\1\n<empty-block/>\n\\3"
    return META_PAT.sub(replacement, segment, count=1)
```

- [ ] **Step 2: `merge` 함수에서 meta 도 교체**

Edit 도구:

`old_string`:
```python
        if n:
            for name in SECTION_NAMES:
                if not n.get(f"{name}_empty", True):
                    feat_segment = _replace_section(feat_segment, name, n[name])
            if n.get("stray", "").strip():
```

`new_string`:
```python
        if n:
            if not n.get("meta_empty", True):
                feat_segment = _replace_meta(feat_segment, n.get("meta", ""))
            for name in SECTION_NAMES:
                if not n.get(f"{name}_empty", True):
                    feat_segment = _replace_section(feat_segment, name, n[name])
            if n.get("stray", "").strip():
```

- [ ] **Step 3: orphan 노트 섹션에 meta 도 포함**

Edit 도구:

`old_string`:
```python
    if orphan_ids:
        merged = merged.rstrip() + "\n\n## 이전 노트 (제거된 피처)\n"
        for fid in orphan_ids:
            feat = notes["features"][fid]
            merged += f"\n### feature_id: {fid}\n"
            for name in SECTION_NAMES:
                if not feat.get(f"{name}_empty", True):
                    merged += f"\n**{name}:**\n{feat[name].strip()}\n"
```

`new_string`:
```python
    if orphan_ids:
        merged = merged.rstrip() + "\n\n## 이전 노트 (제거된 피처)\n"
        for fid in orphan_ids:
            feat = notes["features"][fid]
            merged += f"\n### feature_id: {fid}\n"
            if not feat.get("meta_empty", True) and feat.get("meta", "").strip():
                merged += f"\n**meta:**\n{feat['meta'].strip()}\n"
            for name in SECTION_NAMES:
                if not feat.get(f"{name}_empty", True):
                    merged += f"\n**{name}:**\n{feat[name].strip()}\n"
```

- [ ] **Step 4: 테스트 재실행 — 전부 통과**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest tests/test_note_merger.py tests/test_note_extractor.py -v 2>&1 | tail -20
```

Expected: note_merger 5 + note_extractor 8 = **13 passed**.

### Task 9: 전체 회귀 확인

- [ ] **Step 1: pytest 전체**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest -v 2>&1 | tail -10
```

Expected: 18 (기존) + 6 (enrich_features) + 2 (note_extractor meta) + 2 (note_merger meta) = **28 passed**.

### Task 10: Commit 2

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/note_extractor.py skills/pdf-spec-organizer/scripts/note_merger.py skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py skills/pdf-spec-organizer/scripts/tests/test_note_merger.py && git commit -m "$(cat <<'EOF'
feat(skill): note_extractor/merger support <!-- meta_start|end --> blocks

Phase 3.5 writes a "📊 개발 계획 메타" block per feature Toggle. Extend
the preservation pipeline so /spec-update and Phase 5 overwrite paths keep
user edits to the meta block on par with the ios/android/common note
sections: treat empty → <empty-block/> placeholder, treat non-empty →
inject preserved text, orphan features surface their meta under the
"이전 노트" footer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Commit 3 — 템플릿 / Config / plugin.json

### Task 11: `references/project-context-template.md` 신규 작성

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/project-context-template.md`

- [ ] **Step 1: 파일 작성**

Write 도구로 아래 내용 저장:

```markdown
# Project Context (템플릿)

이 파일을 프로젝트 루트 (또는 `yeoboya-workflow.config.json` 의 `project_context_path` 로 지정한 경로)에 복사해 사용한다. 섹션은 **권장** 수준이며, 팀이 필요에 따라 추가/축소할 수 있다. Claude 는 **있는 만큼** 참고한다.

최대 **500 줄** 까지 사용된다. 그 이상이면 절삭되고 경고가 표시된다.

---

# Project Context

## Team
- iOS: <인원수, 예: 2명 (Junior 1, Mid 1)>
- Android: <인원수>
- 백엔드: <조직 정보, Slack 채널 등>
- 디자인: <Figma/Notion 등>
- QA: <주기/회의>

## Current Sprint / Roadmap
- <현재 스프린트 / 분기 목표>
- <진행 중 프로젝트 / 이미 착수된 피처>

## Past Effort References
기간 추정 calibration 의 근간. 실측 기반으로 업데이트 권장.

- 간단 UI (기본 컴포넌트 조합): iOS 1일, Android 1일
- 신규 플로우 (2-3 화면 + API 연동): iOS 3-5일, Android 3-5일
- A/B 테스트 추가: +1일 (실험 플랫폼 연동 오버헤드)
- 네이티브 기능 (카메라/권한/결제): iOS 2-3일, Android 3-5일

## External Teams & Channels
- 백엔드: Slack #backend, 리드 @<handle>, API 변경은 최소 1주 전 요청
- 디자인: Notion "디자인 리소스 DB", Figma 소스 있음. 새 스타일 요청은 2-3일
- QA: 매주 월 QA 회의, 새 피처는 전주 금요일까지 요청
- 데이터/분석: (옵션) Amplitude/GA 연동 담당자

## Known Constraints
- 플랫폼 최소 지원: iOS <version>+, Android API <version>+
- 푸시: <FCM/APNs, 중앙화 정책>
- 결제: <IAP/PG 정책>
- 그 외 전사 정책 (보안/개인정보/접근성 등)
```

### Task 12: `yeoboya-workflow.config.json.example` 업데이트

**Files:**
- Modify: `/Users/chuchu/testPlugin/yeoboya-workflow.config.json.example`

- [ ] **Step 1: 예시 교체**

Edit 도구:

`old_string`:
```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "<your-feature-db-id>",
    "notion_data_source_id": "<your-data-source-id>",
    "parent_page_id": "<your-parent-page-id>"
  }
}
```

`new_string`:
```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "<your-feature-db-id>",
    "notion_data_source_id": "<your-data-source-id>",
    "parent_page_id": "<your-parent-page-id>",
    "project_context_path": "./docs/project-context.md",
    "codebase_roots": {
      "ios": "<optional: absolute or ~-expanded path to iOS repo>",
      "android": "<optional: absolute or ~-expanded path to Android repo>"
    }
  }
}
```

### Task 13: `plugin.json` version bump

**Files:**
- Modify: `/Users/chuchu/testPlugin/.claude-plugin/plugin.json`

- [ ] **Step 1: version 필드 교체**

Edit 도구:

`old_string`:
```json
  "version": "0.3.0",
```

`new_string`:
```json
  "version": "0.4.0",
```

### Task 14: Commit 3

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/references/project-context-template.md yeoboya-workflow.config.json.example .claude-plugin/plugin.json && git commit -m "$(cat <<'EOF'
feat(config): project-context template + codebase_roots config surface

Adds the project-context.md template teams copy into their repo and
extends the sample config with project_context_path + codebase_roots.
Bumps plugin version to 0.4.0.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Commit 4 — `references/review-format.md` 포맷 규약 확장

### Task 15: 초안 파일 구조에 meta 섹션 삽입

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md`

- [ ] **Step 1: Toggle 예시에 meta 블록 추가**

Edit 도구:

`old_string`:
```markdown
	**누락 체크:**
	- [ ] 에러 케이스 — 명시 없음
	- [x] 빈 상태 — 명시됨

	<!-- notes_ios_start -->
```

`new_string`:
```markdown
	**누락 체크:**
	- [ ] 에러 케이스 — 명시 없음
	- [x] 빈 상태 — 명시됨

	<!-- meta_start -->
	#### 📊 개발 계획 메타

	**예상 기간:** iOS 2-3일, Android 2-3일

	**타팀 의존성:**
	- 🚫 [백엔드] 알림 설정 저장 API — blocking
	  - POST /users/me/notification-settings

	**기획 누락 포인트:**
	- API 실패 시 UI 처리 정의 없음
	- 이전 설정값 출처 명시 없음

	**타팀 요청 사항:**
	- [디자인] 토글 off 상태 스타일 확정 (개발 착수 전)

	> ℹ️ Claude 가 project-context 기반으로 제안한 값입니다. Phase 4 에서 검토/수정하세요.
	<!-- meta_end -->

	<!-- notes_ios_start -->
```

### Task 16: "왜 마커가 많은가" 섹션에 meta 마커 항목 추가

- [ ] **Step 1: 설명 라인 추가**

Edit 도구:

`old_string`:
```markdown
- `<!-- feature_id: ... -->` — Toggle rename/reorder 후에도 노트 보존 병합이 가능한 안정적 식별자.
- `<!-- notes_*_start|end -->` — `/spec-update` 시 해당 섹션만 정확히 교체/추출.
- `<!-- publish_sentinel: ... -->` — Phase 5 chunked publish 재개용 커서.
- `<!-- plugin-state ... -->` — `/spec-resume` phase 판정용. Notion 퍼블리시 시에는 필터링 후 제거.
```

`new_string`:
```markdown
- `<!-- feature_id: ... -->` — Toggle rename/reorder 후에도 노트 보존 병합이 가능한 안정적 식별자.
- `<!-- notes_*_start|end -->` — `/spec-update` 시 해당 섹션만 정확히 교체/추출.
- `<!-- meta_start|end -->` — Phase 3.5 가 생성한 "📊 개발 계획 메타" 섹션 경계. note_extractor/merger 가 노트 섹션과 동일하게 보존한다.
- `<!-- publish_sentinel: ... -->` — Phase 5 chunked publish 재개용 커서.
- `<!-- plugin-state ... -->` — `/spec-resume` phase 판정용. Notion 퍼블리시 시에는 필터링 후 제거.
```

### Task 17: "Phase 별 프롬프트" 섹션 맨 아래에 Phase 3.5 UI 규약 추가

- [ ] **Step 1: 파일 끝에 신규 섹션 append**

Edit 도구:

`old_string` (파일 끝 — 현재 `Phase 3 완료 후:` 로 끝남):
```markdown
Phase 3 완료 후:
```

`new_string`:
```markdown
Phase 3 완료 후:

### 피처 메타 정보 생성 요약 (Phase 3.5)

`project_context_path` 설정이 있을 때 Phase 3 직후 아래 요약이 출력된다:

```
피처 메타 정보 생성 완료 (excluded 제외 <N>개 피처):

  1. <피처명>
     예상 기간: iOS 2-3일, Android 2-3일
     타팀 의존: 백엔드 — 알림 설정 저장 API (blocking)
     기획 누락: API 실패 UI, 이전 설정값 출처
     타팀 요청: 디자인 — 토글 off 상태 (개발 착수 전)

  2. ...

검토/수정은 Phase 4 (개발자 노트) 에서 진행됩니다.
계속하려면 Enter.
```

표시 규칙:
- "(없음)" 으로 표시되는 필드: 해당 피처에서 비어있는 항목
- `codebase_roots` 미설정: 시작 시 한 번만 "기간 추정 신뢰도 하락" 경고 출력
- `project_context_path` 미설정: Phase 3.5 전체 스킵 + "설정 가이드는 README" 경고
- `--fast`: 요약만 출력, Enter 없이 Phase 4 로 진입

#### 메타 섹션 포맷 (초안 md)

각 피처 Toggle 내 `<!-- meta_start -->` ~ `<!-- meta_end -->` 사이. 하위 섹션 순서 고정:
1. `#### 📊 개발 계획 메타` 헤딩
2. `**예상 기간:**` — 자유 문자열. 빈 값이면 "(미정)"
3. `**타팀 의존성:**` — 리스트. blocking → `🚫`, non-blocking → `ℹ️`. 빈 리스트 → "(없음)"
4. `**기획 누락 포인트:**` — 불릿 리스트. 빈 리스트 → "(없음)"
5. `**타팀 요청 사항:**` — 리스트 `[팀] 아이템 (by)`. 빈 리스트 → "(없음)"
6. 마지막에 `> ℹ️ Claude 가 project-context 기반으로 제안한 값입니다. Phase 4 에서 검토/수정하세요.`
```

### Task 18: Commit 4

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/references/review-format.md && git commit -m "$(cat <<'EOF'
docs(format): meta block + Phase 3.5 UI rules in review-format

Toggle draft example now includes a sample 📊 개발 계획 메타 block, marker
catalogue lists <!-- meta_start|end -->, and a new "Phase 3.5" section
documents the terminal summary rendering rules plus the fixed sub-section
ordering for the meta block.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Commit 5 — `SKILL.md` Phase 3.5 섹션 신규

### Task 19: Phase 3 섹션 끝 라인 확인

- [ ] **Step 1: Phase 3 끝 ~ Phase 4 시작 사이 라인 찾기**

Run:
```bash
grep -n "^## Phase 3\|^## Phase 4\|계속하려면 Enter" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: Phase 3 섹션 시작 라인, "계속하려면 Enter" 라인, Phase 4 섹션 시작 라인 번호. Phase 3.5 는 **Phase 4 헤더 바로 위**에 삽입한다.

### Task 20: Phase 3.5 전체 본문 삽입

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Phase 4 헤더 직전에 Phase 3.5 삽입**

Edit 도구. Task 19 에서 찾은 `## Phase 4` 헤더 라인을 기준으로 그 위에 블록 삽입:

`old_string`:
```markdown
## Phase 4 — 개발자 노트 + 미리보기 + 개입 ②
```

`new_string`:
```markdown
## Phase 3.5 — 피처 메타 정보 생성 (v0.4.0)

**왜:** Phase 3 의 고정 체크리스트 누락 체크만으로는 "개발 착수 가능한 스펙" 이 되지 않는다. 이 단계는 `project-context.md` (팀/과거 사례/타팀 채널) 와 iOS/Android 코드베이스(선택) 를 참고해 각 피처에 **예상 기간 / 타팀 의존성 / 기획 누락 포인트 / 타팀 요청사항** 메타 정보를 자동 제안한다. 최종 결정은 Phase 4 에디터에서 개발자가 내린다.

### 3.5-a. 선행 조건 확인

Run:
```bash
CONFIG_PATH="${WORK_DIR}/../yeoboya-workflow.config.json"  # Precondition 2 에서 찾은 경로
CTX_REL=$(python3 -c "
import json, sys
cfg = json.load(open('${CONFIG_PATH}'))
print(cfg.get('pdf_spec_organizer', {}).get('project_context_path', ''))
")
```

`CTX_REL` 이 비어 있으면 아래 경고를 출력하고 **Phase 4 로 곧장 진입**:
```
ℹ️  project_context_path 가 설정되지 않아 피처 메타 정보 생성 스킵.
  설정 가이드: README.md "프로젝트 컨텍스트 셋업"
```

비어 있지 않으면 절대경로로 정규화 후 `enrich_features.py load-context` 로 로드:

```bash
CTX_ABS=$(python3 -c "import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))" "$CTX_REL")
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/enrich_features.py" \
  load-context --path "$CTX_ABS" > "${WORK_DIR}/context.json"
```

결과 `context.json` 의 `skip: true` 이면 위와 동일한 경고 후 Phase 4 진입. `truncated: true` 이면 경고:
```
⚠️  project-context.md 가 <total_line_count> 줄입니다. 앞 500 줄만 사용합니다.
```

`codebase_roots` 가 비어 있으면 한 번만 안내:
```
ℹ️  codebase_roots 가 설정되지 않아 코드 힌트 없이 메타를 생성합니다.
  기간 추정 신뢰도가 낮을 수 있습니다. Phase 4 에서 개발자 검토를 권장합니다.
```

### 3.5-b. 코드베이스 탐색 (Explore subagent)

`codebase_roots` 각 플랫폼 경로가 존재하면, 해당 플랫폼에 속한 `excluded == false` 피처마다 **Claude Code `Explore` subagent** 를 spawn 한다.

병렬화 규칙 (`superpowers:dispatching-parallel-agents` 원칙):
- 대상 피처 수 < 3 → 순차 호출 (Agent 툴 호출을 연속으로)
- 대상 피처 수 ≥ 3 → 플랫폼별로 묶어 **단일 메시지에 여러 Agent 호출** (병렬 dispatch)
- 공통 피처 (`platform` 에 iOS 와 Android 모두 포함) → iOS/Android 양쪽 각각 Explore 1회씩

각 Explore 호출 파라미터:
- `subagent_type`: `"Explore"`
- `description`: `"<피처명> 코드 조사"` (5단어 이내)
- `prompt`: 아래 템플릿에서 생성

```
프로젝트 루트: <codebase_roots.<platform>>
thoroughness: medium

다음 피처가 이 레포에 이미 존재하거나 관련 구조가 있는지 조사하고,
새로 구현할 경우의 복잡도를 200 단어 이내로 요약해 달라.

[피처]
이름: <feature.name>
요약: <feature.summary>
요구사항:
<feature.requirements>

보고에 포함:
1. 유사/관련 코드 경로 (파일명 + 핵심 심볼)
2. 재사용 가능한 컴포넌트 / 보일러플레이트 유무
3. 신규 파일/모듈 대략 개수
4. 기존 코드 패턴과의 충돌 가능성
5. 요약은 200 단어 이내
```

예외/실패 처리:
- Explore 가 에러 반환 또는 2분 timeout → 해당 피처의 해당 플랫폼 보고를 `"(탐색 실패 - skipped)"` 로 두고 계속
- 누적 토큰 사용률이 80% 를 넘었다고 판단되면 이후 spawn 부터 `thoroughness` 를 `"quick"` 으로 강등하고 사용자에게 안내:
  ```
  ⚠️  토큰 한도에 근접해 이후 Explore 호출은 quick 모드로 전환합니다.
  ```

각 피처별 보고(플랫폼별)를 JSON 하나로 모아 `${WORK_DIR}/explore_reports.json` 로 저장:
```json
{
  "<feature_id>": {
    "ios": "<200 word summary>",
    "android": "<200 word summary>"
  }
}
```

### 3.5-c. Claude 메타 정보 생성

`excluded == false` 피처마다 Claude 가 아래 프롬프트로 JSON 메타를 생성하고, 전체를 `${WORK_DIR}/metadata.json` (feature_id → metadata dict) 으로 저장.

프롬프트 (피처 1개당 1회, features.json 의 데이터와 context.json / explore_reports.json 을 합성):

```
다음 정보로 피처의 개발 계획 메타 정보를 JSON 으로 생성.

[피처]
이름: <name>
플랫폼: <platform>
요약: <summary>
요구사항:
<requirements>

[Phase 3 누락 체크 결과]
누락: <missing>
명시: <satisfied>

[프로젝트 컨텍스트]
<context.json.content>

[관련 코드 탐색 결과]  # explore_reports.json 에 해당 feature_id 가 있을 때만
- iOS: <explore_reports[fid].ios>
- Android: <explore_reports[fid].android>

요청 JSON 스키마:
{
  "estimated_effort": "string (플랫폼별 기간 권장)",
  "external_dependencies": [
    {"team": "string", "item": "string", "blocking": true|false, "note": "string"}
  ],
  "planning_gaps": ["string", ...],
  "cross_team_requests": [
    {"team": "string", "item": "string", "by": "string"}
  ]
}

규칙:
- 빈 항목은 [] 또는 "" 허용
- team 은 프로젝트 컨텍스트의 "External Teams & Channels" 에 언급된 이름을 우선 사용
- estimated_effort 는 프로젝트 컨텍스트의 "Past Effort References" 를 참고해 추정
- planning_gaps 는 Phase 3 누락 체크와 중복돼도 무방 (관점이 다름)
- 응답은 위 스키마의 JSON 만. 다른 텍스트 없음.
```

Claude 응답을 JSON 으로 파싱. 파싱 실패하거나 스키마 불일치 시 해당 피처를 스킵(엔트리 제외)하고 `enrich_features.py merge-metadata` 의 fallback 경로에 맡긴다.

누적된 `metadata.json` 을 features.json 에 병합:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/enrich_features.py" \
  merge-metadata \
  --features-file "${WORK_DIR}/features.json" \
  --metadata "${WORK_DIR}/metadata.json"
```

`merge-metadata` 의 stdout JSON 에서:
- `parsed_ok: false` → 전체 JSON 깨짐. 모든 피처가 빈 메타로 fallback 됨
- `touched` / `fallback` 카운트를 다음 단계 요약에 활용

### 3.5-d. 요약 출력

각 피처에 대해 `references/review-format.md` 의 "피처 메타 정보 생성 요약 (Phase 3.5)" 블록을 따라 출력.

- 빈 필드는 "(없음)" 으로 표시
- 파싱 실패로 빈 메타가 된 피처에는 경고 한 줄:
  ```
  ⚠️  <피처명>: Claude 메타 생성 실패, 빈 값으로 계속합니다. Phase 4 에서 수동 작성하세요.
  ```
- `--fast` 모드: 요약만 출력 후 Phase 4 로 진입 (Enter 프롬프트 생략)
- 일반 모드: "계속하려면 Enter." 대기

---

### Task 21: Commit 5

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "$(cat <<'EOF'
feat(skill): Phase 3.5 피처 메타 정보 생성 (Explore subagent)

Inserts a new Phase 3.5 between Phase 3 and Phase 4:
- 3.5-a config/context precondition with load-context JSON protocol
- 3.5-b parallel Explore subagent dispatch per platform (thoroughness
  medium, auto-downgrade to quick on token pressure)
- 3.5-c per-feature Claude metadata prompt + enrich_features.py
  merge-metadata call (fallback on JSON parse failure)
- 3.5-d terminal summary mirroring review-format.md rules

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Commit 6 — SKILL.md Phase 4/5, Resume, Update 확장

### Task 22: Phase 4 초안 md 렌더 확장 — meta 섹션 포함

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

Phase 4 의 "4-2. 초안 md 파일 렌더" 섹션에 meta 섹션 렌더 지시를 추가한다.

- [ ] **Step 1: 4-2 섹션 bullet 목록에 meta 항목 추가**

Run:
```bash
grep -n "4-2\. 초안 md" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Read 로 해당 섹션 확인 후 Edit 도구:

`old_string`:
```markdown
**중요:**
- `<!-- plugin-state -->` 헤더에 `phase: 4`, `pdf_hash`, `source_file`, `created_at`, `publish_state: idle`, `page_id:` (빈 값), `last_block_sentinel_id:` (빈 값) 포함
- 각 피처는 Toggle heading (`### N. <name> {toggle="true"}`) 로 렌더
- 각 Toggle 첫 줄 아래에 `<!-- feature_id: <uuid> -->` 주석 삽입
- iOS / Android / 공통 노트 섹션은 `<!-- notes_*_start/end -->` 마커로 감싸고 **빈 상태** (`<empty-block/>`) 로 렌더
- 각 Toggle 끝에 `<!-- publish_sentinel: feature_<short-id>_done -->` 삽입
- `--fast` 플래그여도 이 Phase 는 생략되지 않음
```

`new_string`:
```markdown
**중요:**
- `<!-- plugin-state -->` 헤더에 `phase: 4`, `pdf_hash`, `source_file`, `created_at`, `publish_state: idle`, `page_id:` (빈 값), `last_block_sentinel_id:` (빈 값) 포함
- 각 피처는 Toggle heading (`### N. <name> {toggle="true"}`) 로 렌더
- 각 Toggle 첫 줄 아래에 `<!-- feature_id: <uuid> -->` 주석 삽입
- **메타 섹션(`<!-- meta_start|end -->`):** Phase 3.5 가 실행됐으면 `features.json[feature].metadata` 를 `references/review-format.md` 의 "메타 섹션 포맷" 규칙대로 렌더. Phase 3.5 스킵 케이스(project_context_path 미설정 등) 에선 `<!-- meta_start -->\n<empty-block/>\n<!-- meta_end -->` 로 빈 상태 렌더 (Update 모드 호환)
- iOS / Android / 공통 노트 섹션은 `<!-- notes_*_start/end -->` 마커로 감싸고 **빈 상태** (`<empty-block/>`) 로 렌더
- 각 Toggle 끝에 `<!-- publish_sentinel: feature_<short-id>_done -->` 삽입
- `--fast` 플래그여도 이 Phase 는 생략되지 않음 (메타 섹션은 Claude 제안값 그대로, 노트 섹션은 빈 상태)
```

### Task 23: Phase 4 미리보기 요약에 메타 완성도 표시

- [ ] **Step 1: 4-5 미리보기 예시 블록 확장**

Run:
```bash
grep -n "### 4-5\. 최종 미리보기\|### 4-6\." /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Edit 도구:

`old_string`:
```markdown
  PDF: <filename>
  피처 7개, 누락 항목 35개, 노트:
    - 앱 시작 플로우 개방: iOS ✓, Android ✗, 공통 ✗
    - 메인화면 비로그인 UI 제어: iOS ✓, Android ✓, 공통 ✗
    ...
```

`new_string`:
```markdown
  PDF: <filename>
  피처 7개, 누락 항목 35개, 상태:
    - 앱 시작 플로우 개방: 메타 ✓, iOS ✓, Android ✗, 공통 ✗
    - 메인화면 비로그인 UI 제어: 메타 ✓, iOS ✓, Android ✓, 공통 ✗
    ...

  (메타 ✓/✗ 는 `<!-- meta_start|end -->` 블록이 비어있지 않은지 여부.
   Phase 3.5 가 스킵됐거나 빈 메타로 fallback 된 피처는 ✗ 로 표시.)
```

### Task 24: Phase 5 요약 로그에 메타 카운트 추가

- [ ] **Step 1: 5-7 결과 요약 부분에 메타 카운트 추가**

Run:
```bash
grep -n "### 5-7\. 결과 요약" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Read 로 해당 블록 확인. Edit 도구:

`old_string`:
```markdown
성공:
```
✓ 퍼블리시 완료:
  <PDF 제목>: https://notion.so/...

초안은 3일 후 자동 삭제됩니다: <draft_path>
```
```

`new_string`:
```markdown
성공:
```
✓ 퍼블리시 완료:
  <PDF 제목>: https://notion.so/...
  피처 <N>개 게시 (메타 생성 <M>개, 웹 필터 제외 <W>개)

초안은 3일 후 자동 삭제됩니다: <draft_path>
```

`<M>` = `features.json` 중 `metadata.estimated_effort` 가 비어있지 않은 피처 수.
`<W>` = `excluded == true and excluded_reason == "web"` 피처 수.
```

### Task 25: Resume 모드에 v0.3 → v0.4 메타 fallback

Resume 섹션(`R-2-b. v2 draft 의 publish_state 별 분기`) 아래, `excluded_ids 복원` 블록 근처에 메타 fallback 지시 추가.

- [ ] **Step 1: 해당 위치 확인**

Run:
```bash
grep -n "excluded_ids 복원\|excluded_ids: \[" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Read 로 해당 블록 확인. Edit 도구로 `excluded_ids 복원` 블록 **직후** 에 신규 단락 삽입:

`old_string`:
```markdown
excluded_ids 가 비어 있거나 키가 없으면 (v0.2 이전 초안) 무시하고 진행. 하위 호환 유지.
```

`new_string`:
```markdown
excluded_ids 가 비어 있거나 키가 없으면 (v0.2 이전 초안) 무시하고 진행. 하위 호환 유지.

**메타 fallback (v0.3 이전 초안):** features.json 의 어떤 피처든 `metadata` 필드가 없으면 아래 빈 구조를 삽입 후 계속:
```json
{"estimated_effort": "", "external_dependencies": [], "planning_gaps": [], "cross_team_requests": []}
```
Resume 는 Phase 3.5 를 **다시 실행하지 않음** — 이미 진행 중인 draft 를 존중. 메타가 필요한 경우 새 `/spec-from-pdf` 실행으로 fresh 초안 생성 필요. 다음 경고 한 줄 출력:
```
ℹ️  v0.3 이하 초안 — 메타 정보 없이 재개합니다. Phase 3.5 재실행이 필요하면 /spec-from-pdf 로 새 실행하세요.
```
```

### Task 26: Update 모드에 meta 섹션 복원 지시 추가

Update 모드(`U-1. 페이지 조회 및 초안 생성`) 섹션의 "페이지 → draft.md 역변환" 주석에 meta 섹션 언급.

- [ ] **Step 1: U-1 역변환 블록 업데이트**

Run:
```bash
grep -n "U-1\. 페이지 조회\|U-2\. feature_name" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Edit 도구:

`old_string`:
```markdown
# 2) 페이지 → draft.md 역변환 (features + notes 를 features.json 스키마로 복원)
# features.json: 각 Toggle 의 feature_id/이름/platform/요구사항/누락 을 복원
# draft.md: review-format.md 포맷으로 재렌더 (preserved 노트 포함)
```

`new_string`:
```markdown
# 2) 페이지 → draft.md 역변환 (features + notes + meta 를 features.json 스키마로 복원)
# features.json: 각 Toggle 의 feature_id/이름/platform/요구사항/누락/metadata 복원
#   - metadata 가 Notion 본문의 meta 섹션에 없으면 빈 구조로 초기화
#   - Update 모드는 Phase 3.5 를 재실행하지 않음 (기존 메타 보존 + 사용자 편집만 허용)
# draft.md: review-format.md 포맷으로 재렌더 (preserved 노트 + preserved meta 포함)
```

- [ ] **Step 2: U-6 병합 퍼블리시에서 meta 섹션 교체 로직 명시**

Run:
```bash
grep -n "U-6\. 병합 퍼블리시\|U-7\." /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Edit 도구:

`old_string`:
```markdown
- 부분 모드 (`FEATURE_NAME` 지정) 면:
  - `notion-update-page command=update_content` 로 해당 Toggle 블록만 검색-교체
  - old_str 은 기존 Toggle 의 `<!-- feature_id: <uuid> -->` 부터 다음 Toggle 의 `<!-- feature_id: ... -->` (또는 페이지 끝) 까지
- 전체 모드:
  - 5-4 (덮어쓰기 노트 보존) 와 동일
```

`new_string`:
```markdown
- 부분 모드 (`FEATURE_NAME` 지정) 면:
  - `notion-update-page command=update_content` 로 해당 Toggle 블록만 검색-교체
  - old_str 은 기존 Toggle 의 `<!-- feature_id: <uuid> -->` 부터 다음 Toggle 의 `<!-- feature_id: ... -->` (또는 페이지 끝) 까지
  - note_extractor/merger 가 `<!-- meta_start|end -->` 도 보존 대상으로 처리한다 (Python 에서 이미 지원)
- 전체 모드:
  - 5-4 (덮어쓰기 노트 보존) 와 동일. meta 블록은 note_merger 가 자동 병합.
```

### Task 27: Commit 6

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "$(cat <<'EOF'
feat(skill): wire meta block into Phase 4/5, Resume, Update

- Phase 4 draft renderer now includes a <!-- meta_start|end --> block
  per Toggle (empty when Phase 3.5 was skipped, pre-filled otherwise).
  Preview summary adds "메타 ✓/✗" alongside ios/android/common flags.
- Phase 5 success log counts meta-enriched features and web-excluded
  features for at-a-glance publish summary.
- Resume gracefully injects an empty metadata struct when reading a
  v0.3 or earlier draft, and does not re-run Phase 3.5.
- /spec-update U-1/U-6 explicitly preserve the meta block through the
  page→draft roundtrip (note_extractor/merger handle it already).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Commit 7 — README, CHANGELOG

### Task 28: CHANGELOG.md `[0.4.0]` 엔트리 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/CHANGELOG.md`

- [ ] **Step 1: 기존 `## [0.3.0]` 블록 위에 신규 `[0.4.0]` 엔트리 삽입**

Edit 도구:

`old_string`:
```markdown
# Changelog

## [0.3.0] - 2026-04-21
```

`new_string`:
```markdown
# Changelog

## [0.4.0] - 2026-04-21

### Added
- Phase 3.5 **피처 메타 정보 생성 단계** — `project_context_path` 가 설정되면 Phase 3 직후 각 피처에 `예상 기간 / 타팀 의존성 / 기획 누락 / 타팀 요청사항` 메타를 자동 제안. 개발자는 Phase 4 에서 검토/수정.
- 코드베이스 탐색에 Claude Code `Explore` subagent 사용 (`superpowers:dispatching-parallel-agents` 원칙으로 피처 3+ 는 병렬 dispatch). 토큰 한도 접근 시 `thoroughness` 를 자동 `quick` 강등.
- `scripts/enrich_features.py` — `load-context` (500줄 절삭) + `merge-metadata` (features.json 병합, JSON 파싱 실패 시 빈 구조 fallback).
- `references/project-context-template.md` — 팀이 복사해서 쓸 템플릿.
- `<!-- meta_start|end -->` 블록이 Phase 4 초안 md 와 Notion Toggle 본문에 포함됨.

### Changed
- `note_extractor.py` / `note_merger.py` 가 `<!-- meta_start|end -->` 블록도 노트 섹션과 동등하게 추출/병합.
- `features.json` 스키마: 각 피처에 `metadata` 객체(`estimated_effort` / `external_dependencies` / `planning_gaps` / `cross_team_requests`) 추가.
- `yeoboya-workflow.config.json.example` 에 `project_context_path` + `codebase_roots` 예시.
- Phase 4 미리보기 요약에 "메타 ✓/✗" 컬럼 추가.
- Phase 5 성공 로그에 메타 생성 카운트 + 웹 필터 제외 카운트 표시.

### Compatibility
- v0.3 이하 draft 를 `/spec-resume` 로 재개하면 `metadata` 필드가 없다 → 빈 구조로 fallback, Phase 3.5 재실행 없음 (경고 출력).
- `project_context_path` 미설정 시 Phase 3.5 전체 스킵 (기존 v0.3 동작 그대로).
- 기존 pytest 회귀 없음 (총 28 tests pass, 신규 10 / 기존 18).

## [0.3.0] - 2026-04-21
```

### Task 29: README.md "프로젝트 컨텍스트 셋업" 섹션 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/README.md`

- [ ] **Step 1: README 에서 "팀 리드 최초 셋업" 섹션 위치 확인**

Run:
```bash
grep -n "^## \|^# " /Users/chuchu/testPlugin/README.md
```

Expected: 각 섹션의 시작 라인. "팀 리드 최초 셋업" 이 있으면 그 아래에, 없으면 "사용법" 같은 주요 섹션 뒤에 삽입.

- [ ] **Step 2: "프로젝트 컨텍스트 셋업" 섹션 신규 추가**

Read 로 README 의 "팀 리드 최초 셋업" (또는 유사) 섹션 찾기. 그 섹션 바로 **뒤**에 아래 블록 삽입.

Edit 도구. `old_string` 으로 해당 섹션의 마지막 줄 (예: 마지막 `` ``` `` 코드블록 닫기) + 그 뒤 빈 줄 + 다음 섹션 헤더 시작까지 잡아서, 아래를 사이에 끼운다:

삽입할 블록:
```markdown

## 프로젝트 컨텍스트 셋업 (v0.4+, 선택)

Phase 3.5 "피처 메타 정보 생성" 을 활성화하려면 팀이 1회 `project-context.md` 를 작성해서 레포에 커밋한다.

1. 템플릿 복사:
   ```bash
   cp skills/pdf-spec-organizer/references/project-context-template.md docs/project-context.md
   ```
2. 팀 구성 / 과거 개발 기간 사례 / 타팀 채널 / 제약 조건 채우기. 자유 마크다운, 500 줄까지 사용됨.
3. `yeoboya-workflow.config.json` 에 경로 선언:
   ```json
   {
     "pdf_spec_organizer": {
       "project_context_path": "./docs/project-context.md",
       "codebase_roots": {
         "ios": "~/repos/myapp-ios",
         "android": "~/repos/myapp-android"
       }
     }
   }
   ```
4. `codebase_roots` 는 **선택**. 있으면 Claude 가 `Explore` subagent 로 레포를 자연어 탐색해 기간 추정 신뢰도를 높인다. 없으면 project-context 만으로 메타를 제안.

설정이 없으면 Phase 3.5 는 스킵되며 v0.3 과 동일하게 동작한다.

```

(주의: 이 삽입 블록은 앞뒤로 빈 줄을 두어 기존 섹션과 분리.)

### Task 30: Commit 7

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add CHANGELOG.md README.md && git commit -m "$(cat <<'EOF'
docs: CHANGELOG v0.4.0 + README project-context setup section

Release note covers the Phase 3.5 metadata pipeline, Explore subagent
integration, features.json schema extension, and the v0.3 resume
compatibility behavior. README gains a new "프로젝트 컨텍스트 셋업"
section that walks the team through copying the template and wiring
project_context_path + codebase_roots in yeoboya-workflow.config.json.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Commit 8 — 검증

### Task 31: 전체 pytest 회귀 테스트

- [ ] **Step 1: 전체 테스트 러너**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && python -m pytest -v 2>&1 | tail -30
```

Expected: **28 passed** (기존 18 + 신규 10 = enrich_features 6 + note_extractor meta 2 + note_merger meta 2).

실패 케이스 발견 시: 어느 커밋에서 깨졌는지 `git bisect` 또는 개별 파일 테스트로 격리 후 수정. 완전 green 확인 후 다음 단계.

### Task 32: 스모크 수동 테스트 절차 (사용자용)

이 태스크는 자동화 대상이 아니다. 사용자가 실제 PDF 와 실제 코드베이스에서 아래 절차를 1회 수행하고 **결과 스크린샷/로그를 공유**해야 완료된다. agent 는 여기까지 오면 다음 안내를 출력하고 종료.

수동 시나리오:

1. **Baseline (v0.3 동작 유지 확인):**
   - `project_context_path` 를 `yeoboya-workflow.config.json` 에서 임시로 제거
   - `/spec-from-pdf ~/Downloads/sample.pdf`
   - Phase 3 후 즉시 Phase 4 진입 확인. meta 섹션은 `<empty-block/>` 로만.
2. **풀 셋업:**
   - `docs/project-context.md` 생성 + config 에 `project_context_path` + `codebase_roots` 설정
   - `/spec-from-pdf ~/Downloads/sample.pdf`
   - Phase 3.5 에서 Explore subagent 호출 진행도 확인 → 메타 요약 출력
   - Phase 4 에디터에서 meta 섹션 편집 후 저장 → Phase 5 완료 확인
   - Notion 페이지에 "📊 개발 계획 메타" 블록 존재 확인
3. **Resume:**
   - Phase 4 에서 에디터 저장 직전에 `Ctrl-C`
   - `/spec-resume --resume-latest` → 메타 섹션이 draft 에 보존됨 확인
4. **Update:**
   - 2번에서 생성한 Notion URL 로 `/spec-update <url> --feature="<피처명>"`
   - 해당 Toggle 의 meta 섹션이 에디터에 그대로 복원됨 확인 → 수정 후 저장 → Notion 반영 확인
5. **JSON 파싱 실패 시뮬레이션 (optional):**
   - 수동 fault injection 은 v0.5 이슈. 스킵 가능.

출력 메시지:
```
✅ 자동 검증 완료 (28 pytest passed). 수동 스모크 시나리오는 사용자가 수행해야 합니다:
  1) Baseline (project_context 미설정 → Phase 3.5 스킵)
  2) 풀 셋업 (project-context + codebase_roots → 메타 생성 + Notion 페이지에 📊 블록)
  3) Resume (Phase 4 중단 후 /spec-resume → 메타 유지)
  4) Update (/spec-update → meta 섹션 보존 편집)

스모크 결과가 확인되면 `git push` 로 v0.4.0 릴리스 준비 가능.
```

---

## Self-Review (실행 전 확인)

### 1. Spec 커버리지 체크

| Spec 요구 | 구현 Task |
|---|---|
| Phase 3.5 신규 (선행 조건 + Explore + Claude 메타 + 요약) | Task 19, 20 |
| `enrich_features.py` load-context (500줄 절삭) | Task 1, 2 |
| `enrich_features.py` merge-metadata (JSON 파싱 fallback) | Task 1, 2 |
| `features.json` metadata 필드 확장 | Task 2 (정의), 20 (SKILL.md 경로) |
| `note_extractor.py` meta 섹션 추출 | Task 5, 6 |
| `note_merger.py` meta 섹션 병합 | Task 7, 8 |
| `references/project-context-template.md` 신규 | Task 11 |
| `references/review-format.md` 메타 섹션 포맷 | Task 15, 16, 17 |
| `yeoboya-workflow.config.json.example` 확장 | Task 12 |
| `plugin.json` version bump | Task 13 |
| SKILL.md Phase 4 초안 md 에 meta 포함 | Task 22 |
| SKILL.md Phase 4 미리보기 메타 완성도 표시 | Task 23 |
| SKILL.md Phase 5 요약 로그 메타 카운트 | Task 24 |
| Resume v0.3 draft → 빈 메타 fallback | Task 25 |
| Update 모드 meta 섹션 보존 | Task 26 |
| `--fast` 모드 처리 | Task 20 (3.5-d), 22 (4-2) |
| 엣지 케이스 (project_context 미설정 등) | Task 20 (3.5-a) |
| CHANGELOG v0.4.0 엔트리 | Task 28 |
| README 프로젝트 컨텍스트 셋업 섹션 | Task 29 |
| pytest 18 회귀 없음 | Task 3, 9, 31 |

누락 없음.

### 2. Placeholder 스캔

- Task 내부에 "TBD/TODO/implement later" 없음 ✓
- 모든 코드 블록에 실제 code 포함 (예: test 코드, Python 스크립트 전문, Edit 의 old/new string) ✓
- 커맨드에 expected output 명시 ✓
- "Similar to Task N" 없음 (각 task 가 독립적으로 실행 가능) ✓

### 3. 타입/시그니처 일관성

- `features.json` metadata 필드: 4개 하위 (estimated_effort, external_dependencies, planning_gaps, cross_team_requests). Task 2, 11, 15, 28 모두 동일 키 사용 ✓
- `<!-- meta_start|end -->` 마커: Task 5, 8, 11, 15, 22, 26 모두 동일 스펠링 ✓
- `enrich_features.py` 서브커맨드: Task 2 정의 (load-context / merge-metadata), Task 20 SKILL.md 에서 동일 사용 ✓
- `external_dependencies` 항목 필드: `{team, item, blocking, note}` — Task 2, 11, 15 일관 ✓
- `cross_team_requests` 항목 필드: `{team, item, by}` — Task 2, 11, 15 일관 ✓

문제 없음.

---

## Execution Handoff

Plan 저장 경로: `docs/superpowers/plans/2026-04-21-feature-enrichment.md` (이 파일).

두 가지 실행 옵션:

**1. Subagent-Driven (권장)** — 각 Task 마다 fresh subagent dispatch, 두 단계 리뷰. 빠른 반복.

**2. Inline Execution** — 현재 세션에서 순차 실행. Commit 경계마다 checkpoint.

**어느 쪽으로 진행할까요?**

- Subagent-Driven 선택 시: REQUIRED SUB-SKILL `superpowers:subagent-driven-development` 호출
- Inline Execution 선택 시: REQUIRED SUB-SKILL `superpowers:executing-plans` 호출
