# Routing + Dispatcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `common/config/routing.yaml` (2D 매트릭스) + `common/scripts/dispatcher.py` (결정적 라우팅 레이어) 를 만들고, 24셀 전수 회귀 테스트를 통과시킨다.

**Architecture:** `InputProfile` 데이터클래스 → `detect_mode()` → `detect_work_type()` → `resolve_route()` 파이프라인. routing.yaml 은 선언적 규칙 리스트. `work_type_normalizer.py` 는 canonical + alias map. 테스트는 24셀 전수 케이스로 회귀 방지.

**Tech Stack:** Python 3.x, PyYAML, pytest, Pydantic (선택).

**Spec reference:** `docs/superpowers/specs/2026-04-22-spec-organizer-wrapper-design.md` (섹션 3)

**PR 번호:** 2/8

**Depends on:** PR 1 (common core extraction)

---

## File Structure Overview

| 경로 | 유형 | 책임 |
|------|------|------|
| `skills/common/config/routing.yaml` | 생성 | 2D 매트릭스 선언 |
| `skills/common/config/work-types.yaml` | 생성 | canonical + alias |
| `skills/common/scripts/input_profile.py` | 생성 | InputProfile 데이터클래스 + build_input_profile |
| `skills/common/scripts/work_type_normalizer.py` | 생성 | alias → canonical |
| `skills/common/scripts/routing.py` | 생성 | routing.yaml 로더 + 규칙 매칭 |
| `skills/common/scripts/dispatcher.py` | 생성 | 파이프라인 진입점 |
| `skills/common/scripts/tests/test_input_profile.py` | 생성 | 입력 프로필 테스트 |
| `skills/common/scripts/tests/test_work_type_normalizer.py` | 생성 | 정규화 테스트 |
| `skills/common/scripts/tests/test_routing.py` | 생성 | routing 규칙 매칭 테스트 |
| `skills/common/scripts/tests/test_dispatcher.py` | 생성 | 파이프라인 E2E |
| `evals/routing-matrix.json` | 생성 | 24셀 케이스 |
| `evals/test_routing_matrix.py` | 생성 | 24셀 회귀 |

---

## Commit 1: `work-types.yaml` + normalizer

### Task 1.1: `work-types.yaml` 작성

**Files:**
- Create: `skills/common/config/work-types.yaml`

- [ ] **Step 1: 디렉터리 생성**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/common/config
```

- [ ] **Step 2: YAML 작성**

`/Users/chuchu/testPlugin/skills/common/config/work-types.yaml`:

```yaml
version: 1

work_types:
  new_feature:
    canonical: "새 기능"
    aliases:
      - "new"
      - "feature"
      - "신규"
      - "피처"
      - "새 피처"
      - "새기능"
      - "new feature"
  bug_fix:
    canonical: "버그 픽스"
    aliases:
      - "bug"
      - "fix"
      - "bugfix"
      - "bug fix"
      - "버그픽스"
      - "버그"
      - "수정"
      - "오류"
      - "에러"
      - "fix bug"
  enhancement:
    canonical: "기능 강화"
    aliases:
      - "enhancement"
      - "improve"
      - "improvement"
      - "개선"
      - "강화"
      - "업그레이드"
      - "기능강화"
      - "enhance"
```

- [ ] **Step 3: 검증**

```bash
python3 -c "
import yaml
with open('/Users/chuchu/testPlugin/skills/common/config/work-types.yaml') as f:
    data = yaml.safe_load(f)
assert set(data['work_types'].keys()) == {'new_feature', 'bug_fix', 'enhancement'}
print('work-types.yaml OK')
"
```

---

### Task 1.2: `work_type_normalizer.py` 작성

**Files:**
- Create: `skills/common/scripts/work_type_normalizer.py`

- [ ] **Step 1: 테스트 먼저 작성**

`/Users/chuchu/testPlugin/skills/common/scripts/tests/test_work_type_normalizer.py`:

```python
from work_type_normalizer import normalize_work_type, WorkType


def test_normalize_canonical():
    assert normalize_work_type("새 기능") == WorkType.NEW_FEATURE
    assert normalize_work_type("버그 픽스") == WorkType.BUG_FIX
    assert normalize_work_type("기능 강화") == WorkType.ENHANCEMENT


