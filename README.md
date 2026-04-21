# yeoboya-workflow

여보야 회사 워크플로우를 자동화하는 Claude Code 플러그인.
iOS/Android 팀이 기획 문서를 받아서 스펙을 정리하고, 공유하고, 놓친 엣지케이스를 찾아내는 데 사용한다.

**상태:** v0.1.0 — `pdf-spec-organizer` 기능 이용 가능

---

## 언제 쓰나?

### 이럴 때 쓰세요

- 기획자가 PDF 로 스펙을 전달했는데, iOS/Android 팀이 각자 읽고 해석해서 구현 단계에서야 엣지케이스가 발견되는 상황
- 스펙 PDF 를 한 번은 정리해서 Notion 에 올려야 하는데, 매번 수작업으로 옮기기 귀찮을 때
- "에러 케이스 / 빈 상태 / 오프라인 처리 / 권한 / 로딩 / 접근성" 같은 표준 체크리스트를 놓치지 않고 검토하고 싶을 때
- 같은 피처에 대해 iOS 와 Android 개발자가 각자 기술 노트를 **같은 페이지**에 남기고 싶을 때

### 안 쓰시는 게 나은 경우

- Notion 에 스펙을 둘 계획이 없을 때 (이 플러그인은 Notion 퍼블리시가 기본)
- 1-2 문장 수준의 간단한 피처 (플러그인 오버헤드가 더 큼)
- 민감한 개인정보가 포함된 PDF (PII 스캔은 경고만 하고 차단은 안 함 — 조심)

---

## 무엇을 하나?

### 핵심 기능: `pdf-spec-organizer`

**PDF 1개 → Notion 피처 DB 페이지들** 로 정리하는 5단계 대화형 워크플로우.

```
PDF ──▶ 파싱 ──▶ 구조화 ──▶ 누락 체크 ──▶ 개발자 노트 ──▶ Notion 퍼블리시
        (자동)   (개입①)     (자동)       (개입②)        (개입③)
```

각 개입 단계에서 사용자가 결과를 검토하고 수정할 수 있다. Notion 에 반영되기 전까지 부작용 없음 (취소 시 아무것도 생성 안 됨).

### 플랜별 기능 요약

| 기능 | 무엇을 | 어떤 커맨드 |
|---|---|---|
| 새 스펙 정리 | PDF → Notion 피처 페이지 | `/spec-from-pdf` |
| 노트 갱신 | 기존 페이지 노트/체크 수정 | `/spec-update` |
| 중단 복구 | 실패한 세션 이어받기 | `/spec-resume` |
| 명세 누락 체크 | 에러/빈/오프라인/권한/로딩/접근성 자동 검토 | Phase 3 에서 자동 |
| 플랫폼 노트 | iOS/Android/공통 섹션 분리 유지 | Phase 4 에서 입력 |
| 병합 기본 충돌 처리 | 동일 피처 재실행 시 타 플랫폼 노트 보존 | Phase 5 에서 자동 |
| 동시 실행 감지 | 5분 내 같은 PDF 다른 실행 경고 | Phase 1 에서 자동 |
| PII 경고 | email/전화/주민번호 자동 감지 후 마스킹 | Phase 1 에서 자동 |
| OCR fallback | 이미지 기반 PDF 에서 텍스트 추출 | Phase 1 에서 자동 |

---

## 빠른 시작

> **경로 표기 안내:** 이 문서에서 `<플러그인-루트>` 는 `git clone` 으로 받은 이 레포의 로컬 경로 (예: `~/projects/yeoboya-workflow`) 를 의미합니다.

### 1. 사전 준비

- **Python 3.11+**
- **Tesseract** (OCR fallback용):
  ```bash
  brew install tesseract tesseract-lang   # macOS
  ```
- **Notion MCP** 가 Claude Code 에 연결되어 있고, 쓰려는 워크스페이스에 접근 권한이 있어야 함

