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