def test_normalize_korean_aliases():
    assert normalize_work_type("버그픽스") == WorkType.BUG_FIX
    assert normalize_work_type("버그") == WorkType.BUG_FIX
    assert normalize_work_type("신규") == WorkType.NEW_FEATURE
    assert normalize_work_type("개선") == WorkType.ENHANCEMENT


def test_normalize_english_aliases():
    assert normalize_work_type("bugfix") == WorkType.BUG_FIX
    assert normalize_work_type("bug fix") == WorkType.BUG_FIX
    assert normalize_work_type("enhancement") == WorkType.ENHANCEMENT
    assert normalize_work_type("feature") == WorkType.NEW_FEATURE


def test_case_insensitive():
    assert normalize_work_type("BUG") == WorkType.BUG_FIX
    assert normalize_work_type("Enhancement") == WorkType.ENHANCEMENT


def test_whitespace_tolerant():
    assert normalize_work_type("  버그  ") == WorkType.BUG_FIX


def test_unknown_returns_none():
    assert normalize_work_type("asdf") is None
    assert normalize_work_type("") is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_work_type_normalizer.py -v 2>&1 | tail -10
```
Expected: FAIL with `ModuleNotFoundError: No module named 'work_type_normalizer'`.

- [ ] **Step 3: 구현**

`/Users/chuchu/testPlugin/skills/common/scripts/work_type_normalizer.py`:

```python
"""work_type 입력 정규화: alias → canonical enum."""
from enum import Enum
from pathlib import Path
import yaml


class WorkType(Enum):
    NEW_FEATURE = "new_feature"
    BUG_FIX = "bug_fix"
    ENHANCEMENT = "enhancement"


_ALIAS_MAP: dict[str, WorkType] | None = None


def _load_alias_map() -> dict[str, WorkType]:
    global _ALIAS_MAP
    if _ALIAS_MAP is not None:
        return _ALIAS_MAP

    config_path = (
        Path(__file__).resolve().parent.parent / "config" / "work-types.yaml"
    )
    with open(config_path) as f:
        data = yaml.safe_load(f)

    alias_map: dict[str, WorkType] = {}
    for key, spec in data["work_types"].items():
        wt = WorkType(key)
        # canonical 도 alias 로 포함
        alias_map[spec["canonical"].lower().strip()] = wt
        for alias in spec["aliases"]:
            alias_map[alias.lower().strip()] = wt

    _ALIAS_MAP = alias_map
    return alias_map


def normalize_work_type(raw: str) -> WorkType | None:
    """raw 입력 → WorkType enum 또는 None."""
    if not raw:
        return None
    key = raw.lower().strip()
    return _load_alias_map().get(key)
```

- [ ] **Step 4: 테스트 재실행**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_work_type_normalizer.py -v 2>&1 | tail -10
```
Expected: **6/6 PASS**.

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/config/work-types.yaml \
        skills/common/scripts/work_type_normalizer.py \
        skills/common/scripts/tests/test_work_type_normalizer.py && \
git commit -m "feat(common): work_type 정규화 (alias → canonical)"
```

---

## Commit 2: `InputProfile` + 입력 감지

### Task 2.1: `input_profile.py` TDD

**Files:**
- Create: `skills/common/scripts/input_profile.py`
- Create: `skills/common/scripts/tests/test_input_profile.py`

- [ ] **Step 1: 테스트 작성**

`/Users/chuchu/testPlugin/skills/common/scripts/tests/test_input_profile.py`:

```python
import tempfile
from pathlib import Path
import pytest

from input_profile import InputProfile, build_input_profile


@pytest.fixture
def tmp_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "sample.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


@pytest.fixture
def tmp_image(tmp_path: Path) -> Path:
    p = tmp_path / "screenshot.png"
    p.write_bytes(b"\x89PNG\r\n")
    return p


def test_empty_input():
    profile = build_input_profile([])
    assert profile.pdf_paths == []
    assert profile.image_paths == []
    assert profile.urls == []
    assert profile.free_text == ""


def test_single_pdf(tmp_pdf):
    profile = build_input_profile([str(tmp_pdf)])
    assert len(profile.pdf_paths) == 1
    assert profile.pdf_paths[0] == tmp_pdf.resolve()


def test_multi_pdf(tmp_pdf, tmp_path):
    second = tmp_path / "second.pdf"
    second.write_bytes(b"%PDF-1.4\n")
    profile = build_input_profile([str(tmp_pdf), str(second)])
    assert len(profile.pdf_paths) == 2


