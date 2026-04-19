# pdf-spec-organizer Skill Refactor 설계

- 작성일: 2026-04-19
- 대상 스킬: `skills/pdf-spec-organizer/`
- 스킬 버전: v0.1.0 → 개선판
- 상태: Draft (사용자 검토 대기)

## 배경

`pdf-spec-organizer` 스킬이 v0.1.0 으로 출시된 후 `skill-creator` 관점으로 리뷰를 받았다. 구조(progressive disclosure, references, scripts)는 모범 사례를 잘 따르지만 **description 과 작성 스타일**에서 개선 여지가 발견됨:

- **Description** 이 "무엇을 하나" 중심이고 "언제 트리거하나" 신호가 약함 → 자연어 호출 시 undertrigger 가능성
- **SKILL.md 479줄** 로 권장 500줄 한계 근접
- **Why 주석 부재** 로 LLM 이 규칙의 의도를 파악하기 어려워 엣지케이스 판단 약함
- **Trigger accuracy 정량 지표 없음** — description 최적화를 체계적으로 할 근거 부족

## 목표

- 자연어 호출 시에도 스킬이 안정적으로 트리거되도록 description 개선
- SKILL.md 길이 감축 (Phase 5 축약)
- Precondition + 각 Phase 에 "Why" 주석 추가하여 LLM 의도 이해도 향상
- `run_loop.py` 로 description 자동 최적화를 돌릴 수 있는 eval set 셋업

## 비목표

- 스킬의 워크플로우 로직 자체는 변경하지 않음
- references/source-of-truth.md (v2 확장 포인트) 는 손대지 않음
- Python 스크립트 변경 없음

## 변경 대상 파일

```
yeoboya-work-flow/
├── skills/pdf-spec-organizer/
│   ├── SKILL.md                         # 수정 (description, Phase 5 축약, Why 주석)
│   └── references/
│       └── conflict-policy.md           # 확장 (Phase 5 이동분 흡수)
└── evals/                               # 신규
    └── trigger-eval.json                # 20 개 eval queries
```

## 커밋 전략 (논리 단위 3개)

1. **skill refactor** — description 재작성 + Phase 5 축약 + conflict-policy.md 확장
2. **skill annotations** — Precondition + Phase 별 "Why" 주석 추가
3. **trigger eval setup** — evals/trigger-eval.json + README 에 run_loop.py 가이드 추가

## 상세 변경 내용

### 1. Description 재작성 (SKILL.md frontmatter)

**현재:**
```
복합 PDF 스펙(PRD+디자인+플로우)을 파싱해 Notion 피처 DB 페이지로 정리한다. 명세 누락 체크 + iOS/Android 플랫폼별 개발자 노트 공유. /spec-from-pdf, /spec-update, /spec-resume 커맨드의 실제 로직.
```

**개정:**
```
기획자/PM 에게 받은 PDF 스펙(PRD, 디자인 시안, 유저 플로우) 을 Notion 피처 DB 페이지로 정리한다. 명세 누락 (에러/빈상태/오프라인/권한/로딩/접근성) 을 자동 체크하고 iOS/Android 팀이 같은 페이지에서 플랫폼별 개발자 노트를 공유하도록 구조화한다. 사용자가 "이 PDF 정리해줘", "기획서 스펙 정리", "피처 스펙 노션에 올려줘", "개발자 노트 정리" 같은 요청을 하거나 기획 PDF 문서를 언급할 때 반드시 이 스킬을 사용할 것. 슬래시 커맨드 `/spec-from-pdf`, `/spec-update`, `/spec-resume` 의 실제 구현 로직.
```

**변경 의도:**
- 사용자 실제 어휘 5개 추가 ("이 PDF 정리해줘" 등) — 자연어 트리거 범위 확대
- 체크 항목 6종 명시 — 키워드 검색 가능성 ↑
- "반드시 이 스킬을 사용할 것" — skill-creator 의 "pushy" 원칙 적용
- "기획자/PM" — 회사별 용어 다양성 커버
- 슬래시 커맨드는 마지막 문장으로 이동 — 자연어 트리거가 주, 커맨드가 보조

### 2. Phase 5 축약 (SKILL.md)

**현재 (~95줄):**
- 5-1 DB ID / 5-2 피처 루프 (a-d) / 5-3 실행 기록 / 5-4 결과 / 5-5 GC

**개정 후 (~45줄):**

```markdown
## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

**왜:** iOS/Android 가 따로 같은 PDF 를 돌릴 수 있음. 병합 기본값으로 타 플랫폼 노트를 실수로 지우는 상황 방지.

### 5-1. DB ID 확보
Precondition 2 에서 읽은 `notion_database_id` 사용. 존재 가정.

### 5-2. 피처별 루프
각 피처마다:
1. `mcp__claude_ai_Notion__notion-search` 로 DB 안에서 동명 피처 조회
2. 존재 → `references/conflict-policy.md` 의 **"Phase 5 충돌 처리"** 섹션 따르기
3. 없음 → `mcp__claude_ai_Notion__notion-create-pages` 로 새 페이지 생성 (속성 + 본문 블록)
4. 이미지 → `references/conflict-policy.md` 의 **"이미지 업로드 전략"** 섹션 따르기

### 5-3. 실행 기록 갱신
모든 피처 성공 → `draft_registry update-status --status success`
부분 실패 → `status failed` + 실패 피처 목록 + `/spec-resume --resume-latest` 가이드 출력

### 5-4. 결과 요약
성공 페이지 URL 리스트 출력, 초안 3일 후 자동 삭제 안내

### 5-5. GC 트리거
성공 시만 `draft_registry gc` 실행 (기회적 청소)
```

