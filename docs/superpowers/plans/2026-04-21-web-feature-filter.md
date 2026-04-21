# Web Feature Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pdf-spec-organizer` 에 웹 전용 피처 필터링을 추가한다. Phase 2 끝에 "웹 전용 피처 번호 입력" 단계를 배치하고, 제외된 피처는 Phase 3/4/5 에서 완전 스킵한다.

**Architecture:** 순수 markdown 변경 (Python 코드 변경 없음). `features.json` 의 각 피처에 `excluded: bool` 플래그 추가. SKILL.md 의 Phase 2 에 제외 단계(`2-6`) 삽입 + Phase 3/4/5 에 `excluded == false` 필터링 지시 반영 + Resume 모드에 `excluded_ids` 직렬화 추가. `references/review-format.md` 에 새 UI 포맷 규약 추가.

**Tech Stack:** Markdown 편집, Bash 검증, (Python 스크립트 변경 없음).

**Spec reference:** `docs/superpowers/specs/2026-04-21-web-feature-filter-design.md`

---

## File Structure Overview

| 경로 | 유형 | 이번 플랜에서 |
|---|---|---|
| `skills/pdf-spec-organizer/references/review-format.md` | 수정 | Claude 힌트 표기 규약 + 웹 제외 프롬프트 포맷 추가 |
| `skills/pdf-spec-organizer/SKILL.md` | 수정 | Phase 2-6 신설, Phase 3/4/5 에 excluded 필터링, Resume 모드에 excluded_ids 직렬화 |
| `CHANGELOG.md` | 수정 | `[Unreleased]` 섹션에 v0.3.0 엔트리 |

> Python 스크립트는 변경 없음. `features.json` 의 `excluded` 플래그는 LLM 이 직접 JSON 쓰기로 관리.

---

## Commit 1: UI 포맷 + Phase 2 제외 단계

### Task 1: `review-format.md` — 피처 리스트 출력 포맷에 Claude 힌트 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md`

- [ ] **Step 1: 현재 "터미널 출력 규약" 섹션 확인**

Run:
```bash
grep -n "^## 터미널 출력 규약\|^## Phase 별" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md
```

Expected: "## 터미널 출력 규약" 과 "## Phase 별 터미널 프롬프트 예시" 두 라인 번호. 사이 영역이 수정 대상.

- [ ] **Step 2: Read 로 해당 섹션 읽기**

Read 도구 사용:
- `file_path`: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md`
- `offset`: Step 1 에서 얻은 "터미널 출력 규약" 줄 번호
- `limit`: 두 헤더 사이 줄 수

이 내용을 Step 3 Edit 의 old_string 으로 그대로 사용.

- [ ] **Step 3: 피처 목록 출력 블록 교체**

Edit 도구로 기존 피처 목록 예시 블록(`피처 3개 추출됨:` 부터 `> ` 프롬프트까지) 을 아래로 교체. **Step 2 Read 결과에서 해당 블록 전체**를 `old_string` 으로, 아래를 `new_string` 으로.

새 블록 (`new_string`):

```markdown
피처 5개 추출됨:
  1. 알림 설정 화면 (iOS, Android)
  2. 랭킹 리더보드 웹뷰 (공통)              💡 Claude: "웹 같음"
  3. 프로필 편집 (iOS, Android, 공통)       💡 Claude: "혼합 — s 3 으로 분리 권장"
  4. 로그인 플로우 (iOS, Android)
  5. PC 관리자 대시보드 (공통)              💡 Claude: "웹 같음 (PC)"

범례: iOS/Android 공통 = iOS+Android 둘 다 (웹 포함 아님)

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

변경점:
- 피처 5개로 예시 확장 (웹/네이티브 혼재 케이스 제시)
- 각 피처 우측에 `💡 Claude: "..."` 힌트 컬럼 예시 (모든 피처에 있는 것은 아님 — Claude 판단 시에만)
- 범례 줄 추가 (`iOS/Android 공통` 용어 정의)

- [ ] **Step 4: 검증**

Run:
```bash
grep -c "💡 Claude:" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md
```
Expected: **3** (예시 3줄)

Run:
```bash
grep "iOS/Android 공통 = iOS+Android 둘 다" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md
```
Expected: 1 라인 출력.

---

### Task 2: `review-format.md` — 웹 제외 프롬프트 포맷 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md`

- [ ] **Step 1: "Phase 별 터미널 프롬프트 예시" 섹션의 Phase 2 부분 위치 확인**

