---
name: pdf-spec-organizer
description: 기획자/PM 에게 받은 PDF 스펙(PRD, 디자인 시안, 유저 플로우) 을 Notion 피처 DB 페이지로 정리하거나, 기존 피처 페이지에 iOS/Android 개발자 노트를 추가한다. 명세 누락 (에러/빈상태/오프라인/권한/로딩/접근성) 을 자동 체크하고 iOS/Android 팀이 같은 페이지에서 플랫폼별 개발자 노트를 공유하도록 구조화한다. 사용자가 "이 PDF 정리해줘", "기획서 스펙 정리", "피처 스펙 노션에 올려줘", "개발자 노트 정리", "명세 누락 체크해줘", "기존 페이지에 내 플랫폼 노트 추가", "같은 페이지에 Android 노트 남길 수 있어?" 같은 요청을 하거나 기획 PDF 문서를 언급하거나 피처 페이지에 협업 노트를 추가하고 싶을 때 반드시 이 스킬을 사용할 것. 슬래시 커맨드 `/spec-from-pdf`, `/spec-update`, `/spec-resume` 의 실제 구현 로직.
allowed-tools: Bash Read Write Edit Grep Glob mcp__claude_ai_Notion__notion-search mcp__claude_ai_Notion__notion-fetch mcp__claude_ai_Notion__notion-create-pages mcp__claude_ai_Notion__notion-create-database mcp__claude_ai_Notion__notion-update-page mcp__claude_ai_Notion__notion-update-data-source
---

# pdf-spec-organizer

복합 PDF 스펙을 Notion 피처 DB 페이지로 정리하는 5단계 워크플로우.

## Precondition 체크 (Skill 시작 시 항상 먼저)

아래 항목을 순서대로 확인하고 실패 시 즉시 중단한다:

### 1. 인자 확인

**왜:** PDF 경로가 없으면 이후 Phase 전체가 실패함. 진입점에서 빠르게 차단해 /tmp 낭비와 잘못된 상태 방지.

- 필수: `PDF_PATH` 환경 변수 또는 커맨드 인자
- 경로가 파일이 아니면 중단 + 구체 메시지

### 2. 팀 공유 설정 확인

**왜:** 팀원들이 각자 다른 Notion DB 에 피처를 만들면 iOS/Android 가 서로 못 봄. 레포에 커밋된 설정이 "팀의 단일 DB" 를 보장.

- **현재 워크스페이스 레포 루트**에서 `yeoboya-work-flow.config.json` 을 찾는다.
- 없으면 다음 메시지로 중단:

  ```
  ❌ 팀 공유 설정 파일이 없습니다: yeoboya-work-flow.config.json

  팀 리드가 먼저 최초 셋업을 실행하고 이 파일을 레포에 커밋해야 합니다.
  최초 셋업은 별도 문서 참고: README.md 의 "팀 리드 최초 셋업" 섹션.
  ```

- 있으면 `pdf_spec_organizer.notion_database_id` 값을 읽어 Notion DB ID 로 사용.

### 3. Python 의존성 확인

**왜:** 후속 스크립트들이 모두 PyPDF2/pdf2image/yaml 등을 import. Phase 1 중간에 실패하면 초안 일관성이 깨지고 사용자 혼란 유발.

Run (Bash):
```bash
python3 -c "import PyPDF2, pdf2image, PIL, yaml, pytesseract" 2>&1
```

실패 시:
```
❌ Python 의존성이 설치되지 않았습니다.
  pip install -r ${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/requirements.txt
```

### 4. Tesseract 확인 (경고만, 차단 아님)

**왜:** 이미지 전용 PDF 에서만 필요. 텍스트 PDF 는 Tesseract 없이도 정상 동작하므로 강제하지 않음 — 경고로 알리기만.

Run: `command -v tesseract`

없으면 경고만:
```
⚠️  Tesseract 가 설치되지 않아 OCR fallback 이 비활성됩니다.
  이미지 전용 페이지의 텍스트 추출이 안 될 수 있습니다.
  설치: brew install tesseract tesseract-lang (macOS)
```

## Phase 1 — 파싱

**왜:** 후속 Phase 는 모두 파싱 결과를 읽음. 여기서 실패하면 뒤는 무의미. 이미지 추출 / OCR fallback / PII 스캔을 이 Phase 에 몰아서 한 번만 처리해 효율 확보.

### 1-1. 임시 작업 폴더 생성

```bash
PDF_PATH="$1"  # 절대경로로 정규화된 값
PDF_HASH=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/pdf_hash.py" "$PDF_PATH")
TS=$(date +%s)
WORK_DIR="/tmp/spec-draft-${PDF_HASH}-${TS}"
mkdir -p "$WORK_DIR"
DRAFT_PATH="${WORK_DIR}/draft.md"
```

