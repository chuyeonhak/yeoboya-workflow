# spec-organizer Wrapper 스킬 설계 문서

**작성일**: 2026-04-22
**버전**: v1 설계
**대상 릴리스**: yeoboya-workflow v1.0.0

---

## 1. 배경 및 목표

### 1.1 현재 상황

`yeoboya-workflow` 플러그인은 v0.4.0 기준으로 `/spec-from-pdf` 를 통해 PDF 기획서를 Notion 피처 DB에 구조화하여 저장한다. 그러나 실제 개발 작업은 세 가지 성격으로 나뉜다.

- **새 기능 (new feature)**: 기획자가 PDF 기획서를 제공하는 전통적 흐름
- **버그 픽스 (bug fix)**: PDF 없이 재현 스텝과 원인만 있는 경우가 대부분
- **기능 강화 (enhancement)**: Slack 메시지 수준의 소규모 개선 요청

현 플러그인은 **새 기능만** 지원하며, 버그 픽스·기능 강화는 Notion 에 기록할 표준 절차가 없어 팀 간 일관성이 떨어진다.

### 1.2 목표

- **단일 진입점** (`spec-organizer` 스킬) 에서 모든 작업 유형을 수용
- **PDF 유무와 관계없이** 스펙 생성 가능
- 기존 `/spec-from-pdf` 사용자 경험을 **해치지 않음** (deprecation 경고 경로로 흡수)
- 한계 분석(2026-04-22)에서 지적된 **silent failure** 3건 해결

### 1.3 비목표 (v1에서 제외)

- 외부 링크(GitHub Issue, Linear, Slack URL) 내용 파싱 → v2
- PII 스캔을 자유 서술 텍스트까지 확장 → v2
- 다국어(영어 PDF) 지원 → v2
- 기존 Notion 페이지 일괄 backfill → v1.5 (별도 커맨드)
- work_type 변경 (`/spec-promote`) → v2

---

## 2. 아키텍처 개요

### 2.1 디렉터리 구조

```
skills/
  common/                               # 공유 코어
    scripts/
      dispatcher.py                     # 결정적 라우팅 레이어
      routing.py                        # routing.yaml 해석
      work_type_normalizer.py           # canonical + alias
      field_collector.py                # 스키마 주도 수집
      notion_client.py                  # exponential backoff 래퍼
      page_publisher.py                 # chunk + 체크포인트
      note_extractor.py                 # --schema 플래그
      note_merger.py                    # --schema 플래그
      feature_id.py                     # 이동 (기존 재사용)
      pdf_hash.py                       # 이동
      pii_scan.py                       # 이동
      enrich_features.py                # 이동 (Pydantic 스키마 검증 추가)
    config/
      routing.yaml                      # 2D 매트릭스
      work-types.yaml                   # canonical + alias
      checklist.yaml                    # applies_to_work_type 필드 추가
      work-type-schemas/
        new_feature.yaml
        bug_fix.yaml
        enhancement.yaml

  spec-organizer/                       # Wrapper 스킬 (~200줄)
    SKILL.md
    scripts/
      dispatch.py                       # Skill tool 연쇄 호출

  pdf-spec-organizer/                   # PDF + 새 기능 (~600줄, 축소)
    SKILL.md
    scripts/
      parse_pdf.py

  bug-spec-organizer/                   # 신규 (~300줄)
    SKILL.md
    scripts/
      bug_input_collector.py

  enhancement-spec-organizer/           # 신규 (~400줄)
    SKILL.md
    scripts/
      enhancement_input_collector.py

commands/
  spec-from-pdf.md   # deprecated, 즉시 위임
  spec-update.md     # deprecated, 즉시 위임
  spec-resume.md     # deprecated, 즉시 위임
```

### 2.2 공유 방식

`common/` 은 Python path hack 으로 공유한다 (v1 MVP):

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "common" / "scripts"))
from dispatcher import resolve_route
```

v1.5 이후 필요 시 pip 패키지로 승격 검토.

### 2.3 실행 흐름

```
사용자 입력
    ↓
[spec-organizer 스킬]
    ↓
[dispatcher.py]
    ├─ build_input_profile()
    ├─ detect_mode()              # create | resume | update
    ├─ detect_work_type()         # 결정적 + ASK fallback
    └─ resolve_route()            # routing.yaml
    ↓
