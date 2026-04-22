# yeoboya-workflow

**여보야 iOS/Android 팀을 위한 Claude Code 플러그인.** 기획자에게 받은 PDF 스펙을 Notion 피처 DB 로 정리하고, 누락된 엣지케이스를 자동 체크하고, 플랫폼별 개발 노트를 한 페이지에서 공유한다.

**상태:** v0.4.0 — 프로젝트 컨텍스트 기반 피처 메타 자동 제안 기능 추가

---

## 이건 뭐 하는 건가요?

하루에 한 번쯤은 이런 상황이 있죠:

- 기획자가 PDF 를 공유방에 올렸다. **언제까지 개발 가능한지 물어본다.**
- iOS/Android 가 **각자 PDF 를 열어 읽고**, 각자 Notion/Slack 에 해석을 남긴다.
- 구현 단계에서 "에러 케이스는 어떡하지?", "빈 상태는?" 같은 질문이 터진다.
- 같은 피처를 나중에 다시 보려면 Notion · Slack · DM 을 뒤져야 한다.

이 플러그인은 그걸 **한 번의 커맨드** 로 정리합니다:

```
/spec-from-pdf ~/Downloads/알림-설정-스펙.pdf
```

이 명령 하나가 PDF 를 파싱하고, 피처를 구조화하고, 6개 카테고리(에러/빈 상태/오프라인/권한/로딩/접근성) 누락을 자동 체크하고, **프로젝트 컨텍스트 기반 개발 기간·타팀 의존성·기획 누락 포인트를 제안** 한 뒤, iOS/Android 노트를 공유할 Notion 페이지까지 만들어줍니다.

### 이런 분들께 유용합니다

- 기획 PDF → Notion 옮기는 작업이 반복적이고 귀찮을 때
- "다 구현했는데 에러/빈 상태 처리 안 했네..." 구현 말미에 터지는 경우가 잦을 때
- iOS 와 Android 가 **같은 페이지** 에서 플랫폼 노트를 공유하고 싶을 때
- 새 피처 착수 전 **개발 기간/타팀 의존성** 을 빠르게 정리하고 싶을 때

### 이런 경우엔 안 쓰셔도 됩니다

- Notion 에 스펙을 두지 않을 계획
- 1-2 문장짜리 초간단 피처 (플러그인 오버헤드가 더 큽니다)
- 민감 개인정보가 포함된 PDF (PII 스캔은 경고만 하고 차단은 안 하니 조심)

---

## 왜 만들었나

### 반복되는 세 가지 문제

**1. 같은 PDF 를 두 번 읽기.** 기획자가 `알림-설정-v3.pdf` 를 공유방에 올리면 iOS 가 한 번, Android 가 한 번 열어 본다. 각자 Notion/Slack 에 해석을 남긴다. "누가 먼저 정리하느냐" 가 암묵적 책임이 되고, **해석이 어긋나면 구현 단계에서야 발견** 된다.

**2. 엣지케이스를 구현 말미에 발견.** "에러 케이스 / 빈 상태 / 오프라인 / 권한 / 로딩 / 접근성" 여섯 가지는 거의 매번 빠진다. PR 리뷰에서 "이 케이스 어떡해요?" 가 터지면 그때부터 기획자·디자이너와 협의가 시작된다. **선택 항목이 아니라 체크리스트** 여야 한다.

**3. 개발 기간 추정이 암묵지.** "이 피처 얼마 걸려요?" 질문에 2년차는 감으로 2일, 5년차는 감으로 5일을 답한다. 과거에 비슷한 피처를 얼마나 걸렸는지는 아무도 기록하지 않는다. **신규 팀원은 추정을 감당 못하고, 기획자는 기간을 받을 근거가 없다.**

### 이 플러그인이 다루는 부분

- PDF → Notion 한 페이지로 **집중점(single source of truth)** 만들기
- Phase 3 에서 6개 엣지케이스 **자동 체크** (설정으로 팀 규칙 추가 가능)
- Phase 3.5 (v0.4+) 에서 **`project-context.md` 와 실제 코드베이스를 참고해** 피처별 예상 기간·타팀 의존성·기획 누락·타팀 요청사항을 자동 제안
- iOS / Android / 공통 노트가 **같은 페이지** 에 공존, 재실행해도 상대방 노트를 덮어쓰지 않음