### 1-2. 동시 실행 감지

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  query-recent --hash "$PDF_HASH" --within-seconds 300 > "${WORK_DIR}/recent.json"
```

`recent.json` 의 `found` 가 `true` 면 사용자에게 경고:
```
⚠️  5분 내 동일 PDF 를 다른 실행이 처리했습니다.
  실행자: <entry.who>  시작: <time>  경로: <entry.draft_path>

덮어쓰기 전에 조율하세요. 계속할까요? (y/n)
```

`n` 이면 중단.

### 1-3. 실행 기록

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  record --hash "$PDF_HASH" --draft-path "$DRAFT_PATH" --status running
```

### 1-4. parse_pdf 실행

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/parse_pdf.py" \
  "$PDF_PATH" --out-dir "${WORK_DIR}/images" > "${WORK_DIR}/parsed.json"
```

exit code:
- `0`: 계속
- `1`: 파일/포맷 오류 → 에러 출력 + 중단
- `3`: 암호화 PDF → "암호 해제된 PDF로 다시 시도해주세요" 안내 + 중단

### 1-5. OCR fallback 판단

`parsed.json` 의 `pages` 에서 `has_text: false` 페이지가 있고 이미지가 있으면 OCR 실행:

```bash
IMG_PATHS=$(python3 -c "
import json
data = json.load(open('${WORK_DIR}/parsed.json'))
need_ocr = any(not p['has_text'] for p in data['pages'])
if need_ocr:
    print(' '.join(img['path'] for img in data['images']))
" )

if [ -n "$IMG_PATHS" ] && command -v tesseract >/dev/null 2>&1; then
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/ocr_fallback.py" \
    --images $IMG_PATHS > "${WORK_DIR}/ocr.json"
  echo "  (OCR 결과 품질이 낮을 수 있습니다. 개발자 노트에서 보완하세요.)"
fi
```

### 1-6. PII 스캔

```bash
python3 -c "
import json
data = json.load(open('${WORK_DIR}/parsed.json'))
print('\n'.join(p['text'] for p in data['pages']))
" | python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/pii_scan.py" > "${WORK_DIR}/pii.json"
```

`pii.json` 의 `findings` 가 비어있지 않으면 경고만 표시 (차단 아님):
```
⚠️  PII 로 의심되는 패턴이 발견되었습니다 (N건):
  - email (line 12): u***r@example.com
  - phone (line 34): 010-****-5678

민감 정보가 Notion 에 퍼블리시될 수 있습니다. 진행할까요? (y/n)
```

### 1-7. 통합 데이터 구성

`parsed.json`, `ocr.json` (있으면), `pii.json` 을 Claude 가 읽어 후속 Phase 에서 사용한다.

## Phase 2 — 구조화 + 개입 ①

**왜:** PDF 를 자동으로 피처 단위로 쪼개는 건 Claude 의 추정이라 실수 가능. 개발자가 한 번 검증해야 잘못된 구조로 Notion 이 오염되지 않음.

### 2-1. Claude 에게 피처 추출 지시

Phase 1 산출물(`parsed.json` + `ocr.json` + 이미지 썸네일)을 읽어 **피처 리스트**를 생성한다.

추출 규칙:
- 한 피처 = 하나의 사용자 가치 단위 (화면/플로우 1~N개 포함 가능)
- 각 피처마다 필드:
  - `name`: 간결한 한글 이름 (10자 내외)
  - `platform`: iOS / Android / 공통 중 1개 이상
  - `summary`: 1-2문장
  - `screens`: 관련 이미지 페이지 번호 리스트
  - `requirements`: 불릿 포인트 리스트

결과를 `${WORK_DIR}/features.json` 으로 저장.

### 2-2. 사용자 확인 프롬프트

`references/review-format.md` 의 "터미널 출력 규약" 섹션을 따라 피처 목록 출력:

```
피처 3개 추출됨:
  1. 알림 설정 화면 (iOS, Android)
  2. 푸시 권한 요청 플로우 (iOS, Android)
  3. 빈 상태 UI (공통)

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

**`--fast` 플래그 처리:**
- 피처 경계 확인(s/m/r) 은 자동 통과
- **플랫폼 태깅(t) 확인은 여전히 강제**. 프롬프트:
  ```
  [--fast 모드] 플랫폼 태깅을 확인해주세요:
    1. 알림 설정 화면 → iOS, Android
    2. 푸시 권한 요청 플로우 → iOS, Android
    3. 빈 상태 UI → 공통

  모두 맞으면 y, 수정하려면 t N:
  >
  ```

### 2-3. 사용자 입력 처리 루프

각 명령별 동작:
- `y` → 다음 Phase
- `s N` → 피처 N번을 Claude 에게 "더 작게 쪼개세요" 지시, 결과 갱신 후 다시 2-2 로
- `m N,M` → Claude 에게 "N번과 M번을 병합, 이름/플랫폼 재정의" 지시 후 2-2
- `r N` → 사용자에게 새 이름 입력받아 N번 `name` 교체 후 2-2
- `t N` → 사용자에게 새 플랫폼 선택(체크박스) 받아 N번 `platform` 교체 후 2-2
- `e` → `${WORK_DIR}/features.md` 로 직렬화 → `$EDITOR` 로 열기 → 저장 후 다시 파싱해서 `features.json` 갱신 → 2-2
- `c` → Phase 정리(아래) 후 중단

### 2-4. 중단 정리

취소 시:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  update-status --draft-path "$DRAFT_PATH" --status failed
```
/tmp 폴더는 TTL 에 의해 7일 후 자동 삭제.

## Phase 3 — 누락 체크

**왜:** 기획서가 엣지케이스(에러/빈상태/오프라인 등) 를 빠뜨리는 건 흔함. 표준 체크리스트로 구현 단계 리스크를 사전 감소. 체크 자체는 자동, 해석/대응은 개발자 노트에서.

### 3-1. 체크리스트 로드

```bash
CHECKLIST_YAML="${CLAUDE_PLUGIN_ROOT}/config/pdf-spec-organizer/checklist.yaml"
CHECKLIST_FALLBACK="${CLAUDE_PLUGIN_ROOT}/config/pdf-spec-organizer/default-checklist.json"

python3 -c "
import sys, json, yaml
try:
    items = yaml.safe_load(open('${CHECKLIST_YAML}'))['items']
    source = 'yaml'
except Exception as e:
    print(f'⚠️  checklist.yaml 파싱 실패: {e}. fallback 사용.', file=sys.stderr)
    items = json.load(open('${CHECKLIST_FALLBACK}'))['items']
    source = 'fallback'
print(json.dumps({'items': items, 'source': source}))
" > "${WORK_DIR}/checklist.json"
```

`source == 'fallback'` 이면 경고 표시 (계속 진행).

### 3-2. 피처별 누락 항목 계산

각 피처에 대해:
1. `applies_to` 와 피처 `platform` 의 교집합이 비어있으면 해당 체크 항목은 스킵
2. 남은 항목에 대해 Claude 가 피처의 `summary` + `requirements` 를 읽고 "이 항목이 명시되어 있는가?" 판정
3. 명시 안 됨 → 누락으로 표시

결과를 `${WORK_DIR}/missing.json` 으로 저장:
```json
{
  "features": [
    {
      "name": "알림 설정 화면",
      "missing": ["error_cases", "offline"],
      "satisfied": ["empty_state", "loading", "a11y"]
    }
  ]
}
```

### 3-3. 요약 출력

```
누락 체크 완료:
  1. 알림 설정 화면
     누락: 에러 케이스, 오프라인 처리
     명시: 빈 상태, 로딩 상태, 접근성

  2. 푸시 권한 요청 플로우
     누락: 권한 거부 재요청 UX
     명시: 에러 케이스, 빈 상태

  의도된 제외는 다음 단계 "개발자 노트" 에 적어주세요.

계속하려면 Enter.
```

## Phase 4 — 개발자 노트 + 미리보기 + 개입 ②

**왜:** 기술 판단(iOS/Android 구현 차이, 엣지케이스, 팀 간 질문거리) 은 Claude 가 대신할 수 없는 영역. 이 단계가 스킬의 핵심 가치 — 팀 지식을 축적하는 지점. v2 부터는 PDF 1개 = 초안 1개 = Notion 페이지 1개 구조이므로 모든 피처 노트를 **한 파일 안에서** 한 번에 작성한다.

### 4-1. feature_id 할당

```bash
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/feature_id.py" \
  assign --features-file "${WORK_DIR}/features.json"
```

- 새 피처에 UUID4 를 부여한다
- 이미 `feature_id` 가 있는 피처는 건드리지 않음 (Phase 2 의 rename/merge/split 이후에도 id 는 유지)

### 4-2. 초안 md 파일 렌더

`features.json` + `missing.json` + `parsed.json` 을 통합해 `${DRAFT_PATH}` 로 저장. 포맷은 `references/review-format.md` 의 "초안 파일 구조" 를 엄격히 따른다.

**중요:**
- `<!-- plugin-state -->` 헤더에 `phase: 4`, `pdf_hash`, `source_file`, `created_at`, `publish_state: idle`, `page_id:` (빈 값), `last_block_sentinel_id:` (빈 값) 포함
- 각 피처는 Toggle heading (`### N. <name> {toggle="true"}`) 로 렌더
- 각 Toggle 첫 줄 아래에 `<!-- feature_id: <uuid> -->` 주석 삽입
- iOS / Android / 공통 노트 섹션은 `<!-- notes_*_start/end -->` 마커로 감싸고 **빈 상태** (`<empty-block/>`) 로 렌더
- 각 Toggle 끝에 `<!-- publish_sentinel: feature_<short-id>_done -->` 삽입
- `--fast` 플래그여도 이 Phase 는 생략되지 않음

### 4-3. 사용자에게 노트 작성 프롬프트

```
다음 단계: 개발자 노트 작성

초안 파일: /tmp/spec-draft-<hash>-<ts>/draft.md
(피처 7개가 Toggle 블록으로 들어있습니다. 담당 플랫폼 섹션만 채우세요.)

어떻게 할까요?
  e) 에디터($EDITOR)로 열기  ← 권장
  s) 건너뛰기 (빈 노트로 퍼블리시)
  c) 취소
>
```

`e` 선택 시 `$EDITOR` 로 열기. 값이 없으면 `code` / `vim` 순으로 시도.

### 4-4. 저장 후 검증

에디터 종료 후:
- 파일 존재 확인
- `plugin-state` 헤더 파싱 → `phase` 를 5 로 업데이트
- 노트 섹션이 전부 비어도 경고만 표시 (계속 가능):
  ```
  ℹ️  노트가 비어있습니다. Phase 5 로 계속할까요? (y/n/e)
  ```
  `e` 는 다시 에디터 열기.

### 4-5. 최종 미리보기

```
미리보기:

  PDF: <filename>
  피처 7개, 누락 항목 35개, 노트:
    - 앱 시작 플로우 개방: iOS ✓, Android ✗, 공통 ✗
    - 메인화면 비로그인 UI 제어: iOS ✓, Android ✓, 공통 ✗
    ...

  Notion 에 퍼블리시할까요?
    y) 퍼블리시
    e) 에디터로 다시 열기
    c) 취소
>
```

### 4-6. 취소 / 에디터 재진입 처리

- `c` → Phase 5 진입 전 정리 (`draft_registry update-status --status failed`)
- `e` → 4-3 으로 돌아감

## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

**왜:** v2 는 PDF 1개 = 페이지 1개. 동일 PDF 재실행·업데이트 PDF·동시 편집 같은 상황을 안전하게 처리해야 한다. 또한 Notion API 의 per-call block 제한 때문에 chunked publish + sentinel 기반 resume 이 필수.

### 5-1. DB ID / 파일명 확보

- Notion DB data source ID: Precondition 2 에서 읽은 `notion_database_id` 와 config 의 `notion_data_source_id` 사용
- `PDF_FILENAME=$(basename "$PDF_PATH")` 만 저장 (홈 경로 노출 방지)

### 5-2. Dedup 조회

1. `mcp__claude_ai_Notion__notion-search` 로 `data_source_url=collection://<data_source_id>`, query=`<PDF 해시>` 검색 (title + PDF 해시 property 매칭)
2. 해시 일치 페이지 있음 → 1a. "동일 PDF 재실행" 프롬프트 (`references/conflict-policy.md` 참조)
3. 해시 불일치 + 같은 파일명 페이지 있음 → 1b. "업데이트된 PDF" 프롬프트
4. 모두 없음 → 5-3 새 페이지 플로우

### 5-3. 새 페이지 퍼블리시 (신규 경로)

```bash
# 1) shell 페이지 생성 (제목/properties/개요만)
# mcp__claude_ai_Notion__notion-create-pages 호출 → page_id 획득

# 2) draft.md 본문을 chunks 로 분할
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/page_publisher.py" chunk \
  --input "${DRAFT_PATH}" --max-blocks 80 > "${WORK_DIR}/chunks.json"

# 3) plugin-state 업데이트
#    publish_state=page_created
#    page_id=<notion page id>
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/draft_registry.py" update-status \
  --draft-path "${DRAFT_PATH}" \
  --status running \
  --page-id "${PAGE_ID}" \
  --publish-state page_created

# 4) chunk 순차 append:
#    각 chunk 에 대해 mcp__claude_ai_Notion__notion-update-page
#    command=update_content, content_updates=[ { old_str: <last_sentinel>, new_str: <chunk_markdown> } ]
#    (첫 chunk 는 shell 페이지의 overview 말미를 anchor 로 사용)
#    성공 후 draft 의 plugin-state 에 last_block_sentinel_id 갱신
#    ${WORK_DIR}/publish.log 에 timestamped 로그 기록
#    Rate limit 발생 시 exponential backoff (1, 2, 4, 8 초, max 3 retries)

# 5) 모든 chunk 성공 → publish_sentinel: complete append
# 6) draft_registry update-status --status success --publish-state complete
```

### 5-4. 덮어쓰기 (노트 보존) 경로

```bash
# 1) 기존 페이지 본문 fetch
# mcp__claude_ai_Notion__notion-fetch id=${EXISTING_PAGE_ID}
# 결과를 ${WORK_DIR}/existing_body.md 로 저장

# 2) 노트 추출
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/note_extractor.py" \
  < "${WORK_DIR}/existing_body.md" > "${WORK_DIR}/preserved_notes.json"

# 3) 새 draft 에 병합
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/note_merger.py" \
  --draft "${DRAFT_PATH}" \
  --notes "${WORK_DIR}/preserved_notes.json"

# 4) 덮어쓰기: replace_content 로 전체 교체
# mcp__claude_ai_Notion__notion-update-page command=replace_content new_str=<draft body>
# (chunk 제한이 문제되면 5-3 의 shell+chunks 경로를 동일하게 사용)

# 5) properties fresh union 으로 갱신
# mcp__claude_ai_Notion__notion-update-page command=update_properties ...
```

### 5-5. 새 버전 경로

1. 5-3 새 페이지 플로우 동일
2. 단, create-page 시 `이전_버전` Relation 에 기존 페이지 URL 포함
3. 기존 페이지는 건드리지 않음

### 5-6. 실행 기록 갱신

성공:
```bash
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/draft_registry.py" update-status \
  --draft-path "${DRAFT_PATH}" \
  --status success \
  --publish-state complete
```

부분 실패 (chunk 도중 중단):
```bash
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/draft_registry.py" update-status \
  --draft-path "${DRAFT_PATH}" \
  --status partial_success \
  --publish-state chunks_appending
```
터미널:
```
⚠️  3 chunk 중 2 chunk 만 append 됐습니다:
  ✓ chunk 0/2
  ✓ chunk 1/2
  ✗ chunk 2/2 (Notion API timeout)

이어서 시도: /spec-resume --resume-latest
초안: <draft_path>  페이지: <notion_url>
```

### 5-7. 결과 요약 + GC

성공:
```
✓ 퍼블리시 완료:
  <PDF 제목>: https://notion.so/...

초안은 3일 후 자동 삭제됩니다: <draft_path>
```

GC 트리거:
```bash
python3 "/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/draft_registry.py" gc
```
`partial_success` 는 7일 보존 (GC 대상 아님) 이므로 자연스럽게 `/spec-resume` 시나리오 보호.

## Resume 모드

`/spec-resume` 가 호출되면 이 Skill 이 다른 모드로 진입.

### R-1. 초안 선택

- `--resume-latest`: `draft_registry list-latest --count 5` 결과에서 **`status` 가 `running` 또는 `failed`** 인 최신 항목 자동 선택. 없으면 사용자에게 리스트 보여주고 선택받기.
- `--resume <path>`: 지정된 경로 사용. 없으면 중단.

### R-2. 상태 복구

초안 파일의 `<!-- plugin-state -->` 헤더에서 `phase` 를 읽어 다음 Phase 부터 시작:
- `phase: 1` → Phase 2 부터 재실행
- `phase: 2` → Phase 3 부터
- `phase: 3` → Phase 4 부터
- `phase: 4` → Phase 5 부터

### R-3. 실행

해당 Phase 부터 본 워크플로우와 동일하게 진행. 마지막에 `update-status` 갱신.

## Update 모드 (`/spec-update`)

기존 Notion 페이지 URL 을 받아 **Phase 4 만** 다시 실행.

### U-1. 페이지 조회

`mcp__claude_ai_Notion__notion-fetch` 로 기존 페이지 본문 가져옴.

### U-2. 임시 초안으로 변환

본문을 `references/review-format.md` 포맷의 md 로 변환해 `${WORK_DIR}/draft.md` 저장.

### U-3. 노트 작성 (Phase 4 재사용)

Phase 4 로직 그대로 실행.

### U-4. 병합 퍼블리시

Phase 5 의 **병합** 경로만 사용. 덮어쓰기/새 버전은 이 모드에서 허용 안 함.
