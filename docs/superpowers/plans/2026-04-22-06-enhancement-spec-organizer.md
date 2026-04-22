# enhancement-spec-organizer 스킬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `skills/enhancement-spec-organizer/` 스킬을 완성해 기능 강화 스펙을 대화형으로 수집하고 Notion 페이지로 생성한다. Phase 3 (엣지체크 풀), Phase 3.5 (메타 생성), Phase 4 (플랫폼 노트) 포함.

**Architecture:** PR 5 (bug-spec-organizer) 와 동일 패턴을 따르되 스키마가 다름. `enhancement_input_collector.py` + `enhancement_notion_builder.py` + SKILL.md. Phase 3.5 는 `common/scripts/enrich_features.py` 재사용.

**Tech Stack:** Markdown, Python, Notion MCP.

**Spec reference:** 설계 문서 섹션 5.4 (enhancement.yaml)

**PR 번호:** 6/8

**Depends on:** PR 1, 2, 3, 4

---

## File Structure Overview

| 경로 | 유형 |
|------|------|
| `skills/enhancement-spec-organizer/SKILL.md` | 생성 |
| `skills/enhancement-spec-organizer/scripts/_path_setup.py` | 생성 |
| `skills/enhancement-spec-organizer/scripts/enhancement_input_collector.py` | 생성 |
| `skills/enhancement-spec-organizer/scripts/enhancement_notion_builder.py` | 생성 |
| `skills/enhancement-spec-organizer/scripts/tests/*.py` | 생성 |
| `skills/enhancement-spec-organizer/references/enhancement-template.md` | 생성 |
| `evals/trigger-eval-enhancement.json` | 생성 |
| `evals/e2e/enhancement_with_url.md` | 생성 |

---

## Commit 1: 스킬 골격 (PR 5 패턴 복제)

### Task 1.1: 구조 생성

- [ ] **Step 1: 디렉터리**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/enhancement-spec-organizer/{scripts/tests,references}
```

- [ ] **Step 2: `_path_setup.py`, `conftest.py`**

PR 5 Task 1.1 와 동일 내용으로 생성.

---

## Commit 2: `enhancement_input_collector.py`

### Task 2.1: 자유 서술/링크에서 필드 추출

- [ ] **Step 1: 테스트**

```python
from enhancement_input_collector import extract_fields_from_text, build_question_sequence


def test_extract_title_and_change():
    text = "로그인에 애플 로그인 버튼 추가. iOS 13+ 에서 필수."
    fields = extract_fields_from_text(text)
    # 첫 문장이 title, 전체가 change_description 으로 매핑 기본
    assert "애플 로그인" in fields.get("title", "") or "애플 로그인" in fields.get("change_description", "")


def test_extract_platforms():
    text = "다크모드 지원 추가. iOS 및 Android 공통."
    fields = extract_fields_from_text(text)
    platforms = fields.get("target_platforms", [])
    assert "iOS" in platforms or "공통" in platforms


def test_extract_reason_from_because():
    text = "로그인 애니메이션 개선. 사용자 피드백에서 느리다는 지적이 많음."
    fields = extract_fields_from_text(text)
    assert fields.get("reason")  # 두 번째 문장이 reason 에 매핑


def test_build_question_sequence_pending():
    extracted = {"title": "애플 로그인 추가"}
    pending = build_question_sequence(extracted)
    ids = [q["id"] for q in pending]
    # title 이미 있음
    assert "title" not in ids
    # related_feature_id 는 ask_with_notion_lookup → 항상 질문
    assert "related_feature_id" in ids
```

- [ ] **Step 2: 구현**

```python
"""기능 강화 입력 수집기.

자유 서술/링크에서 최대한 추출, 나머지는 질문 대상으로 반환.
"""
import re
from typing import Any

from _path_setup import COMMON_SCRIPTS_DIR  # noqa: F401
from field_collector import FieldCollector, CollectContext


PLATFORM_KEYWORDS = {
    "iOS": ["ios", "아이폰"],
    "Android": ["android", "안드로이드"],
    "공통": ["공통", "양쪽", "둘 다", "both"],
}

REASON_MARKERS = ["때문에", "왜냐면", "because", "이유는", "피드백", "가이드라인"]


def _first_sentence(text: str) -> str:
    # 단순 문장 분리
    m = re.search(r"^(.+?[.!?。\n])", text.strip())
    return (m.group(1) if m else text[:80]).strip(" .!?。\n")


