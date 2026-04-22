# bug-spec-organizer 스킬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `skills/bug-spec-organizer/` 스킬을 완성해 버그 픽스 스펙을 대화형으로 수집하고 Notion 페이지로 생성한다. PDF 있을 때는 파싱 후 필드 자동 추출, 없을 때는 스키마 주도 질문.

**Architecture:** SKILL.md (~300줄) + `bug_input_collector.py` (field_collector 활용) + Notion 페이지 템플릿. 스킬 진입 시 컨텍스트 (profile, work_type, phases) 수신 → 필드 수집 → checklist.yaml 기반 엣지체크 → Notion publish.

**Tech Stack:** Markdown, Python, Notion MCP.

**Spec reference:** 설계 문서 섹션 5.3 (bug_fix.yaml)

**PR 번호:** 5/8

**Depends on:** PR 1, 2, 3, 4

---

## File Structure Overview

| 경로 | 유형 | 책임 |
|------|------|------|
| `skills/bug-spec-organizer/SKILL.md` | 생성 | 버그 전용 흐름 |
| `skills/bug-spec-organizer/scripts/_path_setup.py` | 생성 | |
| `skills/bug-spec-organizer/scripts/bug_input_collector.py` | 생성 | 대화/추출 로직 |
| `skills/bug-spec-organizer/scripts/bug_notion_builder.py` | 생성 | Notion 블록 구성 |
| `skills/bug-spec-organizer/scripts/tests/test_bug_input_collector.py` | 생성 | |
| `skills/bug-spec-organizer/scripts/tests/test_bug_notion_builder.py` | 생성 | |
| `skills/bug-spec-organizer/references/bug-template.md` | 생성 | Notion 페이지 구조 |
| `evals/trigger-eval-bug.json` | 생성 | 20 케이스 |

---

## Commit 1: 스킬 골격

### Task 1.1: 디렉터리 + _path_setup

- [ ] **Step 1: 구조 생성**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/bug-spec-organizer/scripts/tests
mkdir -p /Users/chuchu/testPlugin/skills/bug-spec-organizer/references
```

- [ ] **Step 2: _path_setup.py (PR 1 동일 패턴)**

`skills/bug-spec-organizer/scripts/_path_setup.py` — PR 1 의 `pdf-spec-organizer/scripts/_path_setup.py` 내용 복사.

- [ ] **Step 3: conftest.py (PR 4 동일 패턴)**

`skills/bug-spec-organizer/scripts/tests/conftest.py` 작성.

---

## Commit 2: `bug_input_collector.py`

### Task 2.1: PDF 파싱 텍스트 → 필드 자동 추출

**Files:**
- Create: `skills/bug-spec-organizer/scripts/bug_input_collector.py`
- Create: `skills/bug-spec-organizer/scripts/tests/test_bug_input_collector.py`

- [ ] **Step 1: 테스트**

```python
from bug_input_collector import (
    extract_fields_from_text,
    build_question_sequence,
    BugFields,
)


def test_extract_title_from_first_line():
    text = "로그인 시 흰 화면\n\n재현: 1. 로그인 탭\n2. ID 입력 후 버튼 탭\n3. 흰 화면 1분 유지"
    fields = extract_fields_from_text(text)
    assert fields.get("title") == "로그인 시 흰 화면"


def test_extract_symptom_from_structured():
    text = "제목\n\n## 증상\n- 로그인 후 흰 화면\n\n## 원인\n- 토큰 파싱 실패"
    fields = extract_fields_from_text(text)
    assert "흰 화면" in fields.get("symptom", "")


def test_platform_detection_ios():
    text = "로그인 버그\niOS 에서만 발생"
    fields = extract_fields_from_text(text)
    assert "iOS" in fields.get("affected_platforms", [])


def test_platform_detection_both():
    text = "로그인 버그\niOS 및 Android 양쪽에서 재현"
    fields = extract_fields_from_text(text)
    platforms = fields.get("affected_platforms", [])
    assert "iOS" in platforms and "Android" in platforms


