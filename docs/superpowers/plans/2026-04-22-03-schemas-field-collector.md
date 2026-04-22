# Schemas + Field Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `common/config/work-type-schemas/*.yaml` (3종) + `field_collector.py` + Notion 피처 DB 키워드 검색 연동을 완성한다. 스키마 주도 수집으로 "Claude 가 뭐가 부족한지 판단" 하는 비결정성을 제거한다.

**Architecture:** 각 work_type 이 스키마 YAML 을 가지며 `source` (auto_or_ask / ask / ask_with_notion_lookup / phase_3_5_auto / phase_1_2_auto) 로 수집 방식 선언. `field_collector.py` 는 이 스키마를 읽어 비어있는 필드만 결정적으로 질문/추출. Notion 검색은 `notion_search_client.py` 래퍼.

**Tech Stack:** Python 3.x, PyYAML, Pydantic (validator), pytest.

**Spec reference:** `docs/superpowers/specs/2026-04-22-spec-organizer-wrapper-design.md` (섹션 5)

**PR 번호:** 3/8

**Depends on:** PR 1, 2

---

## File Structure Overview

| 경로 | 유형 | 책임 |
|------|------|------|
| `skills/common/config/work-type-schemas/new_feature.yaml` | 생성 | PDF 파싱 결과 검증용 |
| `skills/common/config/work-type-schemas/bug_fix.yaml` | 생성 | 버그 필수/선택 필드 |
| `skills/common/config/work-type-schemas/enhancement.yaml` | 생성 | 강화 필수/선택 필드 |
| `skills/common/scripts/schema_loader.py` | 생성 | 스키마 YAML 로더 |
| `skills/common/scripts/validators.py` | 생성 | non_empty, enum, duration 등 |
| `skills/common/scripts/field_collector.py` | 생성 | 파이프라인 수집 |
| `skills/common/scripts/notion_search_client.py` | 생성 | 키워드 검색 래퍼 |
| `skills/common/scripts/tests/test_schema_loader.py` | 생성 | |
| `skills/common/scripts/tests/test_validators.py` | 생성 | |
| `skills/common/scripts/tests/test_field_collector.py` | 생성 | |
| `skills/common/scripts/tests/test_notion_search_client.py` | 생성 | mock 기반 |

---

## Commit 1: 스키마 YAML 3종

### Task 1.1: `bug_fix.yaml`

**Files:**
- Create: `skills/common/config/work-type-schemas/bug_fix.yaml`

- [ ] **Step 1: 디렉터리 생성**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/common/config/work-type-schemas
```

- [ ] **Step 2: YAML 작성**

```yaml
version: 1
work_type: bug_fix
notion_page_template: bug_template

required:
  - id: title
    label: "제목"
    source: auto_or_ask
    validator: non_empty
  - id: symptom
    label: "증상 (재현 스텝)"
    source: auto_or_ask
    validator: non_empty
    hint: "어떤 동작이 잘못되는지 + 재현 순서"
  - id: root_cause
    label: "원인"
    source: ask
    validator: non_empty
  - id: fix_plan
    label: "수정안"
    source: ask
    validator: non_empty
  - id: affected_platforms
    label: "영향 플랫폼"
    source: auto_or_ask
    validator: enum_multi
    choices: [iOS, Android, 공통]
  - id: related_feature_id
    label: "관련 피처"
    source: ask_with_notion_lookup
    validator: exists_in_feature_db

optional:
  - id: estimated_duration
    label: "예상 수정 시간"
    source: phase_3_5_auto
    validator: duration_string
  - id: priority
    label: "우선순위"
    source: ask
    validator: enum
    choices: [Critical, High, Medium, Low]
    default: Medium
  - id: reproduction_env
    label: "재현 환경"
    source: auto_or_ask
    hint: "OS 버전, 기기, 네트워크 상태 등"