def _detect_platforms(text: str) -> list[str]:
    t = text.lower()
    found = []
    for platform, kws in PLATFORM_KEYWORDS.items():
        if any(kw in t for kw in kws):
            found.append(platform)
    return found


def _extract_reason(text: str) -> str | None:
    for marker in REASON_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            # marker 포함 문장 추출
            sentences = re.split(r"[.。\n]", text)
            for s in sentences:
                if marker in s:
                    return s.strip(" .!?。\n")
    return None


def extract_fields_from_text(text: str) -> dict[str, Any]:
    if not text:
        return {}

    fields: dict[str, Any] = {}

    first = _first_sentence(text)
    if first:
        fields["title"] = first[:80]
        fields["change_description"] = text.strip()

    platforms = _detect_platforms(text)
    if platforms:
        fields["target_platforms"] = platforms

    reason = _extract_reason(text)
    if reason:
        fields["reason"] = reason

    return fields


def build_question_sequence(extracted: dict[str, Any]) -> list[dict]:
    collector = FieldCollector("enhancement")
    ctx = CollectContext(auto_extracted=dict(extracted))
    return collector.identify_pending(ctx)
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/enhancement-spec-organizer/scripts/tests && \
python3 -m pytest -v
cd /Users/chuchu/testPlugin && \
git add skills/enhancement-spec-organizer/scripts/ && \
git commit -m "feat(enh): enhancement_input_collector"
```

---

## Commit 3: `enhancement_notion_builder.py`

### Task 3.1: Notion 블록/프로퍼티

- [ ] **Step 1: 테스트**

```python
from enhancement_notion_builder import build_enh_page_blocks, build_enh_properties


def test_blocks_contain_sections():
    fields = {
        "title": "애플 로그인",
        "change_description": "로그인에 Apple ID 추가",
        "reason": "iOS 13+ 가이드라인",
        "target_platforms": ["iOS"],
        "related_feature_id": "pid_login",
    }
    blocks = build_enh_page_blocks(fields)
    heading_texts = [
        b["heading_2"]["rich_text"][0]["text"]["content"]
        for b in blocks if b.get("type") == "heading_2"
    ]
    assert "변경 내용" in heading_texts
    assert "변경 이유" in heading_texts


def test_properties_work_type():
    props = build_enh_properties({"title": "t"})
    assert props["work_type"]["select"]["name"] == "기능 강화"
```

- [ ] **Step 2: 구현**

```python
"""기능 강화 Notion 페이지 빌더."""
from typing import Any


def _h2(text: str) -> dict:
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }


def _p(text: str) -> dict:
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def build_enh_page_blocks(fields: dict[str, Any]) -> list[dict]:
    blocks: list[dict] = []

    if fields.get("reason"):
        blocks.append(_h2("변경 이유 (배경)"))
        blocks.append(_p(fields["reason"]))
        blocks.append(_divider())

    if fields.get("change_description"):
        blocks.append(_h2("변경 내용"))
        blocks.append(_p(fields["change_description"]))
        blocks.append(_divider())

    # Phase 3.5 가 채우는 메타 섹션
    if fields.get("dependencies"):
        blocks.append(_h2("타 팀 의존성"))
        blocks.append(_p(fields["dependencies"]))
        blocks.append(_divider())

    if fields.get("missing_items"):
        blocks.append(_h2("기획 누락 제안"))
        blocks.append(_p(fields["missing_items"]))

    return blocks


def build_enh_properties(fields: dict[str, Any]) -> dict:
    props: dict = {
        "title": {"title": [{"text": {"content": fields.get("title", "(제목 없음)")}}]},
        "work_type": {"select": {"name": "기능 강화"}},
    }

    if fields.get("target_platforms"):
        props["target_platforms"] = {
            "multi_select": [{"name": p} for p in fields["target_platforms"]]
        }

    if fields.get("related_feature_id"):
        props["related_feature"] = {
            "relation": [{"id": fields["related_feature_id"]}]
        }

    if fields.get("estimated_duration"):
        props["estimated_duration"] = {
            "rich_text": [{"text": {"content": fields["estimated_duration"]}}]
        }

    return props
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/enhancement-spec-organizer/scripts/tests && \
python3 -m pytest test_enhancement_notion_builder.py -v
cd /Users/chuchu/testPlugin && \
git add skills/enhancement-spec-organizer/scripts/enhancement_notion_builder.py \
        skills/enhancement-spec-organizer/scripts/tests/test_enhancement_notion_builder.py && \