### 2. 플러그인 로드

Claude Code 에서 `/plugin` 명령으로 이 디렉토리를 플러그인으로 등록하거나, `~/.claude/settings.json` 에 경로 추가:

```json
{
  "plugins": {
    "paths": ["/path/to/yeoboya-workflow"]
  }
}
```

Claude Code 재시작 후 `/spec-from-pdf`, `/spec-update`, `/spec-resume` 커맨드가 등장하면 성공.

### 3. Python 의존성 설치

플러그인 디렉토리에서:

```bash
cd /path/to/yeoboya-workflow/skills/pdf-spec-organizer/scripts
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> `.venv/` 는 플러그인 레포 내부에 격리되며 `.gitignore` 처리된다.

### 4. 팀 리드: 최초 Notion 셋업

팀 리드가 한 번만 해주세요 (이후 팀원들은 이 단계 생략 가능):

1. Notion 에서 스펙을 모아둘 **부모 페이지** 하나 준비 (예: "피처 스펙")
2. `/spec-from-pdf <어떤 PDF든>` 첫 실행
3. 플러그인이 "부모 페이지 URL 을 입력하세요" 요청 → 붙여넣기
4. 플러그인이 **피처 DB 자동 생성** + `yeoboya-workflow.config.json` 초안 출력
5. 그 JSON 을 **사용할 프로젝트 레포의 루트에 커밋**:

   ```json
   {
     "pdf_spec_organizer": {
       "notion_database_id": "<자동 생성된 DB ID>",
       "notion_data_source_id": "<자동 생성된 data source ID>",
       "parent_page_id": "<부모 페이지 ID>"
     }
   }
   ```

이제 팀원 누구나 같은 레포에서 플러그인 쓰면 **같은 Notion DB** 를 바라보게 된다.

### 5. 일상 사용

iOS/Android 개발자가 기획자에게 PDF 스펙 받으면:

```
/spec-from-pdf ~/Downloads/알림-설정-스펙.pdf
```

5개 Phase 가 대화식으로 진행됨. 3-5분 정도 소요.

---

## 프로젝트 컨텍스트 셋업 (v0.4+, 선택)

Phase 3.5 "피처 메타 정보 생성" 을 활성화하려면 팀이 1회 `project-context.md` 를 작성해서 레포에 커밋한다.

1. 템플릿 복사 (`docs/` 가 없으면 먼저 생성):
   ```bash
   mkdir -p docs && cp skills/pdf-spec-organizer/references/project-context-template.md docs/project-context.md
   ```
2. 팀 구성 / 과거 개발 기간 사례 / 타팀 채널 / 제약 조건 채우기. 자유 마크다운. 파일이 500 줄을 넘으면 앞 500 줄만 사용하고 경고가 출력됨.
3. `yeoboya-workflow.config.json` 의 기존 `pdf_spec_organizer` 객체에 아래 두 키(`project_context_path`, `codebase_roots`)를 **추가**한다. 기존 Notion 키는 유지:
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
4. `codebase_roots` 는 **선택**. 있으면 Claude 가 `Explore` subagent 로 레포를 자연어 탐색해 기간 추정 신뢰도를 높인다. 없으면 project-context 만으로 메타를 제안.

설정이 없으면 Phase 3.5 는 스킵되며 v0.3 과 동일하게 동작한다.

---

## 커맨드 레퍼런스

### `/spec-from-pdf <path> [--fast]`

메인 커맨드. PDF 를 Notion 피처 DB 페이지로 정리.

- `<path>` — PDF 파일 절대 경로 또는 `~/` 포함 경로
- `--fast` — 개입 ① (피처 경계) 와 ③ (충돌 처리 기본값) 자동 통과. 개입 ② (노트 작성) 는 여전히 강제

예:
```
/spec-from-pdf ~/Downloads/설정.pdf
/spec-from-pdf ~/Downloads/설정.pdf --fast
```

### `/spec-update <notion-url>`

기존 Notion 피처 페이지의 **노트/체크만** 갱신. Phase 4 (노트) + Phase 5 (병합) 만 실행.

예:
```
/spec-update https://www.notion.so/workspace/알림-설정-abc123
```

### `/spec-resume [--resume-latest | <draft-path>]`

중단된 세션 이어받기. 초안 md 의 `<!-- plugin-state -->` 헤더에서 phase 를 읽어 해당 Phase 부터 재개.

예:
```
/spec-resume --resume-latest                      # 가장 최근 running/failed 세션
/spec-resume /tmp/spec-draft-abc123-1700000000/draft.md
```

---

## 작동 방식 (5 Phase 상세)

### Phase 1 — 파싱 (자동)

- `scripts/parse_pdf.py` 로 텍스트 + 페이지별 이미지 추출
- 텍스트가 부족한 페이지는 `scripts/ocr_fallback.py` (Tesseract) 로 OCR
- `scripts/pii_scan.py` 로 email/전화/주민번호 감지 → 발견 시 경고 후 사용자 확인
- `scripts/draft_registry.py query-recent` 로 5분 내 동일 PDF 해시 실행 감지

### Phase 2 — 구조화 + 개입 ① (대화형)

- Claude 가 파싱 결과를 읽고 **피처 N개** 로 분류 + iOS/Android/공통 태깅
- 사용자가 확인: `y` (진행) / `s N` (쪼개기) / `m N,M` (합치기) / `r N` (리네이밍) / `t N` (플랫폼 변경) / `e` (에디터 편집) / `c` (취소)
- `--fast`: 피처 경계는 자동 통과, **플랫폼 태깅은 여전히 명시 확인**

### Phase 3 — 누락 체크 (자동)

- `config/pdf-spec-organizer/checklist.yaml` 로드 (실패 시 `default-checklist.json` fallback)
- 각 피처의 요구사항을 Claude 가 읽고 체크 항목별 "명시됨 / 누락" 판정
- 피처의 플랫폼과 체크 항목의 `applies_to` 교집합만 검토

### Phase 4 — 개발자 노트 + 미리보기 + 개입 ② (대화형)

- 구조화 결과 + 누락 체크를 `/tmp/spec-draft-<hash>-<ts>/draft.md` 로 렌더
- 본인 플랫폼의 "개발자 노트" 섹션을 `$EDITOR` 로 열어 작성
- 타 플랫폼 섹션은 비워둠 → 상대방이 나중에 `/spec-update` 로 채움
- `--fast` 에서도 이 단계는 **생략 불가** (인간 가치 투입 지점)

### Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

- `yeoboya-workflow.config.json` 의 `notion_data_source_id` 로 피처 DB 조회
- 동명 피처 존재 시:
  - **병합** (기본): 내 플랫폼 섹션만 append, 타 플랫폼 노트 보존
  - **덮어쓰기**: 전체 본문 교체 (파괴적, 추가 확인 필요)
  - **새 버전**: 새 페이지 생성 + `이전_버전` Relation 으로 이전 페이지 연결
  - **건너뛰기**: 이 피처만 스킵
- 없으면 새 페이지 생성 (속성 + 본문 블록)
- 성공 시 생성된 페이지 URL 출력

---

## 설정 커스터마이징

### `config/pdf-spec-organizer/checklist.yaml`

누락 체크 항목을 팀 규칙에 맞게 수정 가능:

```yaml
version: 1