def test_build_question_sequence_pending():
    extracted = {"title": "로그인 버그"}
    questions = build_question_sequence(extracted)
    # title 은 이미 채워짐 → 질문 대상 아님
    ids = [q["id"] for q in questions]
    assert "title" not in ids
    # root_cause 는 항상 ask
    assert "root_cause" in ids
```

- [ ] **Step 2: 구현**

```python
"""버그 픽스 입력 수집기.

PDF/텍스트에서 필드 자동 추출 시도 후 비어있는 것만 질문 대상으로 반환.
"""
import re
from dataclasses import dataclass
from typing import Any

from _path_setup import COMMON_SCRIPTS_DIR  # noqa: F401
from field_collector import FieldCollector, CollectContext


BugFields = dict[str, Any]


TITLE_PATTERNS = [
    re.compile(r"^#\s+(.+)$", re.MULTILINE),   # markdown h1
    re.compile(r"^(.+)\n={3,}", re.MULTILINE),  # setext h1
]

PLATFORM_KEYWORDS = {
    "iOS": ["ios", "아이폰", "애플"],
    "Android": ["android", "안드로이드", "갤럭시"],
    "공통": ["공통", "both", "양쪽", "둘 다"],
}


def _extract_title(text: str) -> str | None:
    for pat in TITLE_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    # fallback: 첫 비어있지 않은 줄
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:80]
    return None


def _extract_section(text: str, header_variants: list[str]) -> str | None:
    for header in header_variants:
        pat = re.compile(rf"^##?\s+{re.escape(header)}\s*$(.+?)(?=^##?\s|\Z)",
                         re.MULTILINE | re.DOTALL)
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


