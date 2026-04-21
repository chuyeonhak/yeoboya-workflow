# pdf-spec-organizer Skill Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `skills/pdf-spec-organizer/SKILL.md` 의 description 을 자연어 트리거에 최적화하고, Phase 5 를 축약하며, Precondition/Phase 별 "Why" 주석을 추가하고, description 자동 튜닝을 위한 trigger eval set 을 준비한다.

**Architecture:** 스킬 워크플로우 로직 자체는 건드리지 않음. SKILL.md 프론트매터 업데이트 + Phase 5 세부를 `references/conflict-policy.md` 로 이동 + 섹션별 Why 주석 삽입. 신규 `evals/trigger-eval.json` 생성 후 `README.md` 에 `skill-creator` 의 `run_loop.py` 실행 가이드 추가.

**Tech Stack:** Markdown (SKILL.md, references, README), JSON (evals), 파이썬 의존성 검증 (기존 pytest suite).

**Spec reference:** `docs/superpowers/specs/2026-04-19-pdf-spec-organizer-skill-refactor-design.md`

---

## File Structure Overview

| 경로 | 책임 | 이번 플랜에서 |
|---|---|---|
| `skills/pdf-spec-organizer/SKILL.md` | 스킬 워크플로우 정의 | description 개정, Phase 5 축약, Why 주석 추가 |
| `skills/pdf-spec-organizer/references/conflict-policy.md` | 충돌 처리 세부 규칙 | "Phase 5 충돌 처리" + "이미지 업로드 전략" 섹션 추가 |
| `evals/trigger-eval.json` (신규) | Description 트리거 eval queries | 신규 생성 (20 개) |
| `README.md` | 플러그인 소개 + 가이드 | "Description 최적화 실행" 섹션 + 문서 링크 갱신 |
| `CHANGELOG.md` | 버전 기록 | [Unreleased] 섹션에 skill refactor 엔트리 추가 |

---

## Commit 1: Skill Refactor

### Task 1: SKILL.md frontmatter 의 description 재작성

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md:1-5`

- [ ] **Step 1: 현재 frontmatter 읽기**

Run:
```bash
head -5 /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected 출력:
```
---
name: pdf-spec-organizer
description: 복합 PDF 스펙(PRD+디자인+플로우)을 파싱해 Notion 피처 DB 페이지로 정리한다. 명세 누락 체크 + iOS/Android 플랫폼별 개발자 노트 공유. /spec-from-pdf, /spec-update, /spec-resume 커맨드의 실제 로직.
allowed-tools: Bash Read Write Edit Grep Glob mcp__claude_ai_Notion__notion-search mcp__claude_ai_Notion__notion-fetch mcp__claude_ai_Notion__notion-create-pages mcp__claude_ai_Notion__notion-create-database mcp__claude_ai_Notion__notion-update-page mcp__claude_ai_Notion__notion-update-data-source
---
```

- [ ] **Step 2: description 만 새 문장으로 교체**

Edit 도구로 `SKILL.md` 의 description 라인을 다음 문장으로 정확히 교체:

**Old:**
```
description: 복합 PDF 스펙(PRD+디자인+플로우)을 파싱해 Notion 피처 DB 페이지로 정리한다. 명세 누락 체크 + iOS/Android 플랫폼별 개발자 노트 공유. /spec-from-pdf, /spec-update, /spec-resume 커맨드의 실제 로직.
```

**New:**
```
description: 기획자/PM 에게 받은 PDF 스펙(PRD, 디자인 시안, 유저 플로우) 을 Notion 피처 DB 페이지로 정리한다. 명세 누락 (에러/빈상태/오프라인/권한/로딩/접근성) 을 자동 체크하고 iOS/Android 팀이 같은 페이지에서 플랫폼별 개발자 노트를 공유하도록 구조화한다. 사용자가 "이 PDF 정리해줘", "기획서 스펙 정리", "피처 스펙 노션에 올려줘", "개발자 노트 정리", "명세 누락 체크해줘" 같은 요청을 하거나 기획 PDF 문서를 언급할 때 반드시 이 스킬을 사용할 것. 슬래시 커맨드 `/spec-from-pdf`, `/spec-update`, `/spec-resume` 의 실제 구현 로직.
```

`name:` 과 `allowed-tools:` 줄은 그대로 유지.

- [ ] **Step 3: frontmatter YAML 파싱 유효성 검증**