[route.skill 서브 스킬]
    ├─ pdf-spec-organizer
    ├─ bug-spec-organizer
    ├─ enhancement-spec-organizer
    └─ superpowers:brainstorming  (Skill tool 연쇄)
    ↓
[field_collector.py]              # 스키마 주도 질문
    ↓
[Phase 실행]                      # work_type별 구성
    ↓
Notion 페이지 생성/업데이트
```

---

## 3. 라우팅 매트릭스

### 3.1 최상위 축: `mode`

세 가지 생명주기를 분리한다. 이번 릴리스의 매트릭스는 `create` 에만 적용된다.

| mode | 설명 | 기존 커맨드 |
|------|------|-------------|
| `create` | 새 스펙 생성 | `/spec-from-pdf` |
| `resume` | 중단된 작업 복구 | `/spec-resume` |
| `update` | 기존 페이지 편집 | `/spec-update` |

`resume`, `update` 는 각각 `common/scripts/resume_handler.py`, `update_handler.py` 로 위임한다.

### 3.2 입력 프로필 모델

자의적 임계값(예: "20자 이상") 을 제거하고 파일 실존·확장자·URL 스킴으로만 판정한다.

```python
@dataclass
class InputProfile:
    pdf_paths: list[Path]
    image_paths: list[Path]
    urls: list[str]
    free_text: str
```

경로 정규화는 `os.path.realpath(os.path.expanduser())`, URL 판정은 `^https?://` 스킴 매칭.

### 3.3 work_type 감지 파이프라인

```python
def detect_work_type(profile: InputProfile, user_hint: str | None) -> WorkType | Literal["ASK"]:
    # 규칙 1: 사용자 명시
    if user_hint:
        return normalize_work_type(user_hint)

    # 규칙 2: free_text 키워드 (결정적)
    text = profile.free_text.lower()
    if any(kw in text for kw in ["버그", "bug", "오류", "fix", "수정", "에러"]):
        return WorkType.BUG_FIX
    if any(kw in text for kw in ["개선", "강화", "추가", "enhancement"]):
        return WorkType.ENHANCEMENT

    # 규칙 3: Claude 분류 필요 (길이 충분)
    if len(text) > 10:
        return "ASK"

    # 규칙 4: 기본값 추론
    if profile.pdf_paths and not profile.free_text:
        return WorkType.NEW_FEATURE

    return "ASK"
```

### 3.4 `routing.yaml` (create 모드)

위에서 아래로 평가, 첫 매치 적용.

```yaml
version: 2

modes:
  create:
    routes:
      - id: pdf_single_new
        when: { pdf_count: 1, work_type: new_feature }
        skill: pdf-spec-organizer
        phases: { 1: full, 2: full, 3: full, 3.5: full, 4: full, 5: full }

      - id: pdf_single_bug
        when: { pdf_count: 1, work_type: bug_fix }
        skill: bug-spec-organizer
        phases: { 1: parse_only, 3: full, 5: full }
        note: "PDF를 QA 버그 리포트로 해석, Phase 2 스킵"

      - id: pdf_single_enh
        when: { pdf_count: 1, work_type: enhancement }
        skill: enhancement-spec-organizer
        phases: { 1: parse_only, 3: full, 3.5: full, 4: full, 5: full }

      - id: pdf_multi_bug
        when: { pdf_count: ">=2", work_type: bug_fix }
        skill: bug-spec-organizer
        phases: { 1: parse_all, 3: full, 5: full }

      - id: pdf_multi_other
        when: { pdf_count: ">=2", work_type: [new_feature, enhancement] }
        action: prompt
        choices:
          - first_only: "첫 번째 PDF만 사용"
          - sequential: "순차 처리 (각각 별도 스펙)"
          - cancel: "취소"

      - id: image_only_bug
        when: { pdf_count: 0, image_count: ">=1", work_type: bug_fix }
        action: block
        message: "이미지만으로 버그 제보는 v1.5에서 지원 예정. 현재는 텍스트 설명이나 PDF로 업로드해주세요."

      - id: text_or_link_new
        when: { pdf_count: 0, has_text_or_link: true, work_type: new_feature }
        action: redirect
        target: superpowers:brainstorming
        handoff_contract:
          input: { free_text: str, urls: list[str] }
          expected_return: { work_type: str, text_summary: str, requirements: list[str], design_doc_path: str }
          reentry_route: text_or_link_enh
        failure_fallback:
          action: prompt
          message: "Brainstorming 결과를 받지 못했습니다. 수동으로 요구사항을 입력할까요?"
          choices: [retry, manual, cancel]

      - id: text_or_link_bug
        when: { pdf_count: 0, has_text_or_link: true, work_type: bug_fix }
        skill: bug-spec-organizer
        phases: { 3: full, 5: full }

      - id: text_or_link_enh
        when: { pdf_count: 0, has_text_or_link: true, work_type: enhancement }
        skill: enhancement-spec-organizer
        phases: { 3: full, 3.5: full, 4: full, 5: full }

      - id: pdf_single_unknown
        when: { pdf_count: 1, work_type: unknown }
        action: prompt
        default_suggestion: new_feature
        questions:
          - "이 PDF는 [1] 새 기능 [2] 버그 픽스 [3] 기능 강화 중 어느 것인가요?"

      - id: empty
        when: { pdf_count: 0, image_count: 0, has_text_or_link: false }
        action: prompt
        questions:
          - "어떤 작업인가요? [1] 새 기능 [2] 버그 픽스 [3] 기능 강화"
          - "작업 내용을 한 문장으로 설명해주세요"
        then_reentry: true

    unmatched:
      action: error
      message: "라우팅 규칙에 일치하는 항목이 없습니다. 버그 리포트를 남겨주세요."
```

