---
name: conversation-spec-organizer
description: PDF 없이 사용자 대화만으로 스펙을 작성해 Notion 피처 DB 페이지로 정리한다. `superpowers:brainstorming` 으로 요구사항을 수집하고, 작업 유형(feature/bug/enhancement)에 맞춰 스펙을 구조화한 뒤 Notion 에 퍼블리시한다. 슬래시 커맨드 `/work --no-pdf` 의 실제 구현 로직.
allowed-tools: Bash Read Write Edit Grep Glob mcp__claude_ai_Notion__notion-search mcp__claude_ai_Notion__notion-fetch mcp__claude_ai_Notion__notion-create-pages mcp__claude_ai_Notion__notion-update-page
---

# conversation-spec-organizer

PDF 없이 **사용자 대화 → Superpowers 체인 → Notion 퍼블리시** 로 이어지는 얇은 3-Phase 워크플로우.

## Precondition 체크 (Skill 시작 시 항상 먼저)

### 1. 인자 확인

**왜:** 이후 Phase 가 읽을 값이 없으면 조기 중단해야 혼란이 없음.

필수 환경변수:
- `WORK_TYPE` ∈ {`feature`, `bug`, `enhancement`}
- `MODE="no-pdf"` (작성 진입 확인)

값이 없거나 범위를 벗어나면 중단:
```
❌ WORK_TYPE 이 지정되지 않았습니다. /work 로 재진입하세요.
```

### 2. 팀 공유 설정 확인

**왜:** Notion 퍼블리시 대상 DB 를 `yeoboya-workflow.config.json` 에서 읽어야 팀원이 같은 DB 를 바라봄. `pdf-spec-organizer` 와 동일한 규칙.

- 레포 루트에서 `yeoboya-workflow.config.json` 탐색
- 없으면:
  ```
  ❌ 팀 공유 설정 파일이 없습니다: yeoboya-workflow.config.json
     팀 리드가 먼저 셋업을 완료해야 합니다. README.md 의 "팀 리드 최초 셋업" 섹션 참고.
  ```
- 있으면 `pdf_spec_organizer.notion_database_id` / `notion_data_source_id` / `parent_page_id` 재사용

### 3. Superpowers 플러그인 확인 (경고만)

**왜:** 이 스킬은 `superpowers:brainstorming` 호출을 가정. 없어도 수동 모드로 동작 가능하지만 품질이 낮아짐.

- `~/.claude/plugins` 또는 settings 에 `superpowers` 등록 확인 (best-effort)
- 없으면 경고 후 계속:
  ```
  ⚠️  superpowers 플러그인이 감지되지 않았습니다.
     수동 대화 모드로 진행합니다. 설치 권장: /plugin (superpowers 등록)
  ```

---

## Phase 1 — 요구사항 대화 수집

**왜:** PDF 라는 명문화된 입력이 없으므로 사용자 머릿속을 구조화해서 끌어내는 게 핵심. Superpowers 의 `brainstorming` 스킬이 "한 번에 한 질문씩 / 2-3 approach 비교 / 승인 후 design doc 저장" 패턴을 강제하므로 이걸 그대로 사용.

### 1-1. 작업 폴더 생성

```bash
TS=$(date +%s)
WORK_DIR="/tmp/spec-conv-${WORK_TYPE}-${TS}"
mkdir -p "$WORK_DIR"
DRAFT_PATH="${WORK_DIR}/draft.md"
SPEC_DOC="${WORK_DIR}/spec.md"  # brainstorming 산출물 저장 위치
```

### 1-2. 작업 유형별 초기 질문 세트 준비

**왜:** 유형별로 관심사가 다름. bug 는 재현·근본원인, feature 는 AC·플로우, enhancement 는 현재 vs 변경.

| WORK_TYPE | 핵심 질문 축 |
|---|---|
| `feature` | 목적 / 사용자 플로우 / Acceptance Criteria / 엣지케이스 / 타팀 의존성 |
| `bug` | 재현 스텝 / 기대 vs 실제 / 영향 범위 / 근본 원인 가설 / 회귀 방지 |
| `enhancement` | 현재 동작 / 변경 목표 / 기존 사용자 영향 / 마이그레이션 / 롤백 조건 |

위 축을 `brainstorming` 스킬 호출 시 컨텍스트로 전달.

### 1-3. brainstorming 스킬 호출

```
Skill: superpowers:brainstorming
args:
  topic: "<WORK_TYPE> 스펙 작성"
  context: |
    작업 유형: <WORK_TYPE>
    타겟 플랫폼: iOS / Android (필요 시 사용자에게 확인)
    결과물: Notion 피처 DB 페이지로 퍼블리시할 스펙 문서
    커버해야 할 축: <위 표의 해당 유형 축 나열>
  output_path: "${SPEC_DOC}"
```

스킬이 한 번에 한 질문씩 진행하며 설계를 확정한 뒤 `${SPEC_DOC}` 에 design doc 을 저장.

### 1-4. 스펙 문서 최소 요건 검증

**왜:** brainstorming 이 자유 형식이라 Phase 2 변환이 실패할 수 있음. 필수 섹션을 조기 검증.

`${SPEC_DOC}` 에 아래 헤더가 모두 있는지 grep:
- `## 개요` 또는 `## Overview`
- `## Acceptance Criteria` (feature) / `## 재현 스텝` (bug) / `## 변경 사항` (enhancement)
- `## 엣지케이스` 또는 `## Known Risks`

빠진 섹션이 있으면 사용자에게 확인 후 brainstorming 재호출 또는 수동 보강.

---

## Phase 2 — 스펙 구조화 (Notion 블록 초안)