### 이 플러그인이 다루지 않는 부분

- 기획 품질 자체를 개선해주지는 않음 (누락 체크만 함)
- 개발 기간 추정은 **힌트** — 팀 리더가 최종 조정해야 함
- 기존 앱과의 중복/충돌 자동 탐지는 v0.5+

---

## 처음 설치

### A. 팀 리드가 한 번만 해주세요

1. **Notion 부모 페이지 준비.** 팀 워크스페이스에 "피처 스펙" 같은 빈 페이지 하나.
2. **플러그인 등록.** Claude Code `/plugin` 명령으로 이 레포 경로를 등록.
3. **Notion 셋업.** 아무 PDF 로 `/spec-from-pdf <pdf>` 를 한 번 실행 → 플러그인이 "부모 페이지 URL" 을 요청하면 붙여넣기 → 피처 DB 가 자동 생성되고 config JSON 이 출력됨.
4. **config 를 팀 레포에 커밋.** 출력된 JSON 을 프로젝트 레포 루트의 `yeoboya-workflow.config.json` 에 저장:

   ```json
   {
     "pdf_spec_organizer": {
       "notion_database_id": "<자동 생성됨>",
       "notion_data_source_id": "<자동 생성됨>",
       "parent_page_id": "<부모 페이지 ID>"
     }
   }
   ```

5. **(선택) 프로젝트 컨텍스트 셋업** — 아래 "B. 팀원 설치" 3번 참고.

이후 팀원 누구나 같은 레포에서 플러그인을 쓰면 **같은 Notion DB** 를 바라보게 됩니다.

### B. 팀원 설치

#### 1. 사전 준비

| 의존성 | 언제/어디서 쓰이나 | 필수? | 설치/설정 |
|---|---|---|---|
| **Notion MCP** | Phase 5 — 피처 스펙을 Notion 피처 DB 페이지로 퍼블리시·병합 | 필수 | Claude Code 에 Notion MCP 연결 + Notion 설정 → Connections → Claude 추가 |
| **Tesseract** | Phase 1 — 이미지 기반 PDF 의 OCR 텍스트 추출 | 필수 | `brew install tesseract tesseract-lang` |
| **Superpowers 플러그인** | 이 플러그인에 **새 기능을 추가/유지보수** 할 때 (아래 스킬 표 참고) | 선택 (기여자용) | Claude Code `/plugin` 으로 `superpowers` 레포 등록 |

**Superpowers 에서 쓰는 스킬 (기여자용):**

| 스킬 | 언제 쓰나 | 한 줄 요약 |
|---|---|---|
| `superpowers:brainstorming` | 아이디어 → 설계 | 한 번에 한 질문씩, 2-3 approach 비교 후 `docs/superpowers/specs/` 에 design doc 커밋 |
| `superpowers:writing-plans` | 스펙 → 구현 플랜 | Commit 단위로 쪼개고, 각 Commit 을 2-5분짜리 task 로 분해 (TDD 단계 명시) |
| `superpowers:subagent-driven-development` | 플랜 → 실제 코드 | 각 Commit 을 fresh subagent 로 dispatch, 끝나면 spec + code quality 2중 리뷰 |
| `superpowers:test-driven-development` | 각 task 내부 | 실패 테스트 먼저 → 구현 → 테스트 통과 → commit 사이클 강제 |
| `superpowers:finishing-a-development-branch` | 구현 완료 후 | 최종 검증 + merge/PR/keep/discard 4개 옵션 |

#### 2. 플러그인 로드

Claude Code 에서 `/plugin` 으로 이 레포를 등록하거나, `~/.claude/settings.json` 에 경로 추가:

```json
{
  "plugins": {
    "paths": ["/path/to/yeoboya-workflow"]
  }
}
```

재시작 후 `/spec-from-pdf`, `/spec-update`, `/spec-resume` 가 뜨면 OK.