### 3.5 Phase 구성표

| Phase | 이름 | new_feature | bug_fix | enhancement |
|-------|------|:-----------:|:-------:|:-----------:|
| 1 | PDF 파싱 | full | parse_only | parse_only |
| 2 | 피처 경계 | full | skip | skip |
| 3 | 엣지케이스 체크 | full | full (checklist 필터) | full |
| 3.5 | 메타 생성 | full | skip | full |
| 4 | 플랫폼 노트 | full | compact | full |
| 5 | Notion publish | full | full | full |

Phase 3은 항상 `full` 로 실행되며, `checklist.yaml` 의 `applies_to_work_type` 필드가 자동으로 카테고리를 필터한다. `3_bug` 같은 이중 식별자는 사용하지 않는다.

---

## 4. 체크리스트 확장

`config/pdf-spec-organizer/checklist.yaml` 을 `common/config/checklist.yaml` 로 이동하고 `applies_to_work_type` 필드를 추가한다.

```yaml
categories:
  - id: error_handling
    applies_to_work_type: [new_feature, bug_fix, enhancement]
  - id: empty_state
    applies_to_work_type: [new_feature, enhancement]
  - id: offline
    applies_to_work_type: [new_feature, bug_fix, enhancement]
  - id: permission
    applies_to_work_type: [new_feature, enhancement]
  - id: loading
    applies_to_work_type: [new_feature, enhancement]
  - id: a11y
    applies_to_work_type: [new_feature, bug_fix, enhancement]
  - id: regression_scope
    applies_to_work_type: [bug_fix]
    description: "수정이 다른 피처에 영향 주지 않는지"
  - id: reproduction_conditions
    applies_to_work_type: [bug_fix]
    description: "재현에 필요한 환경/조건 명시"
```

버그 픽스 Phase 3 은 6개 중 3개 공통 + 2개 전용 = 5개만 체크한다.

---

## 5. work_type 스키마 주도 수집

### 5.1 파일 구성

- `common/config/work-type-schemas/new_feature.yaml` (검증용)
- `common/config/work-type-schemas/bug_fix.yaml`
- `common/config/work-type-schemas/enhancement.yaml`

### 5.2 `source` 속성 의미

| 값 | 의미 |
|----|------|
| `auto_or_ask` | PDF/텍스트 추출 시도 → 실패 시 질문 |
| `ask` | 항상 개발자에게 질문 |
| `ask_with_notion_lookup` | Notion DB 키워드 검색 → 상위 3-5개 제시 |
| `phase_3_5_auto` | Phase 3.5 메타 생성 결과 사용 |
| `phase_1_2_auto` | PDF 파싱 결과 사용 |

### 5.3 `bug_fix.yaml` 예시

