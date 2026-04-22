# Checklist Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `config/pdf-spec-organizer/checklist.yaml` 을 `skills/common/config/checklist.yaml` 로 이동하고 `applies_to_work_type` 필드를 추가해 work_type 별 필터링을 지원한다. Phase 3 실행 로직은 이 필드를 읽어 자동 필터.

**Architecture:** 파일 이동 + YAML 필드 확장 + Python 로더 + 각 스킬의 Phase 3 참조 경로 업데이트.

**Tech Stack:** YAML, Python, Bash (git mv).

**Spec reference:** 설계 문서 섹션 4

**PR 번호:** 7/8

**Depends on:** PR 1

---

## File Structure Overview

| 경로 | 유형 | 변경 |
|------|------|------|
| `config/pdf-spec-organizer/checklist.yaml` | 이동 | → `skills/common/config/checklist.yaml` |
| `skills/common/scripts/checklist_loader.py` | 생성 | work_type 필터 포함 로더 |
| `skills/common/scripts/tests/test_checklist_loader.py` | 생성 | |
| `skills/pdf-spec-organizer/SKILL.md` | 수정 | Phase 3 경로 참조 |
| `skills/bug-spec-organizer/SKILL.md` | 수정 | Phase 3 경로 참조 |
| `skills/enhancement-spec-organizer/SKILL.md` | 수정 | Phase 3 경로 참조 |

---

## Commit 1: 파일 이동 + 필드 확장

### Task 1.1: `git mv` 로 이동

- [ ] **Step 1: 현재 파일 확인**

```bash
cat /Users/chuchu/testPlugin/config/pdf-spec-organizer/checklist.yaml
```

기존 구조 예:
```yaml
categories:
  - id: error_handling
    name: "에러 처리"
    prompts: [...]
  - id: empty_state
  ...
```

- [ ] **Step 2: 이동**

```bash
cd /Users/chuchu/testPlugin && \
git mv config/pdf-spec-organizer/checklist.yaml skills/common/config/checklist.yaml
```

- [ ] **Step 3: 빈 config 디렉터리 확인**

```bash
ls /Users/chuchu/testPlugin/config/pdf-spec-organizer/ 2>/dev/null
```

만약 `checklist.yaml` 외에도 파일이 있다면 (`notion-schema.yaml`, `default-checklist.json` 등) 그들은 유지.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git commit -m "refactor(checklist): config/ → skills/common/config/ 이동"
```

---

### Task 1.2: `applies_to_work_type` 필드 추가

**Files:**
- Modify: `skills/common/config/checklist.yaml`

- [ ] **Step 1: 기존 6개 카테고리에 필드 추가 + 버그 전용 2개 신설**

Edit 도구로 각 카테고리에 `applies_to_work_type` 추가:

```yaml
categories:
  - id: error_handling
    name: "에러 처리"
    applies_to_work_type: [new_feature, bug_fix, enhancement]
    prompts:
      - "네트워크 에러 발생 시 사용자에게 어떻게 안내하나?"
      - "API 5xx 응답은 어떻게 처리?"

  - id: empty_state
    name: "빈 상태"
    applies_to_work_type: [new_feature, enhancement]
    prompts:
      - "데이터가 0개일 때 화면은 어떻게 보이나?"

  - id: offline
    name: "오프라인 동작"
    applies_to_work_type: [new_feature, bug_fix, enhancement]
    prompts:
      - "네트워크 끊김 시 화면은 어떻게 동작하나?"
      - "복구 시 자동 재시도 있나?"

  - id: permission
    name: "권한 거부"
    applies_to_work_type: [new_feature, enhancement]
    prompts:
      - "사용자가 권한을 거부한 경우의 UX 는?"

  - id: loading
    name: "로딩 상태"
    applies_to_work_type: [new_feature, enhancement]
    prompts:
      - "로딩 중 인디케이터 표시?"
      - "로딩 시간이 3초 이상이면?"

  - id: a11y
    name: "접근성"
    applies_to_work_type: [new_feature, bug_fix, enhancement]
    prompts:
      - "VoiceOver/TalkBack 에서 어떻게 읽히나?"
      - "색상 대비가 WCAG 기준 충족?"

  # 신규: 버그 전용
  - id: regression_scope
    name: "회귀 영향 범위"
    applies_to_work_type: [bug_fix]
    description: "수정이 다른 피처에 영향 주지 않는지"
    prompts:
      - "수정 후 어느 화면/플로우에 부작용 가능성?"
      - "회귀 테스트 대상 범위는?"

  - id: reproduction_conditions
    name: "재현 조건"
    applies_to_work_type: [bug_fix]
    description: "재현에 필요한 환경/조건 명시"
    prompts:
      - "OS 버전 특정 조건 필요?"
      - "데이터/세션 상태 조건 필요?"
```

- [ ] **Step 2: YAML 파싱 검증**

```bash
python3 -c "
import yaml
with open('/Users/chuchu/testPlugin/skills/common/config/checklist.yaml') as f:
    data = yaml.safe_load(f)
categories = data['categories']
assert len(categories) == 8, f'expected 8, got {len(categories)}'
assert all('applies_to_work_type' in c for c in categories)
bug_only = [c for c in categories if c['applies_to_work_type'] == ['bug_fix']]
assert len(bug_only) == 2
print('checklist.yaml OK: 8 categories (6 shared + 2 bug-only)')
"
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/config/checklist.yaml && \
git commit -m "feat(checklist): applies_to_work_type 필드 + 버그 전용 2개 카테고리"
```

---

## Commit 2: `checklist_loader.py` — 필터 포함 로더

### Task 2.1: TDD

**Files:**
- Create: `skills/common/scripts/checklist_loader.py`
- Create: `skills/common/scripts/tests/test_checklist_loader.py`

- [ ] **Step 1: 테스트**

```python
from checklist_loader import load_categories, filter_by_work_type