Run:
```bash
grep -n "Phase 2 완료 후\|Phase 3 완료 후" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md
```
Expected: 두 라인. "Phase 2 완료 후" 다음 "Phase 3 완료 후" 전 영역에 새 내용 삽입.

- [ ] **Step 2: Phase 2 섹션 아래에 웹 제외 프롬프트 블록 추가**

Edit 도구로 `Phase 2 완료 후: 위 메뉴` 라인 다음에 새 섹션 삽입.

`old_string`:
```
Phase 2 완료 후: 위 메뉴
Phase 3 완료 후:
```

`new_string`:
```
Phase 2 완료 후: 위 메뉴

### 웹 전용 피처 제외 프롬프트 (Phase 2-6)

구조화 승인(`y`) 직후 아래 프롬프트 표시:

```
웹 전용 피처 번호 입력 (네이티브 개발팀 작업 대상 아님):
  쉼표: 2, 5
  범위: 2-5
  전체 제외: all
  없음: none (또는 Enter)

※ 일부만 웹인 피처는 먼저 `s N` 으로 분리한 뒤 이 단계에서 제외하세요.
> _
```

입력 처리:
- 쉼표 리스트 (`2, 5` 또는 `2,5`): 공백 허용
- 범위 (`2-5`): 포함 양끝 (inclusive)
- `all`: "모든 피처 제외합니다. Phase 3 이후 스킵되며 Notion 에 아무것도 생성되지 않습니다. 확실합니까? (y/N)" 이중 확인
- `none` 또는 Enter: 아무것도 제외 안 함

유효성 오류:
- 범위 밖 숫자 → "N 은 존재하지 않습니다. 1-<max> 사이 숫자 필요" + 재입력
- 형식 오류 → "형식 오류. 쉼표/범위/all/none 중 선택" + 재입력

결과: `features.json` 의 해당 피처에 `excluded: true` 플래그 설정.

Phase 3 완료 후:
```