Run (venv 활성화 필요 — pyyaml 설치된 환경):
```bash
source /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/.venv/bin/activate && \
python3 -c "
import sys, yaml
content = open('/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md').read()
parts = content.split('---')
if len(parts) < 3:
    print('FAIL: frontmatter 구분자 ---  부족', file=sys.stderr); sys.exit(1)
fm = yaml.safe_load(parts[1])  # 실제 YAML 파싱 — 쌍따옴표/특수문자 escape 검증
assert fm['name'] == 'pdf-spec-organizer', f\"name 불일치: {fm.get('name')}\"
assert '이 PDF 정리해줘' in fm['description'], '새 description 키워드 누락'
assert '명세 누락 체크해줘' in fm['description'], '5번째 어휘 누락'
assert 'allowed-tools' in fm, 'allowed-tools 누락'
print('OK — YAML 파싱 성공')
"
```
Expected: `OK — YAML 파싱 성공`

> **왜 YAML 파서:** 단순 문자열 `in` 체크는 YAML 구조 깨짐(예: 쌍따옴표 unquoting, multi-line, 콜론 이스케이프)을 잡지 못함. 실제 Claude Code 가 frontmatter 를 로드할 때 쓰는 파싱과 동일한 검증 필요.

---

### Task 2: conflict-policy.md 에 "Phase 5 충돌 처리" 섹션 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md`

- [ ] **Step 1: 현재 파일 읽기**

Run:
```bash
cat /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md
```

현재 내용은 기본 방침(병합 기본값) 만 담고 있음.

- [ ] **Step 2: 파일 끝에 새 섹션 추가**

Edit 도구로 파일 끝에 아래 내용 append (원본 내용 앞에는 변경 없음):

````markdown

## Phase 5 충돌 처리

Phase 5 에서 피처별 조회 결과 동명 피처가 있을 때 적용하는 상세 동작. (SKILL.md 의 5-2 단계 2번에서 호출)

### 사용자 프롬프트 예시

```
Notion 에 같은 피처가 이미 존재합니다:
  제목: <피처명>
  최근 생성자: <author>
  생성일: <date>
  기존 PDF 해시: <hash or "없음">  (현재: <my_hash>)

어떻게 할까요?
  [1] 병합 (내 플랫폼 섹션만 append) ← 기본
  [2] 덮어쓰기 (기존 노트 손실 가능)
  [3] 새 버전 (이전_버전 Relation 으로 연결)
  [4] 건너뛰기 (이 피처만 스킵)
>
```

### `--fast` 플래그 동작

- `[1] 병합` 은 자동 선택 (파괴적이지 않음)
- `[2]/[3]/[4]` 는 `--fast` 에서도 항상 프롬프트 발생 (파괴적이거나 부작용 큼)

### 각 옵션 구현

- **병합 [1]**: `mcp__claude_ai_Notion__notion-fetch` 로 기존 페이지 본문 읽기 → 내 플랫폼 섹션만 교체 → `mcp__claude_ai_Notion__notion-update-page` 로 업데이트. 타 플랫폼 노트와 공통 질문 섹션은 건드리지 않음.
- **덮어쓰기 [2]**: "정말로 덮어쓰시겠습니까? (y/N)" 추가 확인 → `y` 면 전체 본문 교체. 다른 팀원의 노트가 사라질 수 있으므로 명시적 이중 확인.
- **새 버전 [3]**: 새 페이지를 `mcp__claude_ai_Notion__notion-create-pages` 로 생성 + 새 페이지의 `이전_버전` Relation 속성에 기존 페이지 연결. 기존 페이지는 건드리지 않음.
- **건너뛰기 [4]**: 이 피처만 skip, 다음 피처로 이동.

## 이미지 업로드 전략

각 피처의 `screens` (이미지 경로 리스트) 를 Notion 에 첨부할 때 따른다. (SKILL.md 의 5-2 단계 4번에서 호출)

### 1차 fallback: placeholder URL

`mcp__claude_ai_Notion__notion-create-pages` 는 로컬 파일 경로를 직접 업로드하지 못할 수 있음. 지원 여부를 시도 후:

- **지원 O**: 정상 업로드
- **지원 X**: 이미지 블록에 **placeholder URL (예: `https://placehold.co/600x400?text=local-image`)** 을 넣고, 캡션에 **로컬 경로를 주석으로 표시** (예: "원본: /tmp/spec-draft-<hash>-<ts>/images/page_1_img_0.png")

### 2차 계획 (v0.2)

S3 또는 imgur 등 외부 호스팅 중계 업로더 추가. 로컬 경로를 외부 URL 로 변환 후 Notion 에 제출. `yeoboya-workflow.config.json` 에 `image_upload_bucket` 같은 필드 추가 예정.

### 사용자 통지