git commit -m "feat(enh): Notion 페이지 블록/프로퍼티 빌더"
```

---

## Commit 4: SKILL.md + 템플릿

### Task 4.1: `references/enhancement-template.md`

```markdown
# 기능 강화 Notion 페이지 템플릿

## 프로퍼티
- `title`
- `work_type` = "기능 강화"
- `target_platforms` (MultiSelect)
- `related_feature` (Relation → 피처 DB, 필수)
- `estimated_duration` (Rich text)

## 페이지 본문 순서
1. ## 변경 이유 (배경)
2. ---
3. ## 변경 내용
4. ---
5. ## 엣지케이스 체크 결과 (Phase 3)
6. ---
7. ## 타 팀 의존성 (Phase 3.5)
8. ---
9. ## 기획 누락 제안 (Phase 3.5)
10. ---
11. ## iOS 개발자 노트 (Phase 4)
12. ## Android 개발자 노트 (Phase 4)
```

### Task 4.2: SKILL.md

```markdown
---
name: enhancement-spec-organizer
description: 기존 피처의 기능 강화/개선 스펙을 Notion 에 작성. 자유 서술이나 GitHub/Slack 링크를 받아 자동 파싱 후 부족한 필드만 질문. 트리거 예시: "다크모드 개선", "로그인 강화", "기존 피처에 옵션 추가".
allowed-tools:
  - Bash
  - Read
  - mcp__claude_ai_Notion__*
---

# enhancement-spec-organizer

**전제**: spec-organizer 가 이 스킬을 `pdf_count=0 + has_text_or_link + work_type=enhancement` 또는 `pdf_count=1 + work_type=enhancement` 상황에서 호출.

## Phase 1: 입력 텍스트 획득 (PDF 있으면 parse_only)

PDF 있을 때: `parse_pdf.py` 로 텍스트 추출.
텍스트/링크만: `profile.free_text` + URL 목록 그대로 사용.

## Phase 2 대체: 필드 자동 추출

```bash
python skills/enhancement-spec-organizer/scripts/enhancement_input_collector.py \
  extract --text "$INPUT_TEXT"
```

반환된 JSON 의 pending 필드에 대해 1문장씩 대화형 질문:

1. `title` (없으면): "강화 제목은?"
2. `related_feature_id` (항상): Notion 피처 DB 키워드 검색 → 상위 5개 중 선택
3. `target_platforms` (없으면): "대상 플랫폼? [iOS/Android/공통]"
4. `change_description` (없으면): "어떻게 바뀌는지?"

선택 필드:
- `reason` 자동 추출됐으면 확인, 없으면 "변경 이유는?"

## Phase 3: 엣지케이스 체크 (풀 — 6개)

`common/config/checklist.yaml` 의 `applies_to_work_type` 에 `enhancement` 포함된 카테고리만:
- error_handling, empty_state, offline, permission, loading, a11y (6개 공통)

각 카테고리에 대해 예/아니오/해당없음.

## Phase 3.5: 메타 생성 (풀)

`common/scripts/enrich_features.py` 호출. 입력은 현재 수집된 필드.

반환 필드:
- `estimated_duration` (예: "2d")
- `dependencies` (타 팀 의존성 리스트)
- `missing_items` (기획 누락 제안)

**주의**: Phase 3.5 실패 시 경고 후 스킵 (빈 필드로 진행). PR 8 의 Pydantic 검증 적용.

## Phase 4: 플랫폼 노트 (iOS/Android)

선택된 `target_platforms` 각각에 대해 개발자 노트 작성 질문:
- "iOS 구현 특이사항?"
- "Android 구현 특이사항?"

## Phase 5: Notion Publish

```bash
python skills/enhancement-spec-organizer/scripts/enhancement_notion_builder.py build \
  --fields-json /tmp/fields.json > /tmp/page_payload.json
```

`mcp__claude_ai_Notion__notion-create-pages` 호출 (with_retry 적용).

## 결과

```
✅ 기능 강화 Notion 페이지 생성 완료
  URL: https://notion.so/...
  제목: [강화 제목]
  관련 피처: [로그인 피처]
  플랫폼: iOS, Android
  예상 기간: 2d
```