### 3. `conflict-policy.md` 확장

`references/conflict-policy.md` 에 **두 섹션 추가**:

#### "Phase 5 충돌 처리" 섹션 (현재 SKILL.md 의 5-2-b 내용)
- 프롬프트 예시 (제목/생성자/생성일/해시 표시)
- `[1] 병합(기본) / [2] 덮어쓰기 / [3] 새 버전 / [4] 건너뛰기`
- `--fast` 동작 (병합만 자동, 나머지는 프롬프트)
- 각 옵션의 구체 실행 (notion-fetch/update-page/create-pages + Relation)

#### "이미지 업로드 전략" 섹션 (현재 SKILL.md 의 5-2-d 내용)
- Notion MCP 의 로컬 이미지 업로드 지원 여부 점검
- 1차 fallback: placeholder URL + 로컬 경로 캡션
- 2차 계획 (v0.2): S3/imgur 중계 업로더

### 4. Why 주석 추가 (SKILL.md)

각 섹션 제목 직후 `**왜:** 한두 문장` 형식으로 삽입.

**Precondition 4개:**
- 1 인자 확인: PDF 경로 없으면 이후 Phase 전체 실패, 진입점에서 차단해 /tmp 낭비 방지
- 2 팀 설정: 팀원 각자 다른 DB 쓰면 iOS/Android 못 봄. 레포 커밋된 설정이 단일 DB 보장
- 3 Python 의존성: 후속 스크립트 모두 import 사용, 중간 실패 시 초안 일관성 깨짐
- 4 Tesseract: 이미지 PDF 에서만 필요, 텍스트 PDF 는 정상 동작하므로 경고만

**Phase 5개:**
- Phase 1 (파싱): 후속 Phase 가 모두 파싱 결과를 읽음. 이미지/OCR/PII 한 번에 처리
- Phase 2 (구조화): Claude 추정이라 실수 가능, 개발자 검증 필수
- Phase 3 (누락 체크): 기획서가 엣지케이스 빠뜨리는 건 현실적, 표준 체크리스트로 사전 발견
- Phase 4 (노트): 기술 판단은 Claude 가 대신 못함, 스킬 핵심 가치
- Phase 5 (퍼블리시): 동시 실행 시 타 플랫폼 노트 보호

**길이 영향:**
- Phase 5 축약: –50줄
- Why 주석 추가: +25줄
- 순감소: 약 –25줄 → SKILL.md 454줄 (500줄 한계 안정적 유지)

### 5. Trigger Eval Queries (`evals/trigger-eval.json`)

skill-creator 표준 포맷, **총 20 개 (should-trigger 10 + should-not-trigger 10)**.

**should-trigger 10 카테고리:**
1. 슬래시 커맨드 — 명시적
2. 자연어 — 기본
3. 축약 용어 — "PM이 준 피처 스펙"
4. 영어 섞임 — "PRD 문서 spec 페이지"
5. 체크리스트 강조 — "에러 케이스랑 접근성 누락"
6. 플랫폼 노트 — "iOS랑 Android 같이 볼 수 있게"
7. 캐주얼 — "이거 받은 기획서인데 정리 좀"
8. 업데이트 — "기존 노션 페이지에 Android 노트 추가"
9. 파일 드롭 — 경로만 제시
10. 팀 협업 맥락 — "iOS 개발자가 먼저 올려놨는데..."

**should-not-trigger 10 카테고리 (near-miss):**
1. 일반 PDF 요약 — 스펙 아님
2. API 스펙 (OpenAPI 문서화)
3. 단순 Notion 쓰기 (PDF 없음)
4. 타 플랫폼 — Confluence 업로드
5. 스크린샷 OCR
6. PDF → 슬라이드
7. PDF 번역
8. 개인 문서 (여권)
9. 다른 체크리스트 — 코드 리뷰
10. iOS 구현 — 스펙 정리 아님

**파일 포맷:**
```json
[
  {"query": "전체 프롬프트 텍스트", "should_trigger": true},
  {"query": "...", "should_trigger": false}
]
```

### 6. README 업데이트 (run_loop.py 가이드)

`README.md` 의 "개발 / 확장" 섹션에 추가:

```markdown
### Description 최적화 실행

skill-creator 의 `run_loop.py` 로 description 을 자동 튜닝할 수 있다.

```bash
# skill-creator 디렉토리에서 (gstack 플러그인 캐시 경로 예시):
cd ~/.claude/plugins/cache/skill-creator/unknown/skills/skill-creator

python -m scripts.run_loop \
  --eval-set /Users/chuchu/testPlugin/evals/trigger-eval.json \
  --skill-path /Users/chuchu/testPlugin/skills/pdf-spec-organizer \
  --model claude-opus-4-7 \
  --max-iterations 5 \
  --verbose
```

결과는 HTML 리포트로 열림. 제안된 `best_description` 을 `SKILL.md` frontmatter 에 반영.
\```
```

## 검증 기준

- SKILL.md 가 500줄 이내 유지
- 기존 테스트 (pytest) 모두 계속 통과 (스크립트 로직 변경 없음)
- 수동: 샘플 PDF 로 드라이런 1회 → 기존 동작과 동일
- `run_loop.py` 실행 시 에러 없이 eval-set 읽고 진행 (사용자가 별도 실행)

## 오픈 이슈

- run_loop.py 실행은 **이번 세션 범위 밖** — eval-set 만 작성, 실제 실행은 사용자 판단
- 개정된 description 이 실제로 자연어 트리거를 개선하는지 검증은 run_loop.py 결과에 맡김
- Eval query 내용은 회사 도메인 어휘가 제한적 (개인 프로젝트라 다양성 한계). 실사용 후 추가 query 수집 필요