placeholder 로 fallback 된 경우 터미널에 한 줄 경고:
```
⚠️  3개 이미지가 placeholder 로 대체됐습니다. 원본 경로는 캡션 주석을 참조하세요.
```
````

- [ ] **Step 3: 파일 크기/구조 검증**

Run:
```bash
wc -l /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md && \
grep -c "^## " /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md
```

Expected:
- 줄 수 ~ 80 이상
- `^## ` 헤더 카운트: 최소 3개 (원래 2개 + Phase 5 + 이미지 업로드 = 총 4 또는 그 이상). 실제 원본 구조에 따라 다르지만 최소 3.

Run:
```bash
grep -E "Phase 5 충돌 처리|이미지 업로드 전략" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md
```
Expected: 두 헤더 모두 출력됨.

---

### Task 3: SKILL.md 의 Phase 5 섹션 축약

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md` (Phase 5 섹션)

- [ ] **Step 1: 현재 Phase 5 범위 확인**

Run:
```bash
grep -n "^## Phase 5\|^## Resume 모드" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: 두 라인 번호. 예: `346:## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③` 와 `440:## Resume 모드` (실제 줄 번호는 다를 수 있음).

이 두 라인 사이가 현재 Phase 5. 교체 대상.

- [ ] **Step 2: 기존 Phase 5 섹션을 Read 도구로 추출**

Read 도구로 SKILL.md 를 Step 1 의 grep 결과에 근거해 Phase 5 시작 라인부터 "Resume 모드" 바로 앞 줄까지 읽는다. 예시 (실제 줄 번호는 Step 1 grep 결과로 대체):

```
Read file_path=/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md offset=346 limit=94
```

(`offset` 은 Phase 5 시작, `limit` 은 Resume 모드 바로 앞까지의 줄 수)

읽은 전체 블록을 **변경 없이 그대로** 다음 단계의 Edit `old_string` 으로 사용한다.

> **왜 Read 로 먼저 가져오나:** Edit 도구는 `old_string` 이 파일과 byte 단위로 정확히 일치해야 동작한다. Phase 5 본문 ~95줄을 플랜에 그대로 인라인하면 bloat + 스크립트 블록의 backtick/달러 escape 위험이 커짐. Read 결과를 복사해 쓰는 것이 안전.

- [ ] **Step 3: Phase 5 섹션을 새 내용으로 Edit 교체**

Edit 도구 호출:
- `file_path`: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`
- `old_string`: **Step 2 에서 Read 로 얻은 전체 Phase 5 블록** (토씨 하나 건드리지 말 것)
- `new_string`: 아래 블록

**New (Phase 5 축약본 — old_string 을 아래 new_string 으로 교체):**

```markdown
## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

### 5-1. DB ID 확보

Precondition 2 에서 읽은 `notion_database_id` 사용. 존재 가정.

### 5-2. 피처별 루프

각 피처에 대해:

1. `mcp__claude_ai_Notion__notion-search` 로 DB 안에서 동명 피처 조회
2. **존재 시** → `references/conflict-policy.md` 의 **"Phase 5 충돌 처리"** 섹션을 따라 사용자 프롬프트 + 옵션 실행
3. **없음 시** → `mcp__claude_ai_Notion__notion-create-pages` 로 새 페이지 생성. 속성: 이름 / 플랫폼 / 상태=Draft / 원본_PDF=파일명만 / PDF_해시 / 생성자=현재 사용자 / 누락_항목=`missing` 리스트. 본문: `draft.md` 의 Notion 블록 변환본.
4. **이미지 첨부** → `references/conflict-policy.md` 의 **"이미지 업로드 전략"** 섹션을 따라 처리 (placeholder fallback 포함)

### 5-3. 실행 기록 갱신

모든 피처 성공 시:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  update-status --draft-path "$DRAFT_PATH" --status success
```

부분 실패 시 `failed` 기록 + 실패 피처 목록 터미널 표시 + `/spec-resume` 가이드:
```
⚠️  3개 중 2개 피처만 퍼블리시됐습니다:
  ✓ 알림 설정 화면
  ✓ 푸시 권한 요청 플로우
  ✗ 빈 상태 UI (Notion API timeout)

이어서 시도: /spec-resume --resume-latest
초안: <draft_path>
```

### 5-4. 결과 요약

성공 시:
```
✓ 퍼블리시 완료:
  - 알림 설정 화면: https://notion.so/...
  - 푸시 권한 요청 플로우: https://notion.so/...
  - 빈 상태 UI: https://notion.so/...

초안은 3일 후 자동 삭제됩니다: <draft_path>
```

### 5-5. GC 트리거

성공 시만 기회적 gc:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" gc
```
```

- [ ] **Step 4: 길이 검증**

Run:
```bash
wc -l /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: 원래 479 줄 → 약 430 줄 (Phase 5 약 –50 줄). 오차 ±5 줄 허용.