## brainstorming 귀환 처리

wrapper 가 brainstorming 을 거쳐 `expected_return` 으로 이 스킬 재진입 시:
- `text_summary` 를 INPUT_TEXT 로 사용
- `requirements` 를 change_description 에 반영 또는 저장
- `design_doc_path` 가 있으면 `source_design_doc` optional 필드에 URL 형태로 저장

## 참조

- 템플릿: references/enhancement-template.md
- 스키마: common/config/work-type-schemas/enhancement.yaml
```

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/enhancement-spec-organizer/SKILL.md \
        skills/enhancement-spec-organizer/references/ && \
git commit -m "feat(enh): SKILL.md + 템플릿"
```

---

## Commit 5: trigger-eval + 등록 + E2E

### Task 5.1: `evals/trigger-eval-enhancement.json`

```json
{
  "skill": "enhancement-spec-organizer",
  "version": 1,
  "cases": [
    {"query": "다크모드 개선", "should_trigger": true},
    {"query": "로그인에 애플 로그인 추가", "should_trigger": true},
    {"query": "기존 검색 속도 개선", "should_trigger": true},
    {"query": "프로필 편집 UX 강화", "should_trigger": true},
    {"query": "결제 플로우 단축", "should_trigger": true},
    {"query": "알림 옵션 추가", "should_trigger": true},
    {"query": "기존 피처 enhancement", "should_trigger": true},
    {"query": "홈 화면 개선 방안", "should_trigger": true},
    {"query": "버튼 크기 조정 스펙", "should_trigger": true},
    {"query": "피드백 기반 개선", "should_trigger": true},

    {"query": "로그인 버그 있음", "should_trigger": false},
    {"query": "새 결제 시스템 기획", "should_trigger": false},
    {"query": "크래시 리포트", "should_trigger": false},
    {"query": "코드 리팩터링", "should_trigger": false},
    {"query": "서버 배포", "should_trigger": false},
    {"query": "API 문서", "should_trigger": false},
    {"query": "SQL 쿼리 최적화", "should_trigger": false},
    {"query": "이 PDF 기획서 파싱", "should_trigger": false},
    {"query": "QA 테스트", "should_trigger": false},
    {"query": "번역 작업", "should_trigger": false}
  ]
}
```

### Task 5.2: `.claude-plugin/plugin.json`

```json
{ "name": "enhancement-spec-organizer", "path": "skills/enhancement-spec-organizer" }
```

### Task 5.3: E2E `evals/e2e/enhancement_with_url.md`

```markdown
# E2E: 기능 강화 + URL 입력

## 입력
- free_text: "로그인에 애플 로그인 추가"
- urls: ["https://github.com/example/issues/42"]

## 기대 흐름
1. spec-organizer → text_or_link_enh 라우트
2. enhancement-spec-organizer 호출
3. 자동 추출: title="로그인에 애플 로그인 추가", change_description=전체
4. 질문:
   - 관련 기존 피처? → "로그인 피처" 검색 → 선택
   - 대상 플랫폼? → "iOS"
5. Phase 3: 6개 엣지케이스 체크
6. Phase 3.5: enrich_features 로 duration/dependencies/missing 자동 생성
7. Phase 4: iOS 노트 작성 ("Apple Sign In SDK 연동")
8. Phase 5: Notion 페이지 생성

## 기대 출력
- work_type = "기능 강화"
- target_platforms = ["iOS"]
- related_feature relation
- estimated_duration 자동 채움
- 본문에 reason/change_description/dependencies/missing_items + iOS 노트
- source_design_doc 필드에 URL 저장
```

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add evals/trigger-eval-enhancement.json \
        evals/e2e/enhancement_with_url.md \
        .claude-plugin/plugin.json && \
git commit -m "test(enh): trigger-eval + e2e + 플러그인 등록"
```

---

## 완료 기준 (PR 6)

- [ ] `enhancement-spec-organizer` 구조 완성
- [ ] 텍스트 추출 + Notion 빌더 테스트 PASS
- [ ] SKILL.md 완성 (~400줄)
- [ ] trigger-eval-enhancement 20 케이스
- [ ] E2E 시나리오
- [ ] plugin.json 등록

---

## 다음 플랜

→ `docs/superpowers/plans/2026-04-22-07-checklist-migration.md` (PR 7)