```yaml
version: 1
work_type: bug_fix
notion_page_template: bug_template

required:
  - { id: title, source: auto_or_ask, validator: non_empty }
  - { id: symptom, source: auto_or_ask, validator: non_empty, hint: "재현 스텝" }
  - { id: root_cause, source: ask, validator: non_empty }
  - { id: fix_plan, source: ask, validator: non_empty }
  - { id: affected_platforms, source: auto_or_ask, validator: enum_multi, choices: [iOS, Android, 공통] }
  - { id: related_feature_id, source: ask_with_notion_lookup, validator: exists_in_feature_db }

optional:
  - { id: estimated_duration, source: phase_3_5_auto, validator: duration_string }
  - { id: priority, source: ask, validator: enum, choices: [Critical, High, Medium, Low], default: Medium }
  - { id: reproduction_env, source: auto_or_ask, hint: "OS 버전, 기기, 네트워크" }
```

### 5.4 `enhancement.yaml`

```yaml
version: 1
work_type: enhancement
notion_page_template: enhancement_template

required:
  - { id: title, source: auto_or_ask, validator: non_empty }
  - { id: related_feature_id, source: ask_with_notion_lookup, validator: exists_in_feature_db }
  - { id: target_platforms, source: auto_or_ask, validator: enum_multi, choices: [iOS, Android, 공통] }
  - { id: change_description, source: auto_or_ask, validator: non_empty }

optional:
  - { id: reason, source: auto_or_ask }
  - { id: estimated_duration, source: phase_3_5_auto }
  - { id: dependencies, source: phase_3_5_auto }
  - { id: missing_items, source: phase_3_5_auto }
```

### 5.5 질문 방식

- `source: ask` 필드는 **1문장씩 대화형** (개발자 맥락 유지)
- Notion 피처 DB 조회는 **키워드 검색 → 상위 3-5개 매칭** 후 번호 선택
- 스키마가 결정하므로 Claude 의 주관적 "이거 부족한가?" 판단은 발생하지 않음

---

## 6. brainstorming 핸드오프

### 6.1 호출 방식

`pdf_count=0 + has_text_or_link + work_type=new_feature` 케이스에서 `spec-organizer` 가 Skill tool 로 `superpowers:brainstorming` 을 호출한다 (v1 옵션 1: Skill tool 연쇄).

### 6.2 계약

```yaml
handoff_contract:
  input:
    free_text: str
    urls: list[str]
    initial_hint: "새 기능 스펙화 목적"
  expected_return:
    work_type: str            # enhancement 로 승격 가능
    text_summary: str
    requirements: list[str]
    design_doc_path: str      # docs/superpowers/specs/*.md
  reentry_route: text_or_link_enh
```

### 6.3 귀환 후 처리

1. `text_summary` 를 새 `free_text` 로 간주
2. 반환된 `work_type` 으로 매트릭스 재평가 (일반적으로 `text_or_link_enh` 로 진입)
3. `design_doc_path` 를 Notion 페이지의 `source_design_doc` optional 필드에 저장

### 6.4 실패 처리

brainstorming 스킬이 비정상 종료하거나 `expected_return` 스키마와 다른 결과를 반환하면:

```yaml
failure_fallback:
  action: prompt
  message: "Brainstorming 결과를 받지 못했습니다."
  choices:
    - retry: "brainstorming 재시도"
    - manual: "수동으로 요구사항 입력 (enhancement 경로)"
    - cancel: "취소"
```

---

## 7. resume / update 모드

### 7.1 resume 모드

```
감지 신호:
  - 인자가 .md 파일 경로 (draft)
  - 자연어: "이전 작업", "이어서", "복구"
  - --resume-latest 플래그

흐름:
  1. draft 경로 유효성 확인
  2. draft 헤더에서 work_type 추출
     - 있음: 해당 전담 스킬에 resume 컨텍스트 전달
     - 없음 (레거시): "어떤 작업이었나요?" 질문 → 사용자 선택
  3. 해당 스킬이 중단 지점부터 재개
```

### 7.2 update 모드

```
감지 신호:
  - 인자가 Notion URL (notion.so/...)
  - 자연어: "노트 수정", "업데이트", "페이지 고쳐"

흐름:
  1. URL 에서 page_id 추출
  2. 페이지 메타 조회 → work_type property 읽기
     - 있음: 해당 스킬의 update 모드로 위임
     - 없음 (레거시): 사용자 선택
  3. 수정 범위 확인:
     - 전체 재생성 (full overwrite)
     - 노트 섹션만 (iOS/Android)
     - 특정 필드만
```