Run:
```bash
grep -n "^## " /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: 주요 섹션 헤더들이 모두 존재 (Precondition, Phase 1-5, Resume 모드, Update 모드).

- [ ] **Step 5: 실패 시 롤백 가이드**

Step 4 길이 검증 결과가 ±5줄 오차를 넘거나, `grep -n "^## "` 에서 Phase 1-5 중 하나라도 누락 감지됐다면 **Edit 이 잘못 적용된 것**. 즉시 롤백 후 Step 2 부터 재시도:

```bash
cd /Users/chuchu/testPlugin && git restore skills/pdf-spec-organizer/SKILL.md
```

> **왜 롤백:** 부분 적용된 SKILL.md 로 Task 4 커밋이 나가면 Task 5/6 의 Why 주석 Edit 이 예상 위치를 못 찾아 연쇄 실패 발생.

---

### Task 4: Commit 1 — skill refactor

- [ ] **Step 1: 변경 파일 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && git status --short
```

Expected:
```
 M skills/pdf-spec-organizer/SKILL.md
 M skills/pdf-spec-organizer/references/conflict-policy.md
```

- [ ] **Step 2: diff 내용 확인 (손상 없는지)**

Run:
```bash
cd /Users/chuchu/testPlugin && git diff --stat
```

Expected: 두 파일에 insert/delete 수치. SKILL.md 는 대체로 `-` 많고, conflict-policy.md 는 `+` 많음.

- [ ] **Step 3: 커밋**

Run:
```bash
cd /Users/chuchu/testPlugin && \
git add skills/pdf-spec-organizer/SKILL.md skills/pdf-spec-organizer/references/conflict-policy.md && \
git commit -m "refactor(skill): rewrite description for natural-language triggering and relocate phase 5 details to conflict-policy"
```

Expected: 커밋 성공, SHA 출력.

---

## Commit 2: Skill Annotations (Why 주석)

### Task 5: Precondition 4개 섹션에 "Why" 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md` (Precondition 섹션)

- [ ] **Step 1: 현재 Precondition 구조 확인**

Run:
```bash
grep -n "^### [1-4]\." /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md | head -4
```

Expected 4개 섹션 헤더: 인자 확인 / 팀 공유 설정 확인 / Python 의존성 확인 / Tesseract 확인.

- [ ] **Step 2: Precondition 1 에 Why 추가**

Edit Old:
```
### 1. 인자 확인

- 필수: `PDF_PATH` 환경 변수 또는 커맨드 인자
```

Edit New:
```
### 1. 인자 확인

**왜:** PDF 경로가 없으면 이후 Phase 전체가 실패함. 진입점에서 빠르게 차단해 /tmp 낭비와 잘못된 상태 방지.

- 필수: `PDF_PATH` 환경 변수 또는 커맨드 인자
```

- [ ] **Step 3: Precondition 2 에 Why 추가**

Edit Old:
```
### 2. 팀 공유 설정 확인

- **현재 워크스페이스 레포 루트**에서 `yeoboya-workflow.config.json` 을 찾는다.
```

Edit New:
```
### 2. 팀 공유 설정 확인

**왜:** 팀원들이 각자 다른 Notion DB 에 피처를 만들면 iOS/Android 가 서로 못 봄. 레포에 커밋된 설정이 "팀의 단일 DB" 를 보장.

- **현재 워크스페이스 레포 루트**에서 `yeoboya-workflow.config.json` 을 찾는다.
```

- [ ] **Step 4: Precondition 3 에 Why 추가**

Edit Old:
```
### 3. Python 의존성 확인

Run (Bash):
```

Edit New:
```
### 3. Python 의존성 확인

**왜:** 후속 스크립트들이 모두 PyPDF2/pdf2image/yaml 등을 import. Phase 1 중간에 실패하면 초안 일관성이 깨지고 사용자 혼란 유발.

Run (Bash):
```

- [ ] **Step 5: Precondition 4 에 Why 추가**

Edit Old:
```
### 4. Tesseract 확인 (경고만, 차단 아님)

Run: `command -v tesseract`
```

Edit New:
```
### 4. Tesseract 확인 (경고만, 차단 아님)

**왜:** 이미지 전용 PDF 에서만 필요. 텍스트 PDF 는 Tesseract 없이도 정상 동작하므로 강제하지 않음 — 경고로 알리기만.

Run: `command -v tesseract`
```

- [ ] **Step 6: 4개 Why 블록 모두 삽입 확인**