def test_load_all():
    cats = load_categories()
    assert len(cats) == 8


def test_filter_bug_fix():
    cats = filter_by_work_type("bug_fix")
    ids = {c["id"] for c in cats}
    # bug_fix 해당: error_handling, offline, a11y (공통) + regression_scope + reproduction_conditions
    assert ids == {"error_handling", "offline", "a11y", "regression_scope", "reproduction_conditions"}


def test_filter_new_feature():
    cats = filter_by_work_type("new_feature")
    ids = {c["id"] for c in cats}
    assert ids == {"error_handling", "empty_state", "offline", "permission", "loading", "a11y"}


def test_filter_enhancement():
    cats = filter_by_work_type("enhancement")
    ids = {c["id"] for c in cats}
    # enhancement 는 공통 6개 모두 (bug 전용 제외)
    assert ids == {"error_handling", "empty_state", "offline", "permission", "loading", "a11y"}


def test_filter_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        filter_by_work_type("invalid")
```

- [ ] **Step 2: 구현**

```python
"""checklist.yaml 로더 with work_type 필터링."""
from pathlib import Path
from typing import Any
import yaml

CHECKLIST_PATH = Path(__file__).resolve().parent.parent / "config" / "checklist.yaml"
VALID_WORK_TYPES = {"new_feature", "bug_fix", "enhancement"}

_CACHE: dict[str, Any] | None = None


def load_categories() -> list[dict]:
    global _CACHE
    if _CACHE is None:
        with open(CHECKLIST_PATH) as f:
            _CACHE = yaml.safe_load(f)
    return list(_CACHE["categories"])


def filter_by_work_type(work_type: str) -> list[dict]:
    if work_type not in VALID_WORK_TYPES:
        raise ValueError(f"unknown work_type: {work_type}")
    return [
        c for c in load_categories()
        if work_type in c.get("applies_to_work_type", [])
    ]
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_checklist_loader.py -v
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/checklist_loader.py \
        skills/common/scripts/tests/test_checklist_loader.py && \
git commit -m "feat(common): checklist_loader — work_type 필터"
```

---

## Commit 3: 각 스킬 SKILL.md 의 Phase 3 경로 업데이트

### Task 3.1: pdf-spec-organizer

- [ ] **Step 1: 경로 참조 찾기**

```bash
grep -n "config/pdf-spec-organizer/checklist.yaml\|config/.*checklist" \
  /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

- [ ] **Step 2: Edit 로 치환**

`config/pdf-spec-organizer/checklist.yaml` → `skills/common/config/checklist.yaml`

또한 Phase 3 로직에 필터 호출 추가 (Bash 예시):
```bash
python -c "
import sys; sys.path.insert(0, 'skills/common/scripts')
from checklist_loader import filter_by_work_type
import json
print(json.dumps(filter_by_work_type('new_feature'), ensure_ascii=False))
"
```

### Task 3.2: bug-spec-organizer

- [ ] **Step 1: Phase 3 섹션에 filter_by_work_type('bug_fix') 호출 명시**

기존 SKILL.md 의 Phase 3 블록을 Edit 로 갱신.

### Task 3.3: enhancement-spec-organizer

- [ ] **Step 1: filter_by_work_type('enhancement') 명시**

### Task 3.4: 커밋

```bash
cd /Users/chuchu/testPlugin && \
git add skills/pdf-spec-organizer/SKILL.md \
        skills/bug-spec-organizer/SKILL.md \
        skills/enhancement-spec-organizer/SKILL.md && \
git commit -m "docs(skills): Phase 3 에 checklist_loader 필터 연동"
```

---

## Commit 4: 레거시 경로 cleanup

### Task 4.1: 빈 config 디렉터리 정리

- [ ] **Step 1: 빈 디렉터리 제거 (남은 파일 없을 때만)**

```bash
cd /Users/chuchu/testPlugin && \
if [ -d config/pdf-spec-organizer ] && [ -z "$(ls -A config/pdf-spec-organizer 2>/dev/null)" ]; then
  rmdir config/pdf-spec-organizer
  rmdir config 2>/dev/null || true
  git add -A
  git commit -m "refactor: 빈 config/ 디렉터리 제거"
else
  echo "config/ 에 다른 파일 존재, cleanup 스킵"
  ls config/ 2>/dev/null
fi
```

### Task 4.2: README / CHANGELOG

- [ ] **Step 1: CHANGELOG 엔트리**

Edit 로 `[Unreleased]` 아래 추가:

```markdown
- `config/pdf-spec-organizer/checklist.yaml` → `skills/common/config/checklist.yaml` 이동
- `applies_to_work_type` 필드로 work_type 별 체크리스트 필터링 지원
- 버그 전용 카테고리 2종(`regression_scope`, `reproduction_conditions`) 추가
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add CHANGELOG.md && \
git commit -m "docs(changelog): checklist 마이그레이션 기록"
```

---

## 완료 기준 (PR 7)

- [ ] `skills/common/config/checklist.yaml` 존재 (8 카테고리)
- [ ] `checklist_loader.py` 테스트 PASS
- [ ] 3개 스킬 SKILL.md 가 신규 경로 참조
- [ ] 레거시 `config/pdf-spec-organizer/` cleanup
- [ ] 기존 테스트 회귀 없음

---

## 다음 플랜

→ `docs/superpowers/plans/2026-04-22-08-error-handling.md` (PR 8)