### 7.3 `note_extractor.py` 리팩터

```python
def extract_notes(page_content: str, schema: str) -> dict:
    extractors = {
        "new_feature": extract_feature_notes,          # 기존 sentinel 로직
        "bug_fix": extract_bug_sections,               # 신규
        "enhancement": extract_enhancement_sections,    # 신규
    }
    return extractors[schema](page_content)
```

`--schema` CLI 플래그로 명시적 선택.

### 7.4 제약

- work_type 변경 (버그 → 새 기능 승격) 은 **v1에서 금지**. 새 페이지 생성 필요. v2 에서 `/spec-promote` 검토.

---

## 8. Notion DB 마이그레이션

### 8.1 Lazy 전략 (v1)

- 첫 실행 시 Notion DB 스키마 조회 → `work_type` Select property 존재 확인
- 없으면: "추가할까요?" 프롬프트 → 승인 시 **DB 스키마에 property 만 추가** (기존 페이지는 건드리지 않음)
- 이후 매 작업에서 생성/수정되는 페이지만 `work_type` 값 저장 (touch-on-write)

### 8.2 v1.5 에서 제공

```
/spec-migrate-work-type
  - 3req/s rate limiter
  - 진행 상황 checkpoint (registry.json)
  - 중단 후 재개 가능
  - 기본값은 new_feature (사용자가 --default 로 변경 가능)
```

---

## 9. 에러 처리 개선 (한계 분석 반영)

### 9.1 Phase 3.5 JSON 파싱 실패

기존 silent `EMPTY_METADATA` 반환을 **Pydantic 스키마 검증 + stderr 명시 경고**로 교체.

```python
class Phase35Response(BaseModel):
    estimated_duration: str
    dependencies: list[str]
    missing_items: list[str]

def parse_claude_meta_response(raw: str) -> Phase35Response | None:
    try:
        return Phase35Response(**json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as e:
        sys.stderr.write(
            f"⚠️  [Phase 3.5] 메타 생성 실패 ({e.__class__.__name__})\n"
            f"   → 예상시간/의존성 필드가 비어있는 상태로 진행합니다.\n"
            f"   → Notion 페이지에서 수동 입력하거나 `/spec-update`로 재생성 가능합니다.\n"
        )
        return None
```

### 9.2 Notion API 재시도

```python
def with_retry(fn, max_attempts=3, base_delay=2.0):
    for attempt in range(max_attempts):
        try:
            return fn()
        except (NotionRateLimitError, NotionServerError):
            if attempt == max_attempts - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))  # 2s → 4s → 8s
```

`page_publisher.py` 는 chunk append 사이에 **체크포인트 파일** (`.spec-organizer/checkpoints/{page_id}.json`) 저장 → 중간 실패 시 `/spec-resume` 가 체크포인트부터 재개.

### 9.3 OCR 미설치 차단

기존 silent skip 을 **에러 차단 + 3가지 해결책**으로 교체.

```python
if not shutil.which("tesseract"):
    raise SkillError(
        "이 PDF는 이미지 전용이라 OCR이 필요합니다.\n"
        "해결 방법:\n"
        "  1) macOS: brew install tesseract tesseract-lang\n"
        "  2) PDF를 텍스트 선택 가능한 형태로 재생성\n"
        "  3) 자유 서술로 입력: '이 PDF 대신 설명으로 스펙 만들어줘'"
    )
```

---

## 10. 테스트 전략

### 10.1 단위 테스트

| 파일 | 대상 |
|------|------|
| `common/scripts/tests/test_dispatcher.py` | routing 결정 |
| `common/scripts/tests/test_work_type_normalizer.py` | alias 매핑 |
| `common/scripts/tests/test_field_collector.py` | 스키마 주도 수집 |
| `common/scripts/tests/test_notion_client_retry.py` | exponential backoff |
| `common/scripts/tests/test_phase35_parser.py` | Pydantic 검증 |
| `skills/bug-spec-organizer/scripts/tests/test_bug_input_collector.py` | 신규 |
| `skills/enhancement-spec-organizer/scripts/tests/test_enhancement_input_collector.py` | 신규 |
| 기존 13개 테스트 | 회귀 방지 (import path 수정) |

### 10.2 라우팅 회귀 테스트

`evals/routing-matrix.json` 에 24셀 전수 케이스 + 기대 route ID.