Run:
```bash
grep -c "^\*\*왜:\*\*" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: **4** (Precondition 만 수정했으니 이 시점엔 4)

---

### Task 6: Phase 1~5 섹션에 "Why" 추가

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md` (Phase 1~5)

- [ ] **Step 1: Phase 1 에 Why 추가**

Edit Old:
```
## Phase 1 — 파싱

### 1-1. 임시 작업 폴더 생성
```

Edit New:
```
## Phase 1 — 파싱

**왜:** 후속 Phase 는 모두 파싱 결과를 읽음. 여기서 실패하면 뒤는 무의미. 이미지 추출 / OCR fallback / PII 스캔을 이 Phase 에 몰아서 한 번만 처리해 효율 확보.

### 1-1. 임시 작업 폴더 생성
```

- [ ] **Step 2: Phase 2 에 Why 추가**

Edit Old:
```
## Phase 2 — 구조화 + 개입 ①

### 2-1. Claude 에게 피처 추출 지시
```

Edit New:
```
## Phase 2 — 구조화 + 개입 ①

**왜:** PDF 를 자동으로 피처 단위로 쪼개는 건 Claude 의 추정이라 실수 가능. 개발자가 한 번 검증해야 잘못된 구조로 Notion 이 오염되지 않음.

### 2-1. Claude 에게 피처 추출 지시
```

- [ ] **Step 3: Phase 3 에 Why 추가**

Edit Old:
```
## Phase 3 — 누락 체크

### 3-1. 체크리스트 로드
```

Edit New:
```
## Phase 3 — 누락 체크

**왜:** 기획서가 엣지케이스(에러/빈상태/오프라인 등) 를 빠뜨리는 건 흔함. 표준 체크리스트로 구현 단계 리스크를 사전 감소. 체크 자체는 자동, 해석/대응은 개발자 노트에서.

### 3-1. 체크리스트 로드
```

- [ ] **Step 4: Phase 4 에 Why 추가**

Edit Old:
```
## Phase 4 — 개발자 노트 + 미리보기 + 개입 ②

### 4-1. 초안 md 파일 렌더
```

Edit New:
```
## Phase 4 — 개발자 노트 + 미리보기 + 개입 ②

**왜:** 기술 판단(iOS/Android 구현 차이, 엣지케이스, 팀 간 질문거리) 은 Claude 가 대신할 수 없는 영역. 이 단계가 스킬의 핵심 가치 — 팀 지식을 축적하는 지점.

### 4-1. 초안 md 파일 렌더
```

- [ ] **Step 5: Phase 5 에 Why 추가**

Edit Old:
```
## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

### 5-1. DB ID 확보
```

Edit New:
```
## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

**왜:** iOS/Android 개발자가 같은 PDF 를 따로 돌릴 수 있음. 병합 기본값으로 타 플랫폼 노트를 실수로 지우는 상황을 방지 — 팀 협업의 파괴적 동시성 리스크 차단.

### 5-1. DB ID 확보
```

- [ ] **Step 6: 모든 Why 블록 수 검증**

Run:
```bash
grep -c "^\*\*왜:\*\*" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: **9** (Precondition 4개 + Phase 5개 = 9)

Run:
```bash
wc -l /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: Task 3 끝난 후 ~430 → +약 +18 줄 (왜 블록 9개 × 평균 2줄) → **약 448 줄**. 500 줄 이내 유지.

---

### Task 7: Commit 2 — annotations