### C. (선택) 프로젝트 컨텍스트 셋업 — v0.4+

**Phase 3.5 "피처 메타 정보 생성"** 을 활성화하려면 팀이 1회 `project-context.md` 를 작성해서 레포에 커밋합니다. 설정이 없으면 이 기능은 조용히 스킵되고 v0.3 과 동일하게 동작합니다.

1. **템플릿 복사** (`docs/` 가 없으면 먼저 생성):
   ```bash
   mkdir -p docs && cp skills/pdf-spec-organizer/references/project-context-template.md docs/project-context.md
   ```

2. **내용 채우기.** 팀 구성 / 과거 개발 기간 사례 / 타팀 채널 / 제약 조건 등. 자유 마크다운. 500 줄을 넘으면 앞 500 줄만 사용됩니다.

3. **config 확장.** 기존 `pdf_spec_organizer` 객체에 두 키(`project_context_path`, `codebase_roots`) 를 **추가** — 기존 Notion 키는 유지:

   ```json
   {
     "pdf_spec_organizer": {
       "notion_database_id": "<your-feature-db-id>",
       "notion_data_source_id": "<your-data-source-id>",
       "parent_page_id": "<your-parent-page-id>",
       "project_context_path": "./docs/project-context.md",
       "codebase_roots": {
         "ios": "~/repos/myapp-ios",
         "android": "~/repos/myapp-android"
       }
     }
   }
   ```

4. `codebase_roots` 는 **선택** — 있으면 Claude 가 `Explore` subagent 로 실제 앱 레포를 자연어 탐색해 기간 추정 신뢰도를 높입니다. 없으면 project-context 만 참고합니다.

---

## 일상 사용법

### 워크플로우 단계 (한눈에 보기)

1. **PDF 받기.** 기획자가 공유한 스펙 PDF 를 로컬에 저장.
2. **커맨드 실행.** 프로젝트 레포에서 `/spec-from-pdf <pdf-path>` 입력.
3. **피처 구조 확인.** 파싱/구조화 결과를 검토, 필요시 경계 조정 (`y`/`s`/`m`/`r`).
4. **누락 체크 리뷰.** 6개 카테고리 (에러/빈 상태/오프라인/권한/로딩/접근성) 자동 리포트 확인 — v0.4+ 는 Phase 3.5 에서 예상 기간·타팀 의존성도 같이 제안.
5. **개발자 노트 작성.** 에디터에서 **자기 플랫폼 섹션만** 편집 후 저장.
6. **Notion 퍼블리시 & 공유.** 페이지 URL 을 팀 Slack 에 공유.
7. **반대편 플랫폼.** 상대 플랫폼 개발자는 같은 URL 로 `/spec-update <url>` — **같은 페이지에 노트 공존**.

### PDF 스펙 정리 (가장 자주 쓰는 명령)

```
/spec-from-pdf ~/Downloads/알림-설정-스펙.pdf
```

6-8 Phase 가 대화식으로 진행되고, 3-5분 정도 걸립니다.

| Phase | 무엇을 | 사용자 입력 |
|---|---|---|
| 1. 파싱 | PDF 텍스트+이미지 추출, OCR, PII 스캔 | 자동 |
| 2. 구조화 | 피처 N개로 분류, iOS/Android/공통 태깅 | `y`/`s`/`m`/`r`/`t`/`e`/`c` |
| 2-6. 웹 필터 | 웹 전용 피처 제외 (선택) | 번호 입력 |
| 3. 누락 체크 | 6개 카테고리 자동 검토 | 자동 |
| **3.5. 메타 생성** | **v0.4+ — 예상 기간/타팀 의존성/기획 누락/타팀 요청** | 요약 확인 |
| 4. 개발자 노트 | 플랫폼별 노트 작성 | 에디터 편집 |
| 5. 퍼블리시 | Notion 페이지 생성/병합 | 충돌 시 선택 |

**`--fast` 플래그**: 피처 경계·충돌 기본값을 자동 통과. 플랫폼 태깅·개발자 노트는 여전히 명시 확인.