```json
{
  "version": 1,
  "cases": [
    { "id": "c01_pdf_single_new_explicit", "input": {...}, "expected": { "route_id": "pdf_single_new", ... } },
    ...
  ]
}
```

### 10.3 E2E 테스트

`evals/e2e/` 에 4개 시나리오 (버그 픽스 최소 입력, 기능 강화+URL, PDF 새 기능 회귀, resume 재개). Notion API 는 `pytest-vcr` fixtures 로 기록.

### 10.4 Trigger Eval

각 스킬별 20 케이스 × 3 스킬 = 60 케이스. 목표 정확도 ≥95%.

- `evals/trigger-eval.json` (spec-organizer)
- `evals/trigger-eval-bug.json`
- `evals/trigger-eval-enhancement.json`

---

## 11. 구현 순서 (8 PR)

| PR | 내용 | 예상 소요 |
|----|------|----------|
| 1 | 공통 코어 추출 (common/ 생성, 9개 스크립트 이동, import path 수정) | **2일** |
| 2 | routing.yaml + dispatcher.py + 24셀 회귀 테스트 | **3일** |
| 3 | work-type-schemas + field_collector (Notion 검색 포함) | **3일** |
| 4 | spec-organizer wrapper 스킬 + Skill tool 연쇄 | **2일** |
| 5 | bug-spec-organizer 스킬 + 템플릿 + E2E | **3일** |
| 6 | enhancement-spec-organizer 스킬 + 템플릿 + E2E | **3일** |
| 7 | checklist.yaml 이동 + applies_to_work_type + Phase 3 리팩터 | **1일** |
| 8 | 에러 처리 (Pydantic / backoff / OCR 차단) + deprecation 경고 주입 | **2일** |

**총 예상: 19 영업일 (≈ 4주)**

PR 4 이후 PR 5, 6, 7은 병렬 가능.

---

## 12. Deprecation 계획

### 12.1 v1.0.0 (이번 릴리스)

기존 커맨드는 유지하되, 실행 시 로그에 경고 남기고 즉시 위임:

```
$ /spec-from-pdf path.pdf
[DEPRECATED] /spec-from-pdf 는 v1.5에서 제거됩니다. 자연어로 호출해주세요.
(spec-organizer 에 위임 중...)
```

### 12.2 v1.5

- 기존 3개 커맨드 완전 제거
- `/spec-migrate-work-type` 배치 커맨드 제공
- `common/` 파일 핸드오프 리팩터 (옵션 2)

### 12.3 v2

- 외부 링크 파싱, PII 확장, 다국어, `/spec-promote`

---

## 13. 성공 기준 (v1 완료 정의)

- [ ] 기존 13개 단위 테스트 통과 (회귀 없음)
- [ ] 신규 단위 테스트 15+ 통과
- [ ] `evals/routing-matrix.json` 24/24 통과
- [ ] 각 스킬 trigger-eval 95%+ 정확도
- [ ] 4개 E2E 시나리오 통과
- [ ] `yeoboya-workflow.config.json` 변경 없이 기존 사용자 동작 확인
- [ ] README.md 업데이트 (wrapper 스킬 사용법, deprecation 안내)
- [ ] CHANGELOG.md 에 v1.0.0 마이그레이션 가이드

---

## 14. 위험 및 완화

| 위험 | 영향 | 완화 |
|------|------|------|
| `common/` path hack 이 다른 플러그인과 충돌 | 테스트 격리 실패 | pytest fixture 로 sys.path 복원, v1.5 pip 패키지 전환 |
| brainstorming Skill tool 연쇄 호출이 Claude Code 네이티브 미지원 | v1 핵심 UX 불가 | 검증 PoC 먼저 수행 (PR 4 초입), 실패 시 파일 핸드오프로 즉시 전환 |
| Notion API 스키마 자동 감지 실패 | 마이그레이션 차단 | 스키마 조회 타임아웃 5초, 실패 시 수동 추가 안내 |
| 24셀 중 실제 발생 빈도 낮은 케이스 과잉 구현 | 개발 비용 | 사용 통계(`registry.json`) 기반 v1.5 에서 정리 |

---

## 15. 관련 문서

- 이전 설계: `docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md`
- 한계 분석: (대화 내 분석, 별도 문서화 예정)
- README: `README.md` (v1 업데이트 필요)