- [ ] **Step 1: 변경 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && git status --short && git diff --stat
```

Expected: 오직 `SKILL.md` 만 변경. +약 18 줄 추가.

- [ ] **Step 2: 커밋**

Run:
```bash
cd /Users/chuchu/testPlugin && \
git add skills/pdf-spec-organizer/SKILL.md && \
git commit -m "docs(skill): add why annotations to precondition and phase sections"
```

Expected: 커밋 성공.

---

## Commit 3: Trigger Eval Setup

### Task 8: `evals/trigger-eval.json` 생성

**Files:**
- Create: `/Users/chuchu/testPlugin/evals/trigger-eval.json`

- [ ] **Step 1: 디렉토리 생성**

Run:
```bash
mkdir -p /Users/chuchu/testPlugin/evals
```

- [ ] **Step 2: 파일 작성**

Write 도구로 `/Users/chuchu/testPlugin/evals/trigger-eval.json` 을 아래 내용으로 생성:

```json
[
  {"query": "/spec-from-pdf ~/Downloads/설정.pdf", "should_trigger": true},
  {"query": "이 기획서 PDF 좀 정리해서 노션에 올려줘. 파일은 ~/Downloads/알림설정_v3.pdf 이거야. iOS랑 Android 팀이 같이 봐야돼", "should_trigger": true},
  {"query": "PM이 방금 보낸 피처 스펙 정리해줘. 에러 케이스랑 오프라인 처리 누락됐는지도 체크해줘", "should_trigger": true},
  {"query": "이 PRD 문서 spec 페이지로 만들어 주세요. Notion database에 들어갈 수 있게요. ~/Docs/feature_prd.pdf", "should_trigger": true},
  {"query": "이 PDF에서 접근성이랑 빈 상태 UI 누락됐는지 체크하고 피처 페이지로 정리해줘", "should_trigger": true},
  {"query": "iOS랑 Android 같이 볼 수 있게 피처 스펙 공유 페이지 만들어. 각 플랫폼 개발자가 노트 남길 수 있는 구조로", "should_trigger": true},
  {"query": "이거 받은 기획서인데 정리 좀... 완전 raw 상태야 ㅠㅠ ~/Downloads/new_feature_draft.pdf", "should_trigger": true},
  {"query": "기존 노션 페이지에 Android 구현 노트 추가하고 싶어. https://www.notion.so/workspace/알림-설정-abc123 여기야", "should_trigger": true},
  {"query": "~/Downloads/새로운-피처-스펙.pdf 이거 처리해줘", "should_trigger": true},
  {"query": "우리 팀 iOS 개발자가 먼저 스펙 올려놨는데 같은 페이지에 내가 Android 노트 남길 수 있어?", "should_trigger": true},
  {"query": "이 PDF 요약해줘 ~/Downloads/paper.pdf. 연구 논문이야", "should_trigger": false},
  {"query": "이 API 스펙을 OpenAPI 문서로 만들어줘. /api/v2 엔드포인트들 다 정리해서", "should_trigger": false},
  {"query": "이 내용을 노션에 페이지로 저장해줘: '회의록 2026-04-19 — 참석자 김철수, 이영희...'", "should_trigger": false},
  {"query": "이 PDF를 Confluence에 올려줘. ~/Docs/quarterly_report.pdf", "should_trigger": false},
  {"query": "이 스크린샷에서 텍스트 추출해줘. ~/Screenshots/error_dialog.png", "should_trigger": false},
  {"query": "이 PDF를 슬라이드로 만들어줘. Keynote나 파워포인트 형식으로", "should_trigger": false},
  {"query": "이 기획서 PDF를 영어로 번역해줘. 해외 팀에 공유해야 돼", "should_trigger": false},
  {"query": "이 여권 스캔 정리해서 노션에 저장해줘. ~/Documents/passport.pdf", "should_trigger": false},
  {"query": "코드 리뷰 체크리스트 만들어줘. 우리 팀 PR 리뷰 기준으로", "should_trigger": false},
  {"query": "iOS 알림 권한 요청 구현해줘. UNUserNotificationCenter 쓰는 방식으로", "should_trigger": false}
]
```

- [ ] **Step 3: JSON 유효성 + 개수 검증**

Run:
```bash
python3 -c "
import json
data = json.load(open('/Users/chuchu/testPlugin/evals/trigger-eval.json'))
assert isinstance(data, list), 'list 아님'
assert len(data) == 20, f'20개 아님 ({len(data)}개)'
trigger = sum(1 for d in data if d['should_trigger'])
no_trigger = sum(1 for d in data if not d['should_trigger'])
assert trigger == 10, f'should_trigger 10 아님 ({trigger})'
assert no_trigger == 10, f'should_not_trigger 10 아님 ({no_trigger})'
print('OK — 20개 (trigger 10 + no_trigger 10)')
"
```

Expected: `OK — 20개 (trigger 10 + no_trigger 10)`

---

### Task 9: README 확장 + CHANGELOG 엔트리

**Files:**
- Modify: `/Users/chuchu/testPlugin/README.md` (Description 최적화 섹션 + 문서 링크 갱신)
- Modify: `/Users/chuchu/testPlugin/CHANGELOG.md` (Unreleased 엔트리)

- [ ] **Step 1: 현재 README 에 "개발 / 확장" 섹션 위치 확인**

Run:
```bash
grep -n "^## 개발" /Users/chuchu/testPlugin/README.md
```

Expected: `## 개발 / 확장` 이 있는 줄 번호 출력.

- [ ] **Step 2: "테스트" 서브섹션 끝에 새 서브섹션 추가**

README 의 "개발 / 확장" 섹션 안, "### 테스트" 서브섹션 끝 (다음 서브섹션인 `### 수동 QA` 직전) 에 아래 내용 추가.

