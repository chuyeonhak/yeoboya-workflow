---
name: pdf-spec-organizer
description: 복합 PDF 스펙(PRD+디자인+플로우)을 파싱해 Notion 피처 DB 페이지로 정리한다. 명세 누락 체크 + iOS/Android 플랫폼별 개발자 노트 공유. /spec-from-pdf, /spec-update, /spec-resume 커맨드의 실제 로직.
allowed-tools: Bash Read Write Edit Grep Glob mcp__claude_ai_Notion__notion-search mcp__claude_ai_Notion__notion-fetch mcp__claude_ai_Notion__notion-create-pages mcp__claude_ai_Notion__notion-create-database mcp__claude_ai_Notion__notion-update-page mcp__claude_ai_Notion__notion-update-data-source
---

# pdf-spec-organizer

복합 PDF 스펙을 Notion 피처 DB 페이지로 정리하는 5단계 워크플로우.

## Precondition 체크 (Skill 시작 시 항상 먼저)

아래 항목을 순서대로 확인하고 실패 시 즉시 중단한다:

### 1. 인자 확인

- 필수: `PDF_PATH` 환경 변수 또는 커맨드 인자
- 경로가 파일이 아니면 중단 + 구체 메시지

### 2. 팀 공유 설정 확인

- **현재 워크스페이스 레포 루트**에서 `yeoboya-work-flow.config.json` 을 찾는다.
- 없으면 다음 메시지로 중단:

  ```
  ❌ 팀 공유 설정 파일이 없습니다: yeoboya-work-flow.config.json

  팀 리드가 먼저 최초 셋업을 실행하고 이 파일을 레포에 커밋해야 합니다.
  최초 셋업은 별도 문서 참고: README.md 의 "팀 리드 최초 셋업" 섹션.
  ```

- 있으면 `pdf_spec_organizer.notion_database_id` 값을 읽어 Notion DB ID 로 사용.

### 3. Python 의존성 확인

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

Run: `command -v tesseract`

없으면 경고만:
```
⚠️  Tesseract 가 설치되지 않아 OCR fallback 이 비활성됩니다.
  이미지 전용 페이지의 텍스트 추출이 안 될 수 있습니다.
  설치: brew install tesseract tesseract-lang (macOS)
```

## Phase 1 — 파싱

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