items:
  - id: error_cases
    name: 에러 케이스
    description: 네트워크/서버 오류 발생 시 UX
    applies_to: [iOS, Android, 공통]
  # ... 추가 가능
```

- `applies_to` 에 명시된 플랫폼과 피처 플랫폼이 **교집합 없으면 스킵**
- 회사 규칙 추가 (예: "다국어 처리", "다크모드") 하려면 여기에 항목 추가

### `yeoboya-workflow.config.json` (프로젝트 레포에 커밋)

Notion DB 위치만 담는 단순 설정:

```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "<your-feature-db-id>",
    "notion_data_source_id": "<your-data-source-id>",
    "parent_page_id": "<your-parent-page-id>"
  }
}
```

(실제 값은 `yeoboya-workflow.config.json.example` 참고. 팀 리드가 최초 셋업 시 받은 ID 로 채우세요.)

---

## 팀 협업 시나리오

### 시나리오 A: 처음 받은 PDF

1. iOS 개발자가 `/spec-from-pdf 알림.pdf` 실행
2. 피처 "알림 설정" 생성, iOS 노트 작성 → Notion 퍼블리시
3. Slack 에 Notion URL 공유
4. Android 개발자가 **같은 PDF** 로 `/spec-from-pdf 알림.pdf` 다시 실행
5. Phase 5 에서 "동일 피처 존재, 기본값은 병합" 확인
6. Android 노트만 추가 → Notion 에 **iOS 노트 + Android 노트 공존**

### 시나리오 B: 후속 질문/보완

1. 구현 중 Android 개발자가 새 엣지케이스 발견
2. `/spec-update https://notion.so/알림-설정-abc123` 실행
3. Phase 4 로 바로 진입 → Android 섹션에 노트 추가
4. 병합 퍼블리시. iOS/공통 섹션 변화 없음