def _extract_platforms(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for platform, kws in PLATFORM_KEYWORDS.items():
        if any(kw in text_lower for kw in kws):
            found.append(platform)
    return found


def extract_fields_from_text(text: str) -> BugFields:
    if not text:
        return {}

    fields: BugFields = {}

    title = _extract_title(text)
    if title:
        fields["title"] = title

    symptom = _extract_section(text, ["증상", "symptom", "재현"])
    if symptom:
        fields["symptom"] = symptom

    cause = _extract_section(text, ["원인", "cause", "root cause"])
    if cause:
        fields["root_cause"] = cause

    plan = _extract_section(text, ["수정", "수정안", "fix", "solution"])
    if plan:
        fields["fix_plan"] = plan

    platforms = _extract_platforms(text)
    if platforms:
        fields["affected_platforms"] = platforms

    env = _extract_section(text, ["환경", "환경정보", "env"])
    if env:
        fields["reproduction_env"] = env

    return fields


def build_question_sequence(extracted: BugFields) -> list[dict]:
    collector = FieldCollector("bug_fix")
    ctx = CollectContext(auto_extracted=dict(extracted))
    return collector.identify_pending(ctx)
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/bug-spec-organizer/scripts/tests && \
python3 -m pytest test_bug_input_collector.py -v
cd /Users/chuchu/testPlugin && \
git add skills/bug-spec-organizer/scripts/_path_setup.py \
        skills/bug-spec-organizer/scripts/bug_input_collector.py \
        skills/bug-spec-organizer/scripts/tests/ && \
git commit -m "feat(bug): bug_input_collector — 텍스트 → 필드 추출"
```

---

## Commit 3: `bug_notion_builder.py`

### Task 3.1: Notion 블록 구성

- [ ] **Step 1: 테스트**

```python
from bug_notion_builder import build_bug_page_blocks, build_bug_properties


def test_page_blocks_structure():
    fields = {
        "title": "로그인 버그",
        "symptom": "흰 화면 1분",
        "root_cause": "토큰 파싱 실패",
        "fix_plan": "null 체크 추가",
        "affected_platforms": ["iOS"],
        "related_feature_id": "pid_login",
    }
    blocks = build_bug_page_blocks(fields)
    # 증상/원인/수정안/플랫폼 각 섹션 헤딩 존재
    heading_texts = [
        b["heading_2"]["rich_text"][0]["text"]["content"]
        for b in blocks if b.get("type") == "heading_2"
    ]
    assert "증상" in heading_texts
    assert "원인" in heading_texts
    assert "수정안" in heading_texts


def test_properties_include_work_type():
    fields = {"title": "t", "affected_platforms": ["iOS"], "priority": "High"}
    props = build_bug_properties(fields)
    assert props["work_type"]["select"]["name"] == "버그 픽스"
    assert props["priority"]["select"]["name"] == "High"


def test_related_feature_relation():
    fields = {"title": "t", "related_feature_id": "pid_abc"}
    props = build_bug_properties(fields)
    assert props["related_feature"]["relation"][0]["id"] == "pid_abc"
```

- [ ] **Step 2: 구현**

```python
"""버그 픽스 Notion 페이지 블록/프로퍼티 빌더."""
from typing import Any


def _heading_2(text: str) -> dict:
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def build_bug_page_blocks(fields: dict[str, Any]) -> list[dict]:
    blocks: list[dict] = []

    if fields.get("symptom"):
        blocks.append(_heading_2("증상"))
        blocks.append(_paragraph(fields["symptom"]))
        blocks.append(_divider())

    if fields.get("root_cause"):
        blocks.append(_heading_2("원인"))
        blocks.append(_paragraph(fields["root_cause"]))
        blocks.append(_divider())

    if fields.get("fix_plan"):
        blocks.append(_heading_2("수정안"))
        blocks.append(_paragraph(fields["fix_plan"]))
        blocks.append(_divider())

    if fields.get("reproduction_env"):
        blocks.append(_heading_2("재현 환경"))
        blocks.append(_paragraph(fields["reproduction_env"]))

    return blocks


def build_bug_properties(fields: dict[str, Any]) -> dict:
    props: dict = {
        "title": {
            "title": [{"text": {"content": fields.get("title", "(제목 없음)")}}]
        },
        "work_type": {"select": {"name": "버그 픽스"}},
    }

    if fields.get("affected_platforms"):
        props["affected_platforms"] = {
            "multi_select": [{"name": p} for p in fields["affected_platforms"]]
        }

    if fields.get("priority"):
        props["priority"] = {"select": {"name": fields["priority"]}}

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
cd /Users/chuchu/testPlugin/skills/bug-spec-organizer/scripts/tests && \
python3 -m pytest test_bug_notion_builder.py -v
cd /Users/chuchu/testPlugin && \
git add skills/bug-spec-organizer/scripts/bug_notion_builder.py \
        skills/bug-spec-organizer/scripts/tests/test_bug_notion_builder.py && \
git commit -m "feat(bug): Notion 페이지 블록/프로퍼티 빌더"
```

---

## Commit 4: `SKILL.md` + `references/bug-template.md`

### Task 4.1: 템플릿 문서

`skills/bug-spec-organizer/references/bug-template.md`:

```markdown
# 버그 픽스 Notion 페이지 템플릿

## 프로퍼티 (DB 속성)
- `title` (제목)
- `work_type` = "버그 픽스" (Select, 필수)
- `affected_platforms` (MultiSelect: iOS / Android / 공통)
- `priority` (Select: Critical / High / Medium / Low)
- `related_feature` (Relation → 피처 DB)
- `estimated_duration` (Rich text: "2h", "1d" 등)

## 페이지 본문 블록 순서
1. ## 증상 (재현 스텝)
2. ---
3. ## 원인
4. ---
5. ## 수정안
6. ---
7. ## 재현 환경 (선택)
8. ## 회귀 체크 결과 (checklist.yaml 통과/실패 요약)
```

### Task 4.2: SKILL.md

`skills/bug-spec-organizer/SKILL.md`:

```markdown
---
name: bug-spec-organizer
description: 버그 픽스 스펙을 Notion 피처 DB 에 작성. 재현 스텝, 원인, 수정안을 대화형으로 수집하고 회귀 방지 체크리스트를 적용. 트리거 예시: "로그인 버그 정리해줘", "이 QA 리포트 스펙화", "iOS 버그 픽스 Notion 생성".
allowed-tools:
  - Bash
  - Read
  - mcp__claude_ai_Notion__*
---

# bug-spec-organizer

**전제**: spec-organizer wrapper 가 이 스킬을 호출한 상태. 컨텍스트로 받은 값:
- `profile`: InputProfile (pdf_paths, free_text, urls)
- `work_type`: "bug_fix"
- `phases`: {"1": "parse_only", "3": "full", "5": "full"} (예)

## Phase 1: 입력 텍스트 수집 (parse_only)

phases 에 "1" 이 있으면 PDF 파싱. common/scripts/parse_pdf.py 는 PDF 전용이므로 재사용.

```bash
for pdf in ${PROFILE_PDF_PATHS[@]}; do
  python skills/pdf-spec-organizer/scripts/parse_pdf.py "$pdf" > "/tmp/bug_$$_$(basename $pdf).txt"
done
```

텍스트 병합 → `$INPUT_TEXT` 변수.

## Phase 2: 필드 자동 추출 + 대화형 수집

```bash
python skills/bug-spec-organizer/scripts/bug_input_collector.py extract --text "$INPUT_TEXT"
# 출력: 자동 추출된 필드 JSON
```

그 후 `build_question_sequence` 가 pending 필드 반환.

각 pending 필드에 대해 **1문장씩 대화형 질문**:

1. `title` (없으면): "짧은 한 줄 제목은?"
2. `symptom` (없으면): "어떤 동작이 잘못되나요? (재현 스텝)"
3. `root_cause` (항상): "원인은?"
4. `fix_plan` (항상): "수정 계획은?"
5. `affected_platforms` (없으면): "영향 플랫폼? [iOS/Android/공통]"
6. `related_feature_id` (항상): Notion 피처 DB 키워드 검색

### Notion 피처 검색

```
사용자: "로그인"
스킬: mcp__claude_ai_Notion__notion-search("로그인", database_id=FEATURE_DB_ID)
스킬: 상위 5개 표시 → 번호 선택
```

### 선택 필드 질문

- `priority`: "우선순위? [Critical/High/Medium/Low] (기본: Medium)"
- `reproduction_env`: 자동 추출됐으면 확인만, 없으면 "재현 환경?"

## Phase 3: 엣지케이스 체크 (bug_fix 필터)

`common/config/checklist.yaml` 에서 `applies_to_work_type: [bug_fix]` 인 카테고리만 체크:
- error_handling, offline, a11y (공통)
- regression_scope, reproduction_conditions (버그 전용)

각 카테고리에 대해 예/아니오/해당없음 선택.

## Phase 5: Notion Publish

```bash
python skills/bug-spec-organizer/scripts/bug_notion_builder.py build \
  --fields-json /tmp/fields.json > /tmp/page_payload.json
```

그 후 `mcp__claude_ai_Notion__notion-create-pages` 호출:
- properties: `build_bug_properties()` 결과
- children (블록): `build_bug_page_blocks()` 결과

**재시도**: common/scripts/notion_client.py 의 `with_retry` 사용 (PR 8 구현 예정).

## 결과 요약

사용자에게:
```
✅ 버그 픽스 Notion 페이지 생성 완료
  URL: https://notion.so/...
  제목: [버그 제목]
  플랫폼: iOS, Android
  우선순위: High
```

## 참조

- 템플릿: references/bug-template.md
- checklist.yaml: common/config/checklist.yaml
- 스키마: common/config/work-type-schemas/bug_fix.yaml
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/bug-spec-organizer/ && \
git commit -m "feat(bug): SKILL.md + bug-template references"
```

---

## Commit 5: trigger-eval + 등록

### Task 5.1: `evals/trigger-eval-bug.json`

```json
{
  "skill": "bug-spec-organizer",
  "version": 1,
  "cases": [
    {"query": "로그인 버그 정리해줘", "should_trigger": true},
    {"query": "이 QA 리포트 스펙화", "should_trigger": true},
    {"query": "iOS 버그 픽스 Notion 생성", "should_trigger": true},
    {"query": "어제 발견한 오류 티켓 만들어줘", "should_trigger": true},
    {"query": "크래시 리포트 문서화", "should_trigger": true},
    {"query": "로그인 실패하는 버그", "should_trigger": true},
    {"query": "에러 원인 분석 기록", "should_trigger": true},
    {"query": "재현 스텝 Notion 에 남겨줘", "should_trigger": true},
    {"query": "이 스크린샷 버그 제보", "should_trigger": true},
    {"query": "결제 실패 버그 Notion", "should_trigger": true},

    {"query": "새 결제 기능 기획", "should_trigger": false},
    {"query": "색상 개선 방안", "should_trigger": false},
    {"query": "API 문서 작성", "should_trigger": false},
    {"query": "코드 리뷰", "should_trigger": false},
    {"query": "서버 배포", "should_trigger": false},
    {"query": "로그 분석", "should_trigger": false},
    {"query": "이 PDF 기획서 파싱", "should_trigger": false},
    {"query": "새 피처 추가 기획", "should_trigger": false},
    {"query": "유닛 테스트 작성", "should_trigger": false},
    {"query": "회의록 정리", "should_trigger": false}
  ]
}
```

### Task 5.2: `.claude-plugin/plugin.json` 등록

- [ ] **Step 1: skills 배열에 추가**

```json
{ "name": "bug-spec-organizer", "path": "skills/bug-spec-organizer" }
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add evals/trigger-eval-bug.json .claude-plugin/plugin.json && \
git commit -m "feat(bug): trigger-eval + 플러그인 등록"
```

---

## Commit 6: E2E 테스트

### Task 6.1: 샘플 버그 → Notion 페이지 (mock)

**Files:**
- Create: `evals/e2e/bug_fix_minimal.md`

```markdown
# E2E: 버그 픽스 최소 입력

## 입력
- free_text: "로그인 버그"

## 기대 흐름
1. spec-organizer 가 text_or_link_bug 라우트 반환
2. bug-spec-organizer 호출
3. 스킬이 다음 질문 순차 제시:
   - "짧은 제목은?" → "로그인 실패"
   - "재현 스텝?" → "ID 입력 → 버튼 탭 → 흰 화면"
   - "원인?" → "토큰 파싱 실패"
   - "수정 계획?" → "null 체크 추가"
   - "영향 플랫폼?" → "iOS"
   - "관련 피처?" → "로그인 피처" (Notion 검색 → 선택)
   - "우선순위?" → "High"
4. 엣지케이스 체크 (5개 카테고리)
5. Notion 페이지 생성

## 기대 출력
- properties.work_type = "버그 픽스"
- affected_platforms = ["iOS"]
- priority = "High"
- related_feature relation 있음
- 본문에 증상/원인/수정안 섹션
```

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add evals/e2e/ && \
git commit -m "test(e2e): 버그 픽스 최소 입력 시나리오 문서"
```

---

## 완료 기준 (PR 5 Definition of Done)

- [ ] `skills/bug-spec-organizer/` 구조 완성
- [ ] `bug_input_collector.py` 텍스트 추출 테스트 PASS
- [ ] `bug_notion_builder.py` 블록 빌더 테스트 PASS
- [ ] SKILL.md ~300줄 수준
- [ ] trigger-eval-bug 20/20 케이스
- [ ] E2E 시나리오 문서
- [ ] plugin.json 등록

---

## 다음 플랜

→ `docs/superpowers/plans/2026-04-22-06-enhancement-spec-organizer.md` (PR 6)