```
/spec-from-pdf ~/Downloads/알림.pdf --fast
```

### 기존 페이지에 노트만 추가

```
/spec-update https://www.notion.so/workspace/알림-설정-abc123
```

Phase 4 (노트 편집) → Phase 5 (병합 퍼블리시) 만 실행. iOS/Android 개발자가 서로의 노트를 건드리지 않고 **자기 플랫폼 섹션만** 추가할 수 있습니다.

특정 피처만 편집하려면:
```
/spec-update <page-url> --feature="알림 설정"
```

### 중단된 세션 이어받기

네트워크 문제나 Ctrl-C 등으로 중단됐을 때:

```
/spec-resume --resume-latest                    # 가장 최근 세션
/spec-resume /tmp/spec-draft-abc123-1700000000/draft.md
```

초안에 저장된 `phase` 상태에서 이어집니다. Phase 5 도중 부분 실패한 chunk append 도 재개 가능.

---

## 팀 협업 시나리오

### 시나리오 A — 기획 PDF 최초 정리

1. **iOS 개발자** 가 `/spec-from-pdf 알림-설정.pdf` 실행
2. 피처 "알림 설정" 생성, iOS 노트 작성 → Notion 페이지 생성
3. Slack 에 Notion URL 공유
4. **Android 개발자** 가 같은 URL 로 `/spec-update <url>` 실행 (또는 같은 PDF 로 `/spec-from-pdf` 재실행)
5. Android 섹션만 추가 → 한 페이지에 **iOS + Android 노트 공존**

### 시나리오 B — 구현 중 엣지케이스 보강

1. 개발 도중 새 엣지케이스 발견
2. `/spec-update <page-url> --feature="알림 설정"` → 해당 Toggle 블록만 에디터에서 열림
3. 본인 플랫폼 섹션에 노트 추가 → 저장 → Notion 에 병합 반영

### 시나리오 C — 기획자와의 기간 협상 (v0.4+)

1. `project-context.md` 에 "신규 플로우(2-3화면+API): iOS 3-5일, Android 3-5일" 같은 과거 사례 기록
2. `/spec-from-pdf 신규-기획.pdf` → Phase 3.5 에서 피처별 예상 기간·타팀 의존성·기획 누락이 자동 제안
3. Phase 4 에디터에서 팀 리더가 검토/수정 → Notion 페이지 본문에 "📊 개발 계획 메타" 블록으로 퍼블리시
4. 기획자·PM 이 Notion 페이지 하나로 기간/의존성 확인

---

## 커맨드 레퍼런스

| 커맨드 | 용도 | 주요 옵션 |
|---|---|---|
| `/spec-from-pdf <path>` | PDF → Notion 페이지 생성/병합 | `--fast`, `--diff-with-code` (v0.5+) |
| `/spec-update <url>` | 기존 페이지의 노트 갱신 | `--feature="<이름>"` |
| `/spec-resume` | 중단된 세션 복구 | `--resume-latest`, `<draft-path>` |

자세한 동작은 [`skills/pdf-spec-organizer/SKILL.md`](skills/pdf-spec-organizer/SKILL.md) 참조.

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `❌ 팀 공유 설정 파일이 없습니다` | `yeoboya-workflow.config.json` 없음 | 팀 리드가 위 "A. 팀 리드" 절차로 생성 후 커밋 |
| `tesseract not found` | Tesseract 미설치 | `brew install tesseract tesseract-lang` |
| Notion 페이지 생성 실패 (404) | MCP 에 워크스페이스 접근 권한 없음 | Notion 설정 → Connections → Claude 추가 |
| OCR 텍스트 깨짐 | 언어 팩 부재 | `brew install tesseract-lang` |
| PII 경고가 계속 뜸 | 실제 민감 정보가 PDF 에 존재 | 마스킹된 항목 확인 후 진행 또는 PDF 정리 후 재시도 |
| Phase 3.5 스킵됨 | `project_context_path` 미설정 | 위 "C. 프로젝트 컨텍스트 셋업" 참고 (또는 그대로 v0.3 동작 사용) |
| `/spec-update` 시 특정 피처를 못 찾음 | 피처명 오타 또는 공백/괄호 정확히 일치 안 함 | `--feature="정확한 이름 (A/B)"` 따옴표 포함 전체 이름 전달 |