```

### Task 1.2: `enhancement.yaml`

**Files:**
- Create: `skills/common/config/work-type-schemas/enhancement.yaml`

- [ ] **Step 1: YAML 작성**

```yaml
version: 1
work_type: enhancement
notion_page_template: enhancement_template

required:
  - id: title
    label: "강화 내용 제목"
    source: auto_or_ask
    validator: non_empty
  - id: related_feature_id
    label: "대상 기존 피처"
    source: ask_with_notion_lookup
    validator: exists_in_feature_db
    hint: "어느 피처를 강화하는 건지"
  - id: target_platforms
    label: "대상 플랫폼"
    source: auto_or_ask
    validator: enum_multi
    choices: [iOS, Android, 공통]
  - id: change_description
    label: "변경 내용"
    source: auto_or_ask
    validator: non_empty
    hint: "어떻게 바뀌는지 구체적으로"

optional:
  - id: reason
    label: "변경 이유"
    source: auto_or_ask
    hint: "왜 이 변경이 필요한지"
  - id: estimated_duration
    label: "예상 개발 시간"
    source: phase_3_5_auto
  - id: dependencies
    label: "타 팀 의존성"
    source: phase_3_5_auto
  - id: missing_items
    label: "기획 누락 제안"
    source: phase_3_5_auto
```

### Task 1.3: `new_feature.yaml`

**Files:**
- Create: `skills/common/config/work-type-schemas/new_feature.yaml`

- [ ] **Step 1: YAML 작성**

```yaml
version: 1
work_type: new_feature
notion_page_template: feature_template
validator_only: true

required:
  - id: title
    source: phase_1_2_auto
  - id: feature_boundaries
    source: phase_1_2_auto
  - id: target_platforms
    source: phase_1_2_auto
```

### Task 1.4: 검증 + 커밋

- [ ] **Step 1: 3개 YAML 파싱 확인**

```bash
python3 -c "
import yaml
from pathlib import Path
base = Path('/Users/chuchu/testPlugin/skills/common/config/work-type-schemas')
for f in ['new_feature.yaml', 'bug_fix.yaml', 'enhancement.yaml']:
    data = yaml.safe_load((base/f).read_text())
    assert 'work_type' in data
    assert 'required' in data
    print(f'{f}: {len(data[\"required\"])} required, {len(data.get(\"optional\", []))} optional')
"
```

Expected:
```
new_feature.yaml: 3 required, 0 optional
bug_fix.yaml: 6 required, 3 optional
enhancement.yaml: 4 required, 4 optional
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/config/work-type-schemas/ && \
git commit -m "feat(common): work-type-schemas 3종 (bug/enhancement/new_feature)"
```

---

## Commit 2: `validators.py` + `schema_loader.py`

### Task 2.1: validators TDD

**Files:**
- Create: `skills/common/scripts/validators.py`
- Create: `skills/common/scripts/tests/test_validators.py`

- [ ] **Step 1: 테스트 작성**

`/Users/chuchu/testPlugin/skills/common/scripts/tests/test_validators.py`:

```python
from validators import (
    non_empty, enum, enum_multi, duration_string, validate_field
)


def test_non_empty():
    assert non_empty("hello") is True
    assert non_empty("") is False
    assert non_empty("  ") is False
    assert non_empty(None) is False


def test_enum_single():
    assert enum("High", choices=["Critical", "High", "Medium", "Low"]) is True
    assert enum("Other", choices=["Critical", "High"]) is False


def test_enum_multi():
    assert enum_multi(["iOS", "Android"], choices=["iOS", "Android", "공통"]) is True
    assert enum_multi(["iOS", "Web"], choices=["iOS", "Android", "공통"]) is False
    assert enum_multi([], choices=["iOS"]) is False  # 빈 선택 불허


def test_duration_string():
    assert duration_string("2h") is True
    assert duration_string("1d") is True
    assert duration_string("30m") is True
    assert duration_string("3w") is True
    assert duration_string("2 hours") is False  # 정형식만