Edit Old (유일 식별 가능한 문자열):
```markdown
18개 단위 테스트 (parse_pdf, ocr_fallback, pii_scan, pdf_hash, draft_registry).

### 수동 QA
```

Edit New:
````markdown
18개 단위 테스트 (parse_pdf, ocr_fallback, pii_scan, pdf_hash, draft_registry).

### Description 최적화 실행

skill-creator 의 `run_loop.py` 로 `pdf-spec-organizer` 스킬의 description 을 자동 튜닝할 수 있다. 20개 trigger eval query 는 `evals/trigger-eval.json` 에 준비됨.

```bash
# skill-creator 가 설치된 디렉토리로 이동 (예: 플러그인 캐시)
cd ~/.claude/plugins/cache/skill-creator/unknown/skills/skill-creator

python -m scripts.run_loop \
  --eval-set /Users/chuchu/testPlugin/evals/trigger-eval.json \
  --skill-path /Users/chuchu/testPlugin/skills/pdf-spec-organizer \
  --model claude-opus-4-7 \
  --max-iterations 5 \
  --verbose
```

- 20개 쿼리 중 12개는 train, 8개는 held-out test (60/40 분할)
- 각 쿼리 3회 실행하여 트리거 비율 평균
- 반복 최대 5회, 최고 test score 의 description 선정
- 완료되면 HTML 리포트가 브라우저에 열림
- 결과의 `best_description` 을 `SKILL.md` frontmatter 에 반영하여 커밋

### 수동 QA
````

- [ ] **Step 3: 삽입 확인**

Run:
```bash
grep -n "Description 최적화 실행" /Users/chuchu/testPlugin/README.md
```

Expected: 한 라인 출력 (서브섹션 헤더 존재).

Run:
```bash
grep -c "run_loop.py" /Users/chuchu/testPlugin/README.md
```

Expected: **1** 이상 (새 섹션에 언급됨).

- [ ] **Step 4: README 의 "## 문서" 섹션에 이번 refactor 스펙/플랜 링크 추가**

Edit Old:
```markdown
- **설계 스펙**: [`docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md`](docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md)
- **구현 계획**: [`docs/superpowers/plans/2026-04-19-pdf-spec-organizer.md`](docs/superpowers/plans/2026-04-19-pdf-spec-organizer.md)
- **수동 QA**: [`docs/manual-qa.md`](docs/manual-qa.md)
- **변경 내역**: [`CHANGELOG.md`](CHANGELOG.md)
```

Edit New:
```markdown
- **설계 스펙 (v0.1)**: [`docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md`](docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md)
- **구현 계획 (v0.1)**: [`docs/superpowers/plans/2026-04-19-pdf-spec-organizer.md`](docs/superpowers/plans/2026-04-19-pdf-spec-organizer.md)
- **설계 스펙 (skill refactor)**: [`docs/superpowers/specs/2026-04-19-pdf-spec-organizer-skill-refactor-design.md`](docs/superpowers/specs/2026-04-19-pdf-spec-organizer-skill-refactor-design.md)
- **구현 계획 (skill refactor)**: [`docs/superpowers/plans/2026-04-19-pdf-spec-organizer-skill-refactor.md`](docs/superpowers/plans/2026-04-19-pdf-spec-organizer-skill-refactor.md)
- **수동 QA**: [`docs/manual-qa.md`](docs/manual-qa.md)
- **변경 내역**: [`CHANGELOG.md`](CHANGELOG.md)
```

- [ ] **Step 5: CHANGELOG 에 skill refactor 엔트리 추가**

현재 CHANGELOG 의 [0.1.0] 섹션 위에 새 Unreleased 섹션 추가.

Edit Old:
```markdown
# Changelog

모든 주목할 만한 변경 사항을 이 파일에 기록합니다.

## [0.1.0] - 2026-04-19
```

Edit New:
```markdown
# Changelog

모든 주목할 만한 변경 사항을 이 파일에 기록합니다.

## [Unreleased]

### Changed
- `pdf-spec-organizer` 스킬 description 을 자연어 트리거에 최적화 (사용자 실제 어휘 5종 반영, skill-creator "pushy" 원칙 적용)
- SKILL.md Phase 5 세부(충돌 처리 프롬프트, 이미지 업로드 fallback) 를 `references/conflict-policy.md` 로 이동 (SKILL.md 길이 감축)

### Added
- SKILL.md 의 Precondition 4개 + Phase 5개 섹션에 "왜 이 단계가 있는가" 주석 추가 (LLM 의도 이해도 향상)
- `evals/trigger-eval.json` — 20 개 description 트리거 eval query (should-trigger 10 + should-not-trigger 10)
- README 에 `skill-creator` 의 `run_loop.py` 실행 가이드 추가 (description 자동 튜닝 루프)

## [0.1.0] - 2026-04-19
```