---

## 알려진 제약

- **이미지 업로드**: Notion MCP 파일 업로드 제약으로 로컬 이미지는 placeholder 로 표시될 수 있음 (향후 개선 예정)
- **OCR 품질**: 이미지 전용 페이지는 Tesseract 품질이 낮을 수 있음 — 개발자 노트에서 보완
- **v0.4 wrong-schema JSON**: Claude 메타 응답이 잘못된 타입으로 오면 경고 없이 빈 값으로 치환됨 (v0.4.1 개선 예정)
- **`/spec-update` 3-way merge**: 동시 편집 충돌 감지가 `meta` 섹션을 커버하지 않음 (v0.4.1 개선 예정)

---

## 어떻게 만들어졌나 — Superpowers 활용

**이 플러그인 자체가 Claude Code + `superpowers` 플러그인 만으로 개발됐습니다.** 코드를 손으로 타이핑한 줄 수는 매우 적고, 대부분이 브레인스토밍 → 스펙 → 플랜 → 서브에이전트 구현 → 두 단계 리뷰 사이클의 결과입니다. 같은 방식으로 다음 기능을 추가하고 싶은 팀원이 참고할 수 있도록 개발 흐름을 기록해둡니다.

### 사용한 superpowers skills

| Skill | 언제 | 무엇을 |
|---|---|---|
| `superpowers:brainstorming` | 아이디어 → 설계 | 한 번에 한 질문씩, 2-3 approach 비교, 승인 후 `docs/superpowers/specs/` 에 design doc 커밋 |
| `superpowers:writing-plans` | 스펙 → 구현 플랜 | Commit 단위로 쪼개고, 각 Commit 을 2-5분짜리 task 로 분해. TDD 단계 명시 |
| `superpowers:subagent-driven-development` | 플랜 → 실제 코드 | 각 Commit 을 **fresh subagent** 로 dispatch, 끝나면 **spec 리뷰 + code quality 리뷰** 두 번 |
| `superpowers:test-driven-development` | 각 task 내부 | 실패 테스트 먼저 → 구현 → 테스트 통과 → commit 사이클 강제 |
| `superpowers:finishing-a-development-branch` | 구현 완료 후 | pytest 최종 검증, merge/PR/keep/discard 4개 옵션 중 선택 |

### v0.4.0 실제 개발 흐름

```
사용자 아이디어
   │
   ▼
[brainstorming skill]
   │  · 한 번에 한 질문씩: "프로젝트" 가 뭔가요? → iOS/Android 코드베이스
   │  · 2-3 approach 비교: Notion DB 비교 vs 코드베이스 비교 vs 둘 다
   │  · 중간에 Plan agent 로 독립 아키텍트 리뷰 받음
   │  · 사용자 "꼬인다" 피드백 → 원점 복귀 → 재정의 (codebase-diff-filter → feature-enrichment)
   │  · 최종 spec: docs/superpowers/specs/2026-04-21-feature-enrichment-design.md
   │
   ▼
[writing-plans skill]
   │  · 8 commits × 32 tasks 로 분해
   │  · 각 task 에 "test 작성 → fail 확인 → 구현 → pass 확인 → commit"
   │  · docs/superpowers/plans/2026-04-21-feature-enrichment.md
   │
   ▼
[subagent-driven-development skill]
   │  ┌─────────────────────────────────────────┐
   │  │ Task 별 반복                              │
   │  │  1. implementer subagent dispatch         │
   │  │  2. spec compliance reviewer              │
   │  │  3. code quality reviewer (superpowers:   │
   │  │     code-reviewer agent)                  │
   │  │  4. 이슈 나오면 fix subagent → 재리뷰       │
   │  └─────────────────────────────────────────┘
   │
   ▼
[finishing-a-development-branch skill]
   │  · pytest 59/59 green 확인
   │  · 4 옵션 중 "push to origin/main" 선택
   │  · fast-forward push
   ▼
   v0.4.0 배포 완료
```