### 시나리오 C: 세션 중단 복구

1. Phase 3 에서 네트워크 문제로 Notion 조회 실패
2. 초안이 `/tmp/spec-draft-<hash>-<ts>/draft.md` 에 보존됨
3. 네트워크 복구 후 `/spec-resume --resume-latest`
4. Phase 4 부터 재개

---

## 알려진 제약

- **이미지 업로드**: Notion MCP 의 파일 업로드 제약으로 로컬 이미지가 Notion 에 직접 업로드되지 않을 수 있음. 현재는 placeholder 로 표시되며 v0.2 에서 S3/imgur 중계 계획
- **OCR 품질**: 이미지 전용 페이지는 Tesseract 결과 품질이 낮을 수 있음 — 개발자 노트에서 보완
- **충돌 체크 (v2)**: 기존 앱 코드나 기존 스펙 DB 와의 중복/충돌 감지는 v0.2 계획. v1 에서는 같은 이름 피처의 단순 존재 여부만 체크

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `❌ 팀 공유 설정 파일이 없습니다` | `yeoboya-workflow.config.json` 없음 | 팀 리드가 최초 셋업 실행 후 JSON 을 레포에 커밋 |
| `tesseract not found` | Tesseract 미설치 | `brew install tesseract tesseract-lang` |
| `PyPDF2 not found` | Python 의존성 미설치 | `pip install -r skills/pdf-spec-organizer/scripts/requirements.txt` (venv 활성화 후) |
| OCR 텍스트가 깨짐 | 언어 팩 부재 | `brew install tesseract-lang` 후 재시도 |
| Notion 페이지 생성 실패 (404) | MCP 가 해당 워크스페이스에 접근 권한 없음 | Notion 설정 → Connections → Claude 추가 |
| PII 경고가 계속 뜸 | 실제로 민감 정보가 PDF 에 포함됨 | 마스킹된 항목 확인 후 진행 여부 판단. 필요시 PDF 정리 후 재시도 |

---

## 개발 / 확장

### 새 워크플로우 기능 추가

`yeoboya-workflow` 는 umbrella 플러그인이라 기능을 계속 쌓을 수 있게 설계됨:

```
skills/<new-feature>/
commands/<new-feature>.md
config/<new-feature>/
```

기존 `pdf-spec-organizer` 파일은 건드리지 않고 독립 디렉토리로 추가.

### 테스트

```bash
cd skills/pdf-spec-organizer/scripts
source .venv/bin/activate
pytest tests/ -v
```