def test_validate_field_dispatches():
    assert validate_field("non_empty", "hello") is True
    assert validate_field("enum", "High", choices=["High", "Low"]) is True
    assert validate_field("unknown_validator", "x") is True  # 모르는 건 pass
```

- [ ] **Step 2: 구현**

```python
"""값 검증 함수들."""
import re


def non_empty(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    return bool(value)


def enum(value, choices: list) -> bool:
    return value in choices


def enum_multi(values, choices: list) -> bool:
    if not values:
        return False
    return all(v in choices for v in values)


DURATION_PATTERN = re.compile(r"^\d+[mhdw]$")


def duration_string(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return bool(DURATION_PATTERN.match(value))


def exists_in_feature_db(value, **kwargs) -> bool:
    # 실제 Notion 조회는 호출 시점에 (notion_search_client 사용)
    return bool(value)


VALIDATORS = {
    "non_empty": lambda v, **_: non_empty(v),
    "enum": lambda v, choices=None, **_: enum(v, choices or []),
    "enum_multi": lambda v, choices=None, **_: enum_multi(v, choices or []),
    "duration_string": lambda v, **_: duration_string(v),
    "exists_in_feature_db": lambda v, **kw: exists_in_feature_db(v, **kw),
}


def validate_field(validator_name: str, value, **kwargs) -> bool:
    fn = VALIDATORS.get(validator_name)
    if fn is None:
        return True  # 알 수 없는 validator 는 통과
    return fn(value, **kwargs)
```

- [ ] **Step 3: PASS 확인 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_validators.py -v 2>&1 | tail -10
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/validators.py \
        skills/common/scripts/tests/test_validators.py && \
git commit -m "feat(common): 필드 validators (non_empty/enum/duration)"
```

---

### Task 2.2: `schema_loader.py`

- [ ] **Step 1: 테스트 작성**

`/Users/chuchu/testPlugin/skills/common/scripts/tests/test_schema_loader.py`:

```python
from schema_loader import load_schema, FieldSpec


def test_load_bug_fix():
    schema = load_schema("bug_fix")
    assert schema["work_type"] == "bug_fix"
    assert len(schema["required"]) == 6
    # 각 필드 스펙
    title = next(f for f in schema["required"] if f["id"] == "title")
    assert title["source"] == "auto_or_ask"
    assert title["validator"] == "non_empty"


def test_load_enhancement():
    schema = load_schema("enhancement")
    assert schema["work_type"] == "enhancement"
    assert len(schema["required"]) == 4


def test_unknown_work_type_raises():
    import pytest
    with pytest.raises(ValueError):
        load_schema("asdf")
```

- [ ] **Step 2: 구현**

```python
"""work-type-schemas/*.yaml 로더."""
from pathlib import Path
from typing import Any
import yaml

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "config" / "work-type-schemas"

_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def load_schema(work_type: str) -> dict[str, Any]:
    if work_type in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[work_type]
    path = SCHEMA_DIR / f"{work_type}.yaml"
    if not path.exists():
        raise ValueError(f"unknown work_type: {work_type}")
    with open(path) as f:
        data = yaml.safe_load(f)
    _SCHEMA_CACHE[work_type] = data
    return data


# FieldSpec 는 dict 로 충분 (의도적으로 Pydantic 도입 지연)
FieldSpec = dict[str, Any]
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_schema_loader.py -v 2>&1 | tail -10
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/schema_loader.py \
        skills/common/scripts/tests/test_schema_loader.py && \
git commit -m "feat(common): schema_loader + work-type-schema 로딩"
```

---

## Commit 3: `notion_search_client.py` (MCP 래퍼)

### Task 3.1: 키워드 검색 래퍼

**Files:**
- Create: `skills/common/scripts/notion_search_client.py`
- Create: `skills/common/scripts/tests/test_notion_search_client.py`

- [ ] **Step 1: 테스트 (mock 기반)**

```python
from unittest.mock import patch
from notion_search_client import search_features, FeatureMatch


@patch("notion_search_client._mcp_search")
def test_search_returns_top_5(mock_search):
    mock_search.return_value = [
        {"id": f"pid_{i}", "title": f"피처 {i}", "score": 1.0 - i*0.1}
        for i in range(10)
    ]
    result = search_features("로그인", max_results=5)
    assert len(result) == 5
    assert isinstance(result[0], FeatureMatch)
    assert result[0].title == "피처 0"


@patch("notion_search_client._mcp_search")
def test_search_empty_returns_empty(mock_search):
    mock_search.return_value = []
    assert search_features("asdf") == []


@patch("notion_search_client._mcp_search")
def test_search_filters_by_database(mock_search):
    mock_search.return_value = [
        {"id": "p1", "title": "피처1", "score": 0.9, "database_id": "DB_A"},
        {"id": "p2", "title": "피처2", "score": 0.8, "database_id": "DB_B"},
    ]
    result = search_features("kw", database_id="DB_A")
    assert len(result) == 1
    assert result[0].id == "p1"
```

- [ ] **Step 2: 구현**

```python
"""Notion 피처 DB 키워드 검색 래퍼.

MCP 의 notion-search 를 호출해 키워드 매칭 상위 N 개 반환.
실제 호출은 Claude (스킬 내부) 가 담당하며, 이 모듈은 Python 레벨에서
호출할 수 있는 동일 인터페이스를 제공한다 (테스트용 mock 지점).
"""
from dataclasses import dataclass


@dataclass
class FeatureMatch:
    id: str
    title: str
    score: float
    database_id: str = ""


def _mcp_search(query: str, **kwargs) -> list[dict]:
    """실제 구현은 MCP 호출.

    이 함수는 테스트에서 mock 되도록 설계.
    프로덕션에서는 스킬 내부에서 mcp__claude_ai_Notion__notion-search 호출 결과를 주입.
    """
    raise NotImplementedError(
        "이 함수는 직접 호출되지 않습니다. "
        "테스트에서 mock 하거나, 스킬이 MCP 결과를 주입해야 합니다."
    )


def search_features(
    query: str,
    max_results: int = 5,
    database_id: str | None = None,
) -> list[FeatureMatch]:
    raw = _mcp_search(query)
    if database_id:
        raw = [r for r in raw if r.get("database_id") == database_id]
    raw.sort(key=lambda r: r.get("score", 0), reverse=True)
    return [
        FeatureMatch(
            id=r["id"],
            title=r["title"],
            score=r.get("score", 0),
            database_id=r.get("database_id", ""),
        )
        for r in raw[:max_results]
    ]
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_notion_search_client.py -v 2>&1 | tail -10
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/notion_search_client.py \
        skills/common/scripts/tests/test_notion_search_client.py && \
git commit -m "feat(common): notion_search_client (키워드 검색 래퍼)"
```

---

## Commit 4: `field_collector.py` — 스키마 주도 수집

### Task 4.1: 핵심 수집 로직

**Files:**
- Create: `skills/common/scripts/field_collector.py`
- Create: `skills/common/scripts/tests/test_field_collector.py`

- [ ] **Step 1: 테스트**

```python
from field_collector import FieldCollector, CollectContext


def make_ctx(free_text="", pdf_text="", auto_extracted=None):
    return CollectContext(
        free_text=free_text,
        pdf_text=pdf_text,
        auto_extracted=auto_extracted or {},
    )


def test_auto_or_ask_uses_extracted():
    ctx = make_ctx(auto_extracted={"title": "로그인 버그"})
    c = FieldCollector("bug_fix")
    pending = c.identify_pending(ctx)
    ids = {f["id"] for f in pending}
    assert "title" not in ids  # 이미 채워짐


def test_auto_or_ask_falls_back_to_ask():
    ctx = make_ctx()
    c = FieldCollector("bug_fix")
    pending = c.identify_pending(ctx)
    ids = {f["id"] for f in pending}
    assert "title" in ids  # 비어있으니 질문 대상


def test_always_ask_field_in_pending():
    ctx = make_ctx(auto_extracted={"root_cause": "X"})
    c = FieldCollector("bug_fix")
    # source: ask 는 auto_extracted 있어도 질문 대상에 남음 (비교 위해)
    # 하지만 실무적으로 ask 필드도 auto_extracted 있으면 사용
    # 여기서는 auto_extracted 값을 우선
    pending = c.identify_pending(ctx)
    ids = {f["id"] for f in pending}
    assert "root_cause" not in ids


def test_phase_3_5_fields_not_in_initial_pending():
    c = FieldCollector("bug_fix")
    pending = c.identify_pending(make_ctx())
    ids = {f["id"] for f in pending}
    # phase_3_5_auto 는 나중에 채워지므로 초기 pending 에서 제외
    assert "estimated_duration" not in ids


def test_enhancement_required_count():
    c = FieldCollector("enhancement")
    pending = c.identify_pending(make_ctx())
    # enhancement 는 4개 required
    assert len(pending) == 4
```

- [ ] **Step 2: 구현**

```python
"""스키마 주도 필드 수집기.

파이프라인:
    1. identify_pending()  — 아직 값이 없는 필드 목록
    2. (스킬 코드가 각 필드에 대해 질문/조회 수행)
    3. validate()          — 최종 값 검증
"""
from dataclasses import dataclass, field as dc_field
from typing import Any

from schema_loader import load_schema
from validators import validate_field


ASKABLE_SOURCES = {"auto_or_ask", "ask", "ask_with_notion_lookup"}
# phase_1_2_auto, phase_3_5_auto 는 다른 단계에서 채워짐


@dataclass
class CollectContext:
    free_text: str = ""
    pdf_text: str = ""
    auto_extracted: dict[str, Any] = dc_field(default_factory=dict)


class FieldCollector:
    def __init__(self, work_type: str):
        self.schema = load_schema(work_type)
        self.required: list[dict] = self.schema.get("required", [])
        self.optional: list[dict] = self.schema.get("optional", [])

    def identify_pending(self, ctx: CollectContext) -> list[dict]:
        """아직 값이 없고, 현 단계에서 수집 가능한 필드 목록."""
        pending: list[dict] = []
        for field in self.required:
            fid = field["id"]
            source = field.get("source", "ask")

            # 이미 auto_extracted 에 값 있으면 스킵
            if fid in ctx.auto_extracted:
                continue

            # phase_* 로 미뤄진 필드는 여기서 제외
            if source not in ASKABLE_SOURCES:
                continue

            pending.append(field)
        return pending

    def validate(self, values: dict[str, Any]) -> tuple[bool, list[str]]:
        errors: list[str] = []
        for field in self.required:
            fid = field["id"]
            if fid not in values:
                errors.append(f"{fid} (필수) 누락")
                continue
            validator = field.get("validator")
            kwargs = {k: v for k, v in field.items() if k in ("choices",)}
            if validator and not validate_field(validator, values[fid], **kwargs):
                errors.append(f"{fid}: validator {validator} 실패 (값={values[fid]})")
        return (len(errors) == 0, errors)
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_field_collector.py -v 2>&1 | tail -10
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/field_collector.py \
        skills/common/scripts/tests/test_field_collector.py && \
git commit -m "feat(common): field_collector (스키마 주도 수집)"
```

---

## 완료 기준 (PR 3 Definition of Done)

- [ ] 3개 work-type-schema YAML 작성 완료
- [ ] `validators.py` — 5종 validator (non_empty, enum, enum_multi, duration_string, exists_in_feature_db)
- [ ] `schema_loader.py` — 캐시 포함
- [ ] `notion_search_client.py` — mock 가능한 구조
- [ ] `field_collector.py` — identify_pending + validate
- [ ] 모든 신규 테스트 PASS
- [ ] 기존 테스트 회귀 없음

---

## 다음 플랜

→ `docs/superpowers/plans/2026-04-22-04-spec-organizer-wrapper.md` (PR 4)