### 이 흐름에서 실제로 얻은 것

- **사용자 요구 오해가 brainstorming 중에 드러났습니다.** 초안 "이미 구현된 피처 제외" 로 spec 까지 썼는데, 사용자가 "꼬인다" 고 말씀해서 원점 복귀 → "피처 메타 정보 자동 제안" 으로 완전히 재정의. **코드 없이** 설계만 버리면 되어서 비용이 작았습니다.
- **Plan-level 오프바이원 버그를 implementer 가 잡아냈습니다.** 테스트 `range(1000)` 과 구현 `[:500]` 조합이 맞지 않았는데, subagent 가 구현 전에 발견하고 BLOCKED 리포트 → controller 가 test fix 지시 → 진행.
- **Critical runtime 버그 3건이 code-quality 리뷰어 덕분에 잡혔습니다.**
  - `CONFIG_PATH="${WORK_DIR}/.."` 가 `/tmp` 로 해석되는 문제
  - `project_context_path` 상대경로가 cwd 기준으로 풀리는 문제 (spec 은 config 기준)
  - `"공통"` 플랫폼 문자열이 dispatch 규칙에서 누락되는 문제
- **최종 holistic 리뷰에서 Important 2건** 발견 (wrong-schema silent coercion, U-5 3-way meta) → v0.4.1 로 이월 (CHANGELOG + README "알려진 제약" 에 명시).

### 수치로 본 v0.4.0

| 항목 | 값 |
|---|---|
| 총 commit | 10 (7 feature + 3 fix) |
| 통과한 리뷰 게이트 | 7 Commit × 2 (spec + code quality) = 14회 |
| 수정 commit 필요했던 review | 3회 (NEEDS_CHANGES → fix → APPROVED) |
| pytest | 49 → **59 passed** (신규 10) |
| 신규/수정 파일 | 16 |
| 신규 insertions | ~3,370 lines (대부분 SKILL.md + spec/plan docs) |

### 같은 방식으로 기능을 추가하고 싶다면

```
/skill superpowers:brainstorming     # 아이디어부터
/skill superpowers:writing-plans     # 승인된 spec 을 플랜으로
/skill superpowers:subagent-driven-development   # 플랜 실행
/skill superpowers:finishing-a-development-branch   # 마무리
```

각 스킬이 다음 스킬로 자연스럽게 이어집니다. 중간에 설계가 흔들리면 brainstorming 으로 돌아가도 됩니다 — 저희가 v0.4.0 개발 중에 한 번 그렇게 했습니다.

---

## 더 알아보기

- **최근 변경**: [`CHANGELOG.md`](CHANGELOG.md)
- **스킬 내부 동작**: [`skills/pdf-spec-organizer/SKILL.md`](skills/pdf-spec-organizer/SKILL.md)
- **설계 스펙**: [`docs/superpowers/specs/`](docs/superpowers/specs/)
- **구현 플랜**: [`docs/superpowers/plans/`](docs/superpowers/plans/)
- **수동 QA 체크리스트**: [`docs/manual-qa.md`](docs/manual-qa.md)
- **기여 가이드**: 새 워크플로우를 쌓으려면 `skills/<new-feature>/` + `commands/<new-feature>.md` 형태로 추가. 기존 `pdf-spec-organizer` 파일은 건드리지 마세요.

---

## 로드맵

**v0.4.1 (가까운 개선):**
- Claude 메타 응답 스키마 검증 강화
- `/spec-update` 3-way merge 에 meta 섹션 포함

**v0.5+ (고려 중):**
- 기존 Notion 피처 DB 와의 중복/충돌 자동 탐지
- 코드베이스 매칭 심화 (Explore subagent 캐싱, thoroughness 동적 조절)
- PDF 외 입력 (`/spec-from-notion`, `/spec-from-figma`)
- 팀명/기간 표준화, 메타 이력 보존

문의: 팀 Slack `#yeoboya-workflow` 채널 또는 PR 환영합니다.