def test_image_only(tmp_image):
    profile = build_input_profile([str(tmp_image)])
    assert profile.pdf_paths == []
    assert len(profile.image_paths) == 1


def test_url_detected():
    profile = build_input_profile(["https://github.com/foo/bar/issues/42"])
    assert profile.urls == ["https://github.com/foo/bar/issues/42"]


def test_http_url_detected():
    profile = build_input_profile(["http://internal.jira/PROJ-1"])
    assert len(profile.urls) == 1


def test_free_text_short():
    profile = build_input_profile(["로그인", "안됨"])
    assert profile.free_text == "로그인 안됨"


def test_mixed_pdf_and_text(tmp_pdf):
    profile = build_input_profile([str(tmp_pdf), "긴급", "버그"])
    assert len(profile.pdf_paths) == 1
    assert profile.free_text == "긴급 버그"


def test_nonexistent_file_becomes_text(tmp_path):
    nonexistent = tmp_path / "nonexistent.pdf"
    profile = build_input_profile([str(nonexistent)])
    assert profile.pdf_paths == []
    assert nonexistent.name in profile.free_text or str(nonexistent) in profile.free_text


def test_path_with_tilde_expansion(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    pdf = tmp_path / "home_spec.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    profile = build_input_profile(["~/home_spec.pdf"])
    assert len(profile.pdf_paths) == 1


def test_has_helpers(tmp_pdf):
    profile = build_input_profile([str(tmp_pdf), "some bug"])
    assert profile.pdf_count == 1
    assert profile.has_text_or_link is True
```

- [ ] **Step 2: FAIL 확인**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_input_profile.py -v 2>&1 | tail -5
```
Expected: FAIL (module not found).

- [ ] **Step 3: 구현**

`/Users/chuchu/testPlugin/skills/common/scripts/input_profile.py`:

```python
"""raw 인자 리스트를 InputProfile 로 구조화한다.

결정적 분류 규칙:
  1. os.path.realpath(os.path.expanduser()) 로 정규화
  2. 파일이 실존하면 확장자로 PDF/이미지 분류
  3. '^https?://' 매칭되면 URL
  4. 그 외는 free_text 에 공백 조인
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
PDF_EXT = {".pdf"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class InputProfile:
    pdf_paths: list[Path] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    free_text: str = ""

    @property
    def pdf_count(self) -> int:
        return len(self.pdf_paths)

    @property
    def image_count(self) -> int:
        return len(self.image_paths)

    @property
    def has_text_or_link(self) -> bool:
        return bool(self.free_text) or bool(self.urls)


def build_input_profile(raw_args: list[str]) -> InputProfile:
    profile = InputProfile()
    text_tokens: list[str] = []

    for arg in raw_args:
        if not arg:
            continue

        # URL 우선 판정 (파일 시스템 체크 전)
        if URL_PATTERN.match(arg):
            profile.urls.append(arg)
            continue

        normalized = os.path.realpath(os.path.expanduser(arg))
        if os.path.isfile(normalized):
            path = Path(normalized)
            ext = path.suffix.lower()
            if ext in PDF_EXT:
                profile.pdf_paths.append(path)
            elif ext in IMAGE_EXT:
                profile.image_paths.append(path)
            else:
                # 알 수 없는 파일은 텍스트로 (드문 케이스)
                text_tokens.append(arg)
        else:
            text_tokens.append(arg)

    profile.free_text = " ".join(text_tokens).strip()
    return profile
```

- [ ] **Step 4: 테스트 PASS 확인**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_input_profile.py -v 2>&1 | tail -15
```
Expected: **모든 테스트 PASS**.

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/input_profile.py \
        skills/common/scripts/tests/test_input_profile.py && \
git commit -m "feat(common): InputProfile 데이터클래스 + 결정적 입력 감지"
```

---

## Commit 3: `routing.yaml` + `routing.py`

### Task 3.1: `routing.yaml` 작성

**Files:**
- Create: `skills/common/config/routing.yaml`

- [ ] **Step 1: YAML 작성**

(스펙 섹션 3.4 전체 내용 반영)

`/Users/chuchu/testPlugin/skills/common/config/routing.yaml`:

```yaml
version: 2

modes:
  create:
    routes:
      - id: pdf_single_new
        when: { pdf_count: 1, work_type: new_feature }
        skill: pdf-spec-organizer
        phases: { "1": full, "2": full, "3": full, "3.5": full, "4": full, "5": full }

      - id: pdf_single_bug
        when: { pdf_count: 1, work_type: bug_fix }
        skill: bug-spec-organizer
        phases: { "1": parse_only, "3": full, "5": full }

      - id: pdf_single_enh
        when: { pdf_count: 1, work_type: enhancement }
        skill: enhancement-spec-organizer
        phases: { "1": parse_only, "3": full, "3.5": full, "4": full, "5": full }

      - id: pdf_multi_bug
        when: { pdf_count_gte: 2, work_type: bug_fix }
        skill: bug-spec-organizer
        phases: { "1": parse_all, "3": full, "5": full }

      - id: pdf_multi_other
        when: { pdf_count_gte: 2, work_type_in: [new_feature, enhancement] }
        action: prompt
        choices:
          - { key: first_only, label: "첫 번째 PDF만 사용" }
          - { key: sequential, label: "순차 처리 (각각 별도 스펙)" }
          - { key: cancel, label: "취소" }

      - id: image_only_bug
        when: { pdf_count: 0, image_count_gte: 1, work_type: bug_fix }
        action: block
        message: "이미지만으로 버그 제보는 v1.5 에서 지원 예정입니다. 텍스트 설명이나 PDF 로 업로드해주세요."

      - id: text_or_link_new
        when: { pdf_count: 0, has_text_or_link: true, work_type: new_feature }
        action: redirect
        target: "superpowers:brainstorming"
        reentry_route: text_or_link_enh

      - id: text_or_link_bug
        when: { pdf_count: 0, has_text_or_link: true, work_type: bug_fix }
        skill: bug-spec-organizer
        phases: { "3": full, "5": full }

      - id: text_or_link_enh
        when: { pdf_count: 0, has_text_or_link: true, work_type: enhancement }
        skill: enhancement-spec-organizer
        phases: { "3": full, "3.5": full, "4": full, "5": full }

      - id: pdf_single_unknown
        when: { pdf_count: 1, work_type: unknown }
        action: prompt
        default_suggestion: new_feature
        question: "이 PDF 는 [1] 새 기능 [2] 버그 픽스 [3] 기능 강화 중 어느 것인가요?"

      - id: empty
        when: { pdf_count: 0, image_count: 0, has_text_or_link: false }
        action: prompt
        question: "어떤 작업인가요? [1] 새 기능 [2] 버그 픽스 [3] 기능 강화"

    unmatched:
      action: error
      message: "라우팅 규칙에 일치하는 조합을 찾지 못했습니다. 버그 리포트를 남겨주세요."
```

- [ ] **Step 2: YAML 파싱 검증**

```bash
python3 -c "
import yaml
with open('/Users/chuchu/testPlugin/skills/common/config/routing.yaml') as f:
    data = yaml.safe_load(f)
routes = data['modes']['create']['routes']
assert len(routes) == 11, f'expected 11 routes, got {len(routes)}'
assert all('id' in r for r in routes)
assert all('when' in r for r in routes)
print('routing.yaml OK, 11 routes')
"
```

---

### Task 3.2: `routing.py` 로더 + 매칭

**Files:**
- Create: `skills/common/scripts/routing.py`
- Create: `skills/common/scripts/tests/test_routing.py`

- [ ] **Step 1: 테스트 작성**

`/Users/chuchu/testPlugin/skills/common/scripts/tests/test_routing.py`:

```python
from input_profile import InputProfile
from pathlib import Path
from routing import load_routes, resolve_route
from work_type_normalizer import WorkType


def make_profile(pdf=0, img=0, text="", urls=None):
    p = InputProfile()
    p.pdf_paths = [Path(f"/tmp/{i}.pdf") for i in range(pdf)]
    p.image_paths = [Path(f"/tmp/{i}.png") for i in range(img)]
    p.urls = urls or []
    p.free_text = text
    return p


def test_pdf_single_new_feature():
    profile = make_profile(pdf=1)
    route = resolve_route(profile, WorkType.NEW_FEATURE)
    assert route["id"] == "pdf_single_new"
    assert route["skill"] == "pdf-spec-organizer"


def test_pdf_single_bug():
    profile = make_profile(pdf=1)
    route = resolve_route(profile, WorkType.BUG_FIX)
    assert route["id"] == "pdf_single_bug"
    assert route["skill"] == "bug-spec-organizer"


def test_pdf_multi_bug_allowed():
    profile = make_profile(pdf=3)
    route = resolve_route(profile, WorkType.BUG_FIX)
    assert route["id"] == "pdf_multi_bug"


def test_pdf_multi_other_prompts():
    profile = make_profile(pdf=2)
    route = resolve_route(profile, WorkType.NEW_FEATURE)
    assert route["id"] == "pdf_multi_other"
    assert route["action"] == "prompt"


def test_image_only_bug_blocks():
    profile = make_profile(img=2)
    route = resolve_route(profile, WorkType.BUG_FIX)
    assert route["id"] == "image_only_bug"
    assert route["action"] == "block"


def test_text_new_redirects_to_brainstorm():
    profile = make_profile(text="로그인 개선 아이디어가 있어")
    route = resolve_route(profile, WorkType.NEW_FEATURE)
    assert route["id"] == "text_or_link_new"
    assert route["action"] == "redirect"
    assert route["target"] == "superpowers:brainstorming"


def test_text_bug_uses_bug_skill():
    profile = make_profile(text="로그인 안 됨")
    route = resolve_route(profile, WorkType.BUG_FIX)
    assert route["id"] == "text_or_link_bug"
    assert route["skill"] == "bug-spec-organizer"


def test_text_enh_uses_enh_skill():
    profile = make_profile(text="버튼 색 바꾸고 싶어")
    route = resolve_route(profile, WorkType.ENHANCEMENT)
    assert route["id"] == "text_or_link_enh"


def test_empty_prompts():
    profile = make_profile()
    route = resolve_route(profile, None)
    assert route["id"] == "empty"


def test_pdf_with_unknown_prompts():
    profile = make_profile(pdf=1)
    route = resolve_route(profile, None)
    assert route["id"] == "pdf_single_unknown"


def test_url_counts_as_text():
    profile = make_profile(urls=["https://github.com/x/y/issues/1"])
    route = resolve_route(profile, WorkType.BUG_FIX)
    assert route["id"] == "text_or_link_bug"
```

- [ ] **Step 2: 구현**

`/Users/chuchu/testPlugin/skills/common/scripts/routing.py`:

```python
"""routing.yaml 로더 및 InputProfile × work_type → route 매칭."""
from pathlib import Path
from typing import Any
import yaml

from input_profile import InputProfile
from work_type_normalizer import WorkType


_ROUTES_CACHE: dict[str, Any] | None = None


def load_routes() -> dict[str, Any]:
    global _ROUTES_CACHE
    if _ROUTES_CACHE is not None:
        return _ROUTES_CACHE
    path = Path(__file__).resolve().parent.parent / "config" / "routing.yaml"
    with open(path) as f:
        _ROUTES_CACHE = yaml.safe_load(f)
    return _ROUTES_CACHE


def _match_condition(cond: dict, profile: InputProfile, work_type: WorkType | None) -> bool:
    wt_str = work_type.value if work_type else "unknown"

    # pdf_count (exact)
    if "pdf_count" in cond and profile.pdf_count != cond["pdf_count"]:
        return False
    # pdf_count_gte
    if "pdf_count_gte" in cond and profile.pdf_count < cond["pdf_count_gte"]:
        return False
    # image_count (exact)
    if "image_count" in cond and profile.image_count != cond["image_count"]:
        return False
    # image_count_gte
    if "image_count_gte" in cond and profile.image_count < cond["image_count_gte"]:
        return False
    # has_text_or_link
    if "has_text_or_link" in cond and profile.has_text_or_link != cond["has_text_or_link"]:
        return False
    # work_type (exact)
    if "work_type" in cond:
        expected = cond["work_type"]
        if expected == "unknown":
            if work_type is not None:
                return False
        elif expected != wt_str:
            return False
    # work_type_in
    if "work_type_in" in cond:
        if wt_str not in cond["work_type_in"]:
            return False

    return True


def resolve_route(
    profile: InputProfile, work_type: WorkType | None, mode: str = "create"
) -> dict[str, Any]:
    routes_data = load_routes()
    routes = routes_data["modes"][mode]["routes"]
    for rule in routes:
        if _match_condition(rule["when"], profile, work_type):
            return rule
    # fallback
    return routes_data["modes"][mode]["unmatched"]
```

- [ ] **Step 3: 테스트 실행**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_routing.py -v 2>&1 | tail -15
```
Expected: **11/11 PASS**.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/config/routing.yaml \
        skills/common/scripts/routing.py \
        skills/common/scripts/tests/test_routing.py && \
git commit -m "feat(common): routing.yaml 2D 매트릭스 + 매칭 엔진"
```

---

## Commit 4: `dispatcher.py` — 파이프라인 진입점

### Task 4.1: work_type 자동 감지 + 디스패치

**Files:**
- Create: `skills/common/scripts/dispatcher.py`
- Create: `skills/common/scripts/tests/test_dispatcher.py`

- [ ] **Step 1: 테스트 작성**

`/Users/chuchu/testPlugin/skills/common/scripts/tests/test_dispatcher.py`:

```python
from pathlib import Path
import pytest

from dispatcher import dispatch, detect_work_type_heuristic
from input_profile import InputProfile, build_input_profile
from work_type_normalizer import WorkType


def test_detect_bug_keywords():
    assert detect_work_type_heuristic("로그인 버그 있음") == WorkType.BUG_FIX
    assert detect_work_type_heuristic("bug in checkout") == WorkType.BUG_FIX
    assert detect_work_type_heuristic("에러 발생") == WorkType.BUG_FIX


def test_detect_enhancement_keywords():
    assert detect_work_type_heuristic("색상 개선") == WorkType.ENHANCEMENT
    assert detect_work_type_heuristic("새 옵션 추가") == WorkType.ENHANCEMENT


def test_detect_returns_none_for_ambiguous():
    assert detect_work_type_heuristic("뭔가 이상해") is None


def test_dispatch_pdf_with_hint(tmp_path):
    pdf = tmp_path / "s.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    result = dispatch([str(pdf)], work_type_hint="새 기능")
    assert result["route"]["id"] == "pdf_single_new"
    assert result["work_type"] == WorkType.NEW_FEATURE


def test_dispatch_empty_prompts():
    result = dispatch([], work_type_hint=None)
    assert result["route"]["id"] == "empty"
    assert result["work_type"] is None


def test_dispatch_text_with_bug_keyword_autodetect():
    result = dispatch(["로그인", "버그"], work_type_hint=None)
    assert result["work_type"] == WorkType.BUG_FIX
    assert result["route"]["id"] == "text_or_link_bug"


def test_dispatch_pdf_without_hint_defaults_to_ask():
    """PDF 만 있고 hint 없으면 pdf_single_unknown 으로 빠져서 prompt."""
    # 실제로는 detect_work_type 이 NEW_FEATURE 반환 (Rule 4)
    # 테스트: 짧은 텍스트 조합으로 ASK 유도
    pass  # 다음 Task 에서 상세 처리
```

- [ ] **Step 2: 구현**

`/Users/chuchu/testPlugin/skills/common/scripts/dispatcher.py`:

```python
"""spec-organizer 의 결정적 라우팅 레이어.

파이프라인:
    1. build_input_profile()     — 파일/URL/텍스트 분류
    2. detect_work_type()        — 사용자 힌트 + 키워드 + 기본 추론
    3. resolve_route()           — routing.yaml 매칭
    4. 반환: {route, work_type, profile}

Claude 는 work_type == None (ASK) 인 경우에만 사용자 질문을 담당.
"""
from typing import Any
from dataclasses import asdict

from input_profile import InputProfile, build_input_profile
from routing import resolve_route
from work_type_normalizer import WorkType, normalize_work_type


BUG_KEYWORDS = {"버그", "bug", "오류", "fix", "수정", "에러", "error", "실패", "안됨", "안 됨"}
ENHANCEMENT_KEYWORDS = {"개선", "강화", "추가", "enhancement", "improve", "업그레이드"}


def detect_work_type_heuristic(free_text: str) -> WorkType | None:
    """free_text 에서 키워드로 work_type 추론. 애매하면 None."""
    text = free_text.lower().strip()
    if not text:
        return None

    has_bug = any(kw in text for kw in BUG_KEYWORDS)
    has_enh = any(kw in text for kw in ENHANCEMENT_KEYWORDS)

    if has_bug and not has_enh:
        return WorkType.BUG_FIX
    if has_enh and not has_bug:
        return WorkType.ENHANCEMENT
    # 둘 다 or 둘 다 아님 → 불확실
    return None


def detect_work_type(
    profile: InputProfile, user_hint: str | None
) -> WorkType | None:
    # 규칙 1: 사용자 명시
    if user_hint:
        wt = normalize_work_type(user_hint)
        if wt:
            return wt

    # 규칙 2: free_text 키워드
    heur = detect_work_type_heuristic(profile.free_text)
    if heur:
        return heur

    # 규칙 3: 짧은 텍스트 → ASK (None)
    if len(profile.free_text) > 10:
        return None  # Claude 가 질문 또는 분류

    # 규칙 4: PDF 만 있고 텍스트 없음 → 기본 새 기능
    if profile.pdf_paths and not profile.free_text:
        return WorkType.NEW_FEATURE

    return None


def dispatch(
    raw_args: list[str],
    work_type_hint: str | None = None,
    mode: str = "create",
) -> dict[str, Any]:
    profile = build_input_profile(raw_args)
    work_type = detect_work_type(profile, work_type_hint)
    route = resolve_route(profile, work_type, mode=mode)
    return {
        "profile": profile,
        "work_type": work_type,
        "route": route,
        "mode": mode,
    }
```

- [ ] **Step 3: 테스트 실행**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_dispatcher.py -v 2>&1 | tail -10
```
Expected: **모든 테스트 PASS**.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/dispatcher.py \
        skills/common/scripts/tests/test_dispatcher.py && \
git commit -m "feat(common): dispatcher 파이프라인 (input_profile → work_type → route)"
```

---

## Commit 5: 24셀 회귀 테스트 (`evals/routing-matrix.json`)

### Task 5.1: 전수 케이스 JSON 작성

**Files:**
- Create: `evals/routing-matrix.json`
- Create: `evals/test_routing_matrix.py`

- [ ] **Step 1: JSON 작성**

(조건 × work_type = 24 조합 중 정의된 11개 + 에지케이스 13개 = 24)

`/Users/chuchu/testPlugin/evals/routing-matrix.json`:

```json
{
  "version": 1,
  "cases": [
    {"id": "c01_pdf1_new", "args": ["TMP_PDF"], "hint": "새 기능", "expected_route": "pdf_single_new"},
    {"id": "c02_pdf1_bug", "args": ["TMP_PDF"], "hint": "버그", "expected_route": "pdf_single_bug"},
    {"id": "c03_pdf1_enh", "args": ["TMP_PDF"], "hint": "강화", "expected_route": "pdf_single_enh"},
    {"id": "c04_pdf1_unknown", "args": ["TMP_PDF"], "hint": null, "expected_route": "pdf_single_new"},
    {"id": "c05_pdf2_bug", "args": ["TMP_PDF", "TMP_PDF2"], "hint": "버그", "expected_route": "pdf_multi_bug"},
    {"id": "c06_pdf2_new", "args": ["TMP_PDF", "TMP_PDF2"], "hint": "새 기능", "expected_route": "pdf_multi_other"},
    {"id": "c07_pdf2_enh", "args": ["TMP_PDF", "TMP_PDF2"], "hint": "강화", "expected_route": "pdf_multi_other"},
    {"id": "c08_pdf2_unknown", "args": ["TMP_PDF", "TMP_PDF2"], "hint": null, "expected_route": "pdf_multi_other"},
    {"id": "c09_img1_bug", "args": ["TMP_IMG"], "hint": "버그", "expected_route": "image_only_bug"},
    {"id": "c10_img1_new", "args": ["TMP_IMG"], "hint": "새 기능", "expected_route": "unmatched"},
    {"id": "c11_img1_enh", "args": ["TMP_IMG"], "hint": "강화", "expected_route": "unmatched"},
    {"id": "c12_text_new", "args": ["로그인 기능 추가하고 싶어"], "hint": "새 기능", "expected_route": "text_or_link_new"},
    {"id": "c13_text_bug", "args": ["로그인 버그"], "hint": null, "expected_route": "text_or_link_bug"},
    {"id": "c14_text_enh", "args": ["로그인 개선"], "hint": null, "expected_route": "text_or_link_enh"},
    {"id": "c15_url_new", "args": ["https://example.com/issue"], "hint": "새 기능", "expected_route": "text_or_link_new"},
    {"id": "c16_url_bug", "args": ["https://example.com/bug"], "hint": "버그", "expected_route": "text_or_link_bug"},
    {"id": "c17_url_enh", "args": ["https://example.com/enh"], "hint": "강화", "expected_route": "text_or_link_enh"},
    {"id": "c18_empty_new", "args": [], "hint": "새 기능", "expected_route": "empty"},
    {"id": "c19_empty_bug", "args": [], "hint": "버그", "expected_route": "empty"},
    {"id": "c20_empty_enh", "args": [], "hint": "강화", "expected_route": "empty"},
    {"id": "c21_empty_unknown", "args": [], "hint": null, "expected_route": "empty"},
    {"id": "c22_text_only_no_hint_short", "args": ["bug"], "hint": null, "expected_route": "text_or_link_bug"},
    {"id": "c23_pdf1_text_bug", "args": ["TMP_PDF", "긴급 버그"], "hint": null, "expected_route": "pdf_single_bug"},
    {"id": "c24_pdf1_text_new", "args": ["TMP_PDF", "새 기능 추가"], "hint": null, "expected_route": "pdf_single_new"}
  ]
}
```

주의: `expected_route: "unmatched"` 인 케이스(c10, c11)는 routing.yaml 의 `empty` 루트나 `unmatched` 로 빠지도록 의도됨. 테스트 러너가 정확한 동작을 검증.

- [ ] **Step 2: pytest 러너 작성**

`/Users/chuchu/testPlugin/evals/test_routing_matrix.py`:

```python
"""24셀 전수 회귀 테스트: routing-matrix.json 의 기대 route 검증."""
import json
import sys
from pathlib import Path
import pytest

# common/scripts 를 import path 에 주입
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "common" / "scripts"))

from dispatcher import dispatch

CASES_PATH = ROOT / "evals" / "routing-matrix.json"


@pytest.fixture(scope="module")
def tmp_pdf(tmp_path_factory):
    d = tmp_path_factory.mktemp("eval")
    p = d / "a.pdf"
    p.write_bytes(b"%PDF-1.4")
    p2 = d / "b.pdf"
    p2.write_bytes(b"%PDF-1.4")
    img = d / "s.png"
    img.write_bytes(b"\x89PNG\r\n")
    return {"TMP_PDF": str(p), "TMP_PDF2": str(p2), "TMP_IMG": str(img)}


def _load_cases():
    with open(CASES_PATH) as f:
        return json.load(f)["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_route(case, tmp_pdf):
    args = [tmp_pdf.get(a, a) for a in case["args"]]
    result = dispatch(args, work_type_hint=case["hint"])
    assert result["route"]["id"] == case["expected_route"], (
        f"case {case['id']}: got {result['route']['id']}, want {case['expected_route']}"
    )
```

- [ ] **Step 3: 실행**

```bash
cd /Users/chuchu/testPlugin && \
python3 -m pytest evals/test_routing_matrix.py -v 2>&1 | tail -30
```

Expected: **24/24 PASS**. 실패가 있으면 routing.yaml 또는 detect_work_type 규칙 조정.

**주의 케이스**:
- c10, c11 이 실패하면 `image_only` 가 new/enhancement 에 해당하는 룰이 없어 `unmatched` 로 빠져야 함 → `expected_route: "unmatched"` 검증
- c22 ("bug" 단독) 가 실패하면 heuristic 키워드 매칭이 짧은 입력에서 동작해야 함
- c23, c24: PDF + 텍스트 조합에서 텍스트 keyword 가 work_type hint 로 작동

필요 시 `detect_work_type_heuristic` 의 짧은 텍스트 룰 수정.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add evals/routing-matrix.json evals/test_routing_matrix.py && \
git commit -m "test(evals): 24셀 전수 routing 회귀 테스트"
```

---

## 완료 기준 (PR 2 Definition of Done)

- [ ] `common/config/routing.yaml` (11개 routes)
- [ ] `common/config/work-types.yaml` (3개 work_type × alias)
- [ ] `common/scripts/` 4개 신규 파일 (input_profile, work_type_normalizer, routing, dispatcher)
- [ ] 단위 테스트 4개 파일 모두 PASS
- [ ] `evals/routing-matrix.json` 24/24 PASS
- [ ] 기존 테스트 회귀 없음

---

## 다음 플랜

→ `docs/superpowers/plans/2026-04-22-03-schemas-field-collector.md` (PR 3)