**왜:** brainstorming 산출물은 설계 에세이 형태. Notion 피처 DB 는 title / properties / Toggle 구조를 기대하므로 변환 필요. 기존 `pdf-spec-organizer` 의 draft.md 스키마를 그대로 따라 Phase 5 퍼블리시 로직을 재사용.

### 2-1. draft.md 스켈레톤 생성

```markdown
<!-- plugin-state
phase: 2
source: conversation
work_type: <feature|bug|enhancement>
created_at: <epoch>
publish_state: idle
page_id:
last_block_sentinel_id:
-->

# <스펙 제목 — 사용자에게 확인>

## 개요
<spec.md 의 개요 섹션 옮김>

## Acceptance Criteria / 재현 스텝 / 변경 사항
<WORK_TYPE 에 따라>

## 엣지케이스
<spec.md 의 risks/edge cases>

## 개발자 노트

<!-- section: ios -->
(iOS 개발자가 `/spec-update` 로 추가)
<!-- /section: ios -->

<!-- section: android -->
(Android 개발자가 `/spec-update` 로 추가)
<!-- /section: android -->

<!-- section: common -->
(공통 노트)
<!-- /section: common -->
```

### 2-2. 제목 확인

사용자에게 스펙 제목을 확인 (brainstorming 에서 도출된 제안 + 수정 기회):
```
제목: "<제안된 제목>"
이대로 진행할까요? (y/수정 내용/n=취소)
```

### 2-3. 초안 미리보기

draft.md 를 사용자에게 출력하고 최종 확인:
```
아래 스펙을 Notion 에 퍼블리시합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━
<draft.md 내용>
━━━━━━━━━━━━━━━━━━━━━━━━━

퍼블리시 (y) / 수정 (e) / 취소 (n):
```

`e` 선택 시 에디터(`$EDITOR`) 로 draft.md 열기, 저장 후 다시 확인.

---

## Phase 3 — Notion 퍼블리시

**왜:** 기존 `pdf-spec-organizer` Phase 5 와 동일한 경로 — `page_publisher.py` + `notion-create-pages` + chunked append. 중복 코드를 쓸 이유가 없음.

### 3-1. Dedup 조회 (옵션)

제목 기준으로 같은 페이지가 이미 있는지 검색:
```
mcp__claude_ai_Notion__notion-search
  data_source_url: collection://<data_source_id>
  query: "<스펙 제목>"
```

있으면 사용자에게:
- `a`: 기존 페이지에 노트 append (→ `/spec-update` 로 위임)
- `n`: 새 페이지로 생성 (이름에 타임스탬프 suffix)
- `c`: 취소

### 3-2. 새 페이지 생성 + chunked publish

```bash
# shell 페이지 생성
# mcp__claude_ai_Notion__notion-create-pages
#   parent: data source (DB)
#   properties: { title, work_type, created_by, source=conversation }
#   → page_id 획득

# draft.md chunking
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/scripts/page_publisher.py" chunk \
  --input "${DRAFT_PATH}" --max-blocks 80 > "${WORK_DIR}/chunks.json"

# publish_state=page_created 로 기록
python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/scripts/draft_registry.py" update-status \
  --draft-path "${DRAFT_PATH}" \
  --status running \
  --page-id "${PAGE_ID}" \
  --publish-state page_created

# chunk 순차 append (rate-limit 시 exponential backoff)
# 각 chunk 성공 → publish.log 기록 + sentinel append
```

### 3-3. 완료 보고

```
✅ 스펙이 Notion 에 퍼블리시되었습니다.

   페이지: <notion-url>
   작업 유형: <WORK_TYPE>
   출처: 대화 기반 (PDF 없음)

   다음 단계:
     · iOS/Android 노트 추가: /spec-update <url>
     · 구현 플랜 작성: superpowers:writing-plans (선택)
```

---

## 실패 / 재개 전략

- Phase 1 도중 중단: `${SPEC_DOC}` 가 남아있으면 `/work --no-pdf --resume` 로 재개 (TODO: 다음 이터레이션)
- Phase 3 chunked publish 도중 실패: 기존 `/spec-resume` 로 이어받기 가능 (publish_state / last_block_sentinel_id 동일 포맷 사용)

---

## 기존 pdf-spec-organizer 와의 관계

| 항목 | pdf-spec-organizer | conversation-spec-organizer |
|---|---|---|
| 입력 | PDF 파일 | 사용자 대화 |
| Phase 1 | PDF 파싱·OCR·PII | **brainstorming 스킬** |
| Phase 2 | 피처 N개 구조화 | 단일 스펙 구조화 (1 피처 = 1 페이지) |
| Phase 3 | 누락 체크 | (생략 — brainstorming 이 커버) |
| Phase 3.5 | 메타 정보 제안 | (생략 — 수동) |
| Phase 4 | 플랫폼 노트 작성 | (Phase 2 draft 에 빈 섹션 포함) |
| Phase 5 | Notion 퍼블리시 | **동일 로직 재사용** (page_publisher.py) |

## 현재 구현 상태 (v0.5-dev)

- [x] Phase 설계 (이 문서)
- [ ] Phase 1 wiring (brainstorming 스킬 호출)
- [ ] Phase 2 draft.md 스켈레톤 생성기
- [ ] Phase 3 퍼블리시 (page_publisher 재사용)
- [ ] `/work --no-pdf` 에서 dispatch
- [ ] pytest 테스트

> 이 스킬은 `/work` 가 "PDF 없음" 분기를 탈 때 호출된다. Phase 1-3 의 실제 호출 순서·환경변수는 `commands/work.md` 참조.