---

### Task 10: Commit 3 — trigger eval setup

- [ ] **Step 1: 변경 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && git status --short
```

Expected (파일 3개: evals 신규, README/CHANGELOG 수정):
```
 M CHANGELOG.md
 M README.md
?? evals/
```

- [ ] **Step 2: 커밋**

Run:
```bash
cd /Users/chuchu/testPlugin && \
git add evals/trigger-eval.json README.md CHANGELOG.md && \
git commit -m "chore(evals): add trigger eval queries, changelog, and run_loop.py guide"
```

Expected: 커밋 성공.

---

## Task 11: 최종 검증

- [ ] **Step 1: 3개 커밋 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && git log --oneline | head -5
```

Expected: 최근 3개 커밋이 refactor / annotations / eval setup 순.

- [ ] **Step 2: 기존 Python 테스트 회귀 없음 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && \
source .venv/bin/activate && \
pytest tests/ -v
```

Expected: **18 passed** (기존 스크립트 변경 없음 → 회귀 없어야 함).

- [ ] **Step 3: SKILL.md 길이 확인**

Run:
```bash
wc -l /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: **약 440~460 줄** (500 줄 이하 유지).

- [ ] **Step 4: frontmatter 새 description 반영 확인**

Run:
```bash
head -4 /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: description 에 "기획자/PM", "이 PDF 정리해줘", "반드시 이 스킬을 사용할 것" 문구 포함.

- [ ] **Step 5: Why 주석 9개 반영 확인**

Run:
```bash
grep -c "^\*\*왜:\*\*" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```

Expected: **9**

- [ ] **Step 6: conflict-policy.md 확장 확인**

Run:
```bash
grep -E "Phase 5 충돌 처리|이미지 업로드 전략" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md
```

Expected: 두 헤더 모두 출력.

- [ ] **Step 7: evals/trigger-eval.json 존재 + 유효**

Run:
```bash
python3 -c "import json; d=json.load(open('/Users/chuchu/testPlugin/evals/trigger-eval.json')); print('items:', len(d), 'trigger:', sum(1 for x in d if x['should_trigger']))"
```

Expected: `items: 20 trigger: 10`

- [ ] **Step 8: 샘플 PDF 드라이런 (스펙의 수동 검증 요구)**

스킬 워크플로우 동작이 refactor 전과 동일한지 확인. Phase 1~5 를 수동으로 재현:

```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && \
source .venv/bin/activate && \
PDF_PATH="tests/samples/minimal.pdf" && \
PDF_HASH=$(python3 pdf_hash.py "$PDF_PATH") && \
WORK_DIR="/tmp/skill-refactor-verify-${PDF_HASH}" && \
mkdir -p "$WORK_DIR/images" && \
python3 parse_pdf.py "$PDF_PATH" --out-dir "$WORK_DIR/images" > "$WORK_DIR/parsed.json" && \
python3 -c "import json; d=json.load(open('$WORK_DIR/parsed.json')); assert 'Notification' in d['pages'][0]['text']; print('Phase 1 OK')" && \
python3 -c "import json; d=json.load(open('$WORK_DIR/parsed.json')); print('\n'.join(p['text'] for p in d['pages']))" | \
python3 pii_scan.py > "$WORK_DIR/pii.json" && \
python3 -c "import json; d=json.load(open('$WORK_DIR/pii.json')); assert any(f['category']=='email' for f in d['findings']); print('PII scan OK')" && \
rm -rf "$WORK_DIR" && \
echo "드라이런 완료 — 기존 동작 유지"
```

Expected: `Phase 1 OK`, `PII scan OK`, `드라이런 완료 — 기존 동작 유지` 순차 출력. 실패 시 refactor 가 스크립트 경로 혹은 config 를 깨뜨렸을 가능성 — 원인 조사 필요.

> **왜 수동 드라이런:** 스크립트 자체는 이번 refactor 에서 건드리지 않지만, SKILL.md 가 참조하는 경로나 환경 변수가 어긋났을 수 있음. 실제 파이프라인 1회 실행으로 확인.

---

## Oracle 이슈 (이번 플랜 범위 밖)

- `run_loop.py` 실제 실행은 **사용자 판단** — eval set 준비까지만 이번 플랜
- 실행 결과로 나온 `best_description` 을 반영하는 follow-up 커밋은 별도
- 개정된 description 의 자연어 트리거 실효성은 `run_loop.py` 결과로 정량 검증 가능