18개 단위 테스트 (parse_pdf, ocr_fallback, pii_scan, pdf_hash, draft_registry).

### Description 최적화 실행

skill-creator 의 `run_loop.py` 로 `pdf-spec-organizer` 스킬의 description 을 자동 튜닝할 수 있다. 20개 trigger eval query 는 `evals/trigger-eval.json` 에 준비됨.

```bash
# skill-creator 가 설치된 디렉토리로 이동 (예: 플러그인 캐시)
cd ~/.claude/plugins/cache/skill-creator/unknown/skills/skill-creator

python -m scripts.run_loop \
  --eval-set <플러그인-루트>/evals/trigger-eval.json \
  --skill-path <플러그인-루트>/skills/pdf-spec-organizer \
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

릴리스 전 [`docs/manual-qa.md`](docs/manual-qa.md) 체크리스트 전 항목 확인.

---

## 문서

- **설계 스펙 (v0.1)**: [`docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md`](docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md)
- **구현 계획 (v0.1)**: [`docs/superpowers/plans/2026-04-19-pdf-spec-organizer.md`](docs/superpowers/plans/2026-04-19-pdf-spec-organizer.md)
- **설계 스펙 (skill refactor)**: [`docs/superpowers/specs/2026-04-19-pdf-spec-organizer-skill-refactor-design.md`](docs/superpowers/specs/2026-04-19-pdf-spec-organizer-skill-refactor-design.md)
- **구현 계획 (skill refactor)**: [`docs/superpowers/plans/2026-04-19-pdf-spec-organizer-skill-refactor.md`](docs/superpowers/plans/2026-04-19-pdf-spec-organizer-skill-refactor.md)
- **수동 QA**: [`docs/manual-qa.md`](docs/manual-qa.md)
- **변경 내역**: [`CHANGELOG.md`](CHANGELOG.md)

---

## 로드맵

**v0.2 (계획):**
- Source-of-truth 인터페이스 — 기존 Notion 스펙 DB + iOS/Android 코드베이스 와 교차 충돌/중복 체크
- `checklist.yaml` 의 `severity` 필드와 조건부 적용

**v0.3+ (가능성):**
- PDF 외 입력 (`/spec-from-notion`, `/spec-from-figma`)
- 로컬 이미지 → 외부 호스팅 자동 중계

---

## v2 변경사항 (2026-04-20)

### 1 PDF = 1 Notion 페이지

기존: 피처마다 개별 페이지 생성 → DB 가 혼잡.
v2: PDF 1개 = 페이지 1개. 피처는 Toggle 블록으로 접혀있음. 필요할 때만 펼쳐서 확인.

### 노트 보존

`/spec-from-pdf` 를 같은 PDF 로 다시 실행해도 iOS/Android/공통 노트는 보존된다. `feature_id` 기반 병합으로 피처 rename 후에도 노트 매칭됨.

### 부분 퍼블리시 재개

Phase 5 도중 실패한 경우 `/spec-resume --resume-latest` 로 **중단된 chunk 부터** 이어서 publish. 전체 재실행 불필요.

### `/spec-update` 피처 단위 편집

```
/spec-update <page-url> --feature="<피처명>"
```
해당 Toggle 블록만 열어서 편집 + 병합. 공백/괄호/슬래시(`(A/B)`) 피처명도 안전.

### 마이그레이션

v1 에서 이미 생성된 피처 페이지가 있다면:

1. DB 에 property 추가 (`migrated_to`, `archived`)
2. `/spec-resume` 또는 새 `/spec-migrate` (해당 workflow) 에서 안내대로 진행
3. 자세한 내용: `skills/pdf-spec-organizer/SKILL.md` 의 "마이그레이션" 섹션

### 기존 커맨드는 동일

`/spec-from-pdf`, `/spec-update`, `/spec-resume` 슬래시 이름은 유지. 동작만 v2 로 바뀜.