> **펜스 충돌 주의:** new_string 안에 마크다운 코드 블록(` ``` `)이 포함돼 있다. 바깥 Edit 호출 시 이 백틱이 손상되지 않도록 그대로 전달.

- [ ] **Step 3: 검증**

Run:
```bash
grep -c "^### 웹 전용 피처 제외 프롬프트" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md
```
Expected: **1**

Run:
```bash
grep "excluded: true" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md
```
Expected: 1 라인 (결과 설명 문장).

---

### Task 3: `SKILL.md` — Phase 2 에 `2-6` 서브섹션 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Phase 2 의 마지막 서브섹션 위치 확인**

Run:
```bash
grep -n "^## Phase 2\|^## Phase 3\|^### 2-[0-9]" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected 라인 (예시):
```
150:## Phase 2 — 구조화 + 개입 ①
164:### 2-1. Claude 에게 피처 추출 지시
...
233:### 2-5. feature_id 확정
249:## Phase 3 — 누락 체크
```

Phase 2 는 현재 2-5 까지. 우리는 **2-6** 으로 새 서브섹션을 2-5 와 "## Phase 3" 사이에 삽입.

- [ ] **Step 2: 2-6 서브섹션을 Phase 3 바로 앞에 삽입**

Edit 도구:
- `old_string`: 2-5 섹션의 마지막 줄들부터 `## Phase 3 — 누락 체크` 헤더까지 고유하게 포함된 영역. 예: `"Phase 5 퍼블리시 시 각 Toggle 상단에 \`<!-- feature_id: <uuid> -->\` 주석으로 고정된다.\n\n## Phase 3 — 누락 체크"`

  실제 Phase 2-5 마지막 문장을 Read 로 확인 후 사용.

- `new_string`: 위 old_string 과 동일하되 `## Phase 3` 직전에 아래 `### 2-6` 블록 삽입.

2-6 서브섹션 내용 (삽입할 블록):

```markdown
### 2-6. 웹 전용 피처 제외

**왜:** 기획서에 웹 기능과 네이티브 기능이 혼재하는 경우, 네이티브 개발팀은 웹 피처를 Notion 에 정리할 필요 없음. Phase 2-5 까지 완료된 피처 목록에서 웹 전용을 한 번에 걸러냄.

#### 2-6-a. Claude 힌트 부여

Phase 2-1 에서 이미 추출된 각 피처의 `name` / `summary` / `requirements` 를 다시 훑어 짧은 힌트 문자열을 생성:

- "웹 같음" — PDF 에 "웹 페이지", "웹 서비스", "브라우저", "URL" 등 명시
- "웹 같음 (PC)" — "PC", "데스크톱" 같은 문구
- "혼합 — s N 으로 분리 권장" — 한 피처에 웹 부분과 네이티브 부분이 섞여 있을 때
- 아무 힌트 없음 — 네이티브로 판단되는 피처

**부정 패턴 예외**: `웹뷰`, `웹소켓`, `웹훅`, `웹 표준`, `WebSocket`, `WebView` 등은 네이티브 문맥에서도 자주 등장. 이들만 보고 "웹" 으로 속단하지 말 것. 문맥 (주변 문장) 에서 "이 피처는 웹에서 제공" 류 명시가 있어야 "웹 같음" 태깅.

힌트는 `features.json` 에 저장하지 **않고**, 이 단계에서 UI 출력용으로만 사용.

#### 2-6-b. 구조화 결과 재표시 (힌트 포함)

`references/review-format.md` 의 피처 목록 출력 포맷을 따라 피처별 힌트와 함께 출력. 범례 포함.

**참고:** 2-2 에서 이미 피처 목록을 한 번 보여주며 y/s/m/r/t/e/c 메뉴를 제공했다. 2-2 ↔ 2-5 루프가 끝난 후 **이 2-6 에서 한 번 더 표시** 하는 이유는: (a) 최종 확정된 피처로 힌트 재생성, (b) 웹 제외 프롬프트 직전에 사용자가 전체 목록을 다시 볼 기회 제공.

#### 2-6-c. 웹 제외 프롬프트

`references/review-format.md` 의 "웹 전용 피처 제외 프롬프트 (Phase 2-6)" 섹션에 정의된 포맷대로 출력:

```
웹 전용 피처 번호 입력 (네이티브 개발팀 작업 대상 아님):
  쉼표: 2, 5
  범위: 2-5
  전체 제외: all
  없음: none (또는 Enter)

※ 일부만 웹인 피처는 먼저 `s N` 으로 분리한 뒤 이 단계에서 제외하세요.
> _
```

#### 2-6-d. 입력 처리

사용자 입력을 아래 순서로 파싱:

1. 공백 제거 후 `none` 또는 빈 문자열 → 제외 없음, 다음 단계로 진행
2. `all` → 이중 확인 프롬프트:
   ```
   모든 피처 제외합니다. Phase 3 이후 스킵되며 Notion 에 아무것도 생성되지 않습니다. 확실합니까? (y/N)
   ```
   - `y` → 모든 피처에 `excluded: true` 설정, 다음 단계
   - 그 외 → 2-6-c 프롬프트로 재진입
3. 쉼표 리스트 또는 범위 문법 (`2, 5`, `2-5`, `2,5-7,10`):
   - `1` ~ `N` (N = 현재 피처 개수) 범위 내 숫자만 허용
   - 범위 밖 숫자 발견 → `"N 은 존재하지 않습니다. 1-<max> 사이 숫자 필요"` + 2-6-c 프롬프트 재진입
   - 모두 유효하면 해당 피처들에 `excluded: true` 설정
4. 그 외 형식 → `"형식 오류. 쉼표/범위/all/none 중 선택"` + 2-6-c 프롬프트 재진입

#### 2-6-e. 결과 저장

`${WORK_DIR}/features.json` 업데이트. 각 피처 객체에 `excluded` 필드 추가 (기본 `false`, 제외된 피처는 `true`).

예:
```json
{
  "features": [
    {"feature_id": "...", "name": "알림 설정", "excluded": false, ...},
    {"feature_id": "...", "name": "랭킹 리더보드", "excluded": true, ...}
  ]
}
```

#### 2-6-f. 전체 제외 엣지 케이스

모든 피처가 excluded (all 선택 후 y 확인) 인 경우:
```
⚠️  모든 피처가 제외되었습니다. 퍼블리시할 피처가 없으므로 종료합니다.
  초안 경로: <draft_path> (TTL 7일 후 자동 삭제)
```
실패 아니라 정상 종료. `draft_registry update-status --status success` 로 기록 후 exit 0.
```

- [ ] **Step 3: 검증**

Run:
```bash
grep -n "^### 2-6\|^## Phase 3" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: `### 2-6` 이 `## Phase 3` 앞에 존재.

Run:
```bash
grep -c "^#### 2-6-" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: **6** (2-6-a 부터 2-6-f 까지 6개 하위 섹션)

---

### Task 4: Commit 1

- [ ] **Step 1: 변경 파일 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && git status --short
```
Expected:
```
 M skills/pdf-spec-organizer/SKILL.md
 M skills/pdf-spec-organizer/references/review-format.md
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/pdf-spec-organizer/SKILL.md skills/pdf-spec-organizer/references/review-format.md && \
git commit -m "feat(skill): add Phase 2-6 web feature exclusion step with UI format"
```

Expected: 커밋 성공 + SHA 출력.

---

## Commit 2: Phase 3/4/5 필터링 + Resume 모드

### Task 5: `SKILL.md` Phase 3 에 excluded 필터링 반영

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md` (Phase 3 섹션)

- [ ] **Step 1: Phase 3 의 피처 루프 위치 확인**

Run:
```bash
grep -n "^## Phase 3\|^### 3-2\|^### 3-3" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: Phase 3 헤더 + 서브섹션 3-1, 3-2, 3-3 줄 번호.

- [ ] **Step 2: Phase 3 피처 루프 시작부에 필터링 문구 추가**

Phase 3-2 "피처별 누락 항목 계산" 섹션 맨 앞에 한 줄 추가. Read 로 현재 내용 확인 후 Edit.

`old_string` 예시:
```
### 3-2. 피처별 누락 항목 계산

각 피처에 대해:
1. `applies_to` 와 피처 `platform` 의 교집합이 비어있으면 해당 체크 항목은 스킵
```

`new_string`:
```
### 3-2. 피처별 누락 항목 계산

**excluded 피처 스킵:** `features.json` 의 `excluded: true` 인 피처는 이 단계에서 처리 안 함. 아래 루프는 `excluded == false` 인 피처에만 적용.

각 피처에 대해:
1. `applies_to` 와 피처 `platform` 의 교집합이 비어있으면 해당 체크 항목은 스킵
```

- [ ] **Step 3: 검증**

Run:
```bash
grep -A2 "^### 3-2" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md | head -5
```
Expected: "excluded 피처 스킵" 문구가 3-2 헤더 바로 아래 포함.

---

### Task 6: `SKILL.md` Phase 4 에 excluded 필터링 반영

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md` (Phase 4 섹션)

- [ ] **Step 1: Phase 4-1 위치 확인**

Run:
```bash
grep -n "^### 4-1" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

- [ ] **Step 2: Phase 4-1 "초안 md 파일 렌더" 섹션에 필터 문구 추가**

Read 로 현재 내용 확인. 4-1 본문 맨 앞에 한 줄 추가.

`old_string` 예시:
```
### 4-1. 초안 md 파일 렌더

`features.json` + `missing.json` + `parsed.json` 을 통합해 `${DRAFT_PATH}` 로 저장.
```

`new_string`:
```
### 4-1. 초안 md 파일 렌더

**excluded 피처 제외:** `features.json` 의 `excluded: true` 인 피처는 초안 md 에 등장하지 않는다. Toggle 블록, 노트 섹션, 메타 모두 생성 안 함.

`features.json` + `missing.json` + `parsed.json` 을 통합해 `${DRAFT_PATH}` 로 저장 (excluded 피처 제외).
```

- [ ] **Step 3: 검증**

Run:
```bash
grep -A3 "^### 4-1" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md | head -6
```
Expected: "excluded 피처 제외" 문구 포함.

---

### Task 7: `SKILL.md` Phase 5 에 excluded 필터링 반영

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md` (Phase 5 섹션)

- [ ] **Step 1: Phase 5-2 루프 위치 확인**

Run:
```bash
grep -n "^### 5-2\|^## Phase 5" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

- [ ] **Step 2: Phase 5-2 "피처별 루프" 섹션 시작에 필터 문구 추가**

Read 로 현재 내용 확인. 5-2 본문 맨 앞에 한 줄 추가.

`old_string` 예시 (실제는 Read 결과에 맞게):
```
### 5-2. 피처별 루프

각 피처에 대해:
```

`new_string`:
```
### 5-2. 피처별 루프

**excluded 피처 스킵:** `features.json` 의 `excluded: true` 인 피처는 Notion 조회/생성/업데이트 대상 아님. 아래 루프는 `excluded == false` 인 피처에만 돈다.

각 피처에 대해:
```

- [ ] **Step 3: 검증**

Run:
```bash
grep -A3 "^### 5-2" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md | head -5
```
Expected: "excluded 피처 스킵" 포함.

---

### Task 8: `SKILL.md` Resume 모드 — excluded_ids 직렬화

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md` (Resume 모드 섹션)

- [ ] **Step 1: Resume 모드 섹션 위치 확인**

Run:
```bash
grep -n "^## Resume 모드\|^### R-\|^## Update 모드" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: Resume 모드 헤더 + R-1, R-2, R-3 등 서브섹션 + Update 모드 다음 섹션 경계.

- [ ] **Step 2: Resume 모드의 상태 복구 (R-2) 섹션에 excluded_ids 추가**

Read 로 R-2 현재 내용 확인.

`old_string` 예시:
```
### R-2. 상태 복구

초안 파일의 `<!-- plugin-state -->` 헤더에서 `phase` 를 읽어 다음 Phase 부터 시작:
- `phase: 1` → Phase 2 부터 재실행
- `phase: 2` → Phase 3 부터
- `phase: 3` → Phase 4 부터
- `phase: 4` → Phase 5 부터
```

`new_string`:
```
### R-2. 상태 복구

초안 파일의 `<!-- plugin-state -->` 헤더에서 `phase` 를 읽어 다음 Phase 부터 시작:
- `phase: 1` → Phase 2 부터 재실행
- `phase: 2` → Phase 3 부터
- `phase: 3` → Phase 4 부터
- `phase: 4` → Phase 5 부터

**excluded_ids 복원:** 초안 헤더에 `excluded_ids: ["<uuid>", ...]` 가 있으면 features.json 의 해당 피처들을 `excluded: true` 로 복원. 헤더 포맷 예:

```
<!-- plugin-state
phase: 4
pdf_hash: <short-hash>
source_file: <filename>
created_at: <iso8601>
excluded_ids:
  - <uuid-1>
  - <uuid-2>
-->
```

excluded_ids 가 비어 있거나 키가 없으면 (v0.2 이전 초안) 무시하고 진행. 하위 호환 유지.
```

- [ ] **Step 3: Phase 4 에서 초안 렌더 시 excluded_ids 를 헤더에 기록하는 지시 추가**

Phase 4-1 이미 Task 6 에서 수정됨. 거기에 한 줄 더 추가.

Read 로 Phase 4-1 최신 내용 확인 후 Edit.

`old_string`:
```
### 4-1. 초안 md 파일 렌더

**excluded 피처 제외:** `features.json` 의 `excluded: true` 인 피처는 초안 md 에 등장하지 않는다. Toggle 블록, 노트 섹션, 메타 모두 생성 안 함.

`features.json` + `missing.json` + `parsed.json` 을 통합해 `${DRAFT_PATH}` 로 저장 (excluded 피처 제외).
```

`new_string`:
```
### 4-1. 초안 md 파일 렌더

**excluded 피처 제외:** `features.json` 의 `excluded: true` 인 피처는 초안 md 에 등장하지 않는다. Toggle 블록, 노트 섹션, 메타 모두 생성 안 함.

**excluded_ids 직렬화:** 초안 헤더 `<!-- plugin-state ... -->` 블록에 `excluded_ids: [<uuid>, ...]` 리스트 포함. Resume 시 복원에 사용. excluded 피처가 없으면 빈 리스트 `[]` 또는 키 생략.

`features.json` + `missing.json` + `parsed.json` 을 통합해 `${DRAFT_PATH}` 로 저장 (excluded 피처 제외).
```

- [ ] **Step 4: 검증**

Run:
```bash
grep -c "excluded_ids" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: **3 이상** (R-2 복원 설명 + 헤더 예시 + Phase 4-1 직렬화 지시).

---

### Task 9: Commit 2

- [ ] **Step 1: 변경 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && git status --short && git diff --stat
```
Expected: SKILL.md 만 변경, 약 20-30줄 추가.

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/pdf-spec-organizer/SKILL.md && \
git commit -m "feat(skill): propagate excluded flag to phase 3/4/5 and resume mode"
```
Expected: 커밋 성공.

---

## Commit 3: CHANGELOG

### Task 10: CHANGELOG `[Unreleased]` 에 엔트리 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/CHANGELOG.md`

- [ ] **Step 1: 현재 최상단 섹션 확인**

Run:
```bash
head -10 /Users/chuchu/testPlugin/CHANGELOG.md
```
Expected: 최상단에 `[Unreleased]` 또는 최신 버전 헤더 (예 `## v0.2.0 — 2026-04-20`). 기존 v0.2.0 섹션 **위** 에 새 `[Unreleased]` 추가.

- [ ] **Step 2: Unreleased 섹션 추가**

현재 최상단 버전 헤더(예 `## v0.2.0`) **위에** 삽입.

`old_string`:
```
모든 주목할 만한 변경 사항을 이 파일에 기록합니다.

## v0.2.0 — 2026-04-20
```

> 실제 CHANGELOG 상단 구조는 Step 1 에서 확인한 뒤 정확한 anchor 로 교체.

`new_string`:
```
모든 주목할 만한 변경 사항을 이 파일에 기록합니다.

## [Unreleased]

### Added
- Phase 2-6 **웹 피처 필터링 단계** — 네이티브 개발팀이 웹 전용 피처를 한 번에 제외 (`excluded: true` 플래그). 제외된 피처는 Phase 3/4/5 에서 완전 스킵, Notion 에 생성 안 됨.
- Claude 힌트 — 각 피처 옆에 "웹 같음", "혼합" 등 짧은 태깅 (자동 제외 아님, 사용자 판단 보조용).
- Resume 모드에 `excluded_ids` 직렬화 — 중단된 세션 복구 시 제외 상태 유지.

### Changed
- Phase 3/4/5 워크플로우: `excluded == false` 인 피처만 처리.
- `features.json` 스키마: 각 피처 객체에 `excluded: bool` 필드 추가 (기본 false).

### Compatibility
- v0.2 이전 초안은 `excluded_ids` 헤더가 없어도 resume 정상 동작 (하위 호환).
- Python 스크립트 변경 없음, 기존 18 pytest 그대로 통과.

## v0.2.0 — 2026-04-20
```

- [ ] **Step 3: 검증**

Run:
```bash
head -20 /Users/chuchu/testPlugin/CHANGELOG.md
```
Expected: `## [Unreleased]` 섹션이 v0.2.0 위에 존재, Added/Changed/Compatibility 3 서브섹션 포함.

---

### Task 11: Commit 3

- [ ] **Step 1: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add CHANGELOG.md && \
git commit -m "docs: changelog entry for web feature filter"
```

---

## Verification

### Task 12: 수동 드라이런 (선택 — 사용자 함께)

**Files:** (검증만)

- [ ] **Step 1: 기존 pytest 회귀 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && \
source .venv/bin/activate && \
pytest tests/ -v 2>&1 | tail -3
```
Expected: **18 passed** (Python 변경 없음 → 회귀 없어야).

- [ ] **Step 2: SKILL.md 구조 건강성 체크**

Run:
```bash
grep -c "^## Phase [1-5]" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: **5** (Phase 1-5 헤더 모두 존재).

Run:
```bash
grep -c "^### 2-[0-9]" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: **6** (2-1 부터 2-6 까지).

Run:
```bash
wc -l /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: 500 줄 이내 (v0.2 에서 이미 일부 추가됐을 수 있음. 정확한 상한보다 방향 확인).

- [ ] **Step 3: YAML frontmatter 파싱**

Run:
```bash
source /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/.venv/bin/activate && \
python3 -c "
import yaml
content = open('/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md').read()
fm = yaml.safe_load(content.split('---')[1])
assert fm['name'] == 'pdf-spec-organizer'
print('YAML frontmatter OK')
"
```
Expected: `YAML frontmatter OK`

- [ ] **Step 4: 실제 PDF 드라이런 (사용자 수동)**

이 단계는 사용자가 Claude Code 세션에서 실행:

```
/spec-from-pdf <실제 기획 PDF 경로>
```

검증 체크리스트 (사용자가 확인):
- [ ] Phase 2-2 에서 피처 목록 표시, `💡 Claude` 힌트 일부 피처에 나타남
- [ ] Phase 2-6 웹 제외 프롬프트 표시됨
- [ ] `2, 5` 입력 → 해당 피처가 이후 Phase 에서 스킵됨
- [ ] `all` → 이중 확인 후 정상 종료 ("모든 피처 제외" 메시지)
- [ ] Enter → 모든 피처 포함 진행
- [ ] Phase 5 완료 후 Notion 에 excluded 피처 미생성 확인
- [ ] `/spec-resume --resume-latest` → excluded 상태 유지

문제 발견 시 해당 Task 로 돌아가 수정 후 재시도.

---

## Oracle 이슈 (플랜 범위 밖)

- Claude 힌트 정확도 측정 — 실사용 데이터 쌓이면 v0.3.x 에서 튜닝 여부 결정
- 전용 `split-web N` 명령 (혼합 피처 분리 전담) — 사용자 피드백 보고 판단
- 웹 전용 피처의 기록 보존 (excluded 이력 별도 저장) — v0.4 이후 고려
