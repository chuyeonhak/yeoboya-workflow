# yeoboya-work-flow

여보야 회사 워크플로우 자동화 Claude Code 플러그인.

## 기능

### pdf-spec-organizer (v0.1)

복합 PDF 스펙(PRD + 디자인 + 플로우)을 Notion 피처 DB 페이지로 정리한다. iOS/Android 팀이 같은 페이지에서 플랫폼별 개발자 노트를 공유한다.

**커맨드:**
- `/spec-from-pdf <path> [--fast]` — PDF → Notion 페이지 생성
- `/spec-update <notion-url>` — 기존 페이지에 노트/체크만 갱신
- `/spec-resume [--resume-latest | <draft-path>]` — 중단된 세션 이어받기

## 설치

플러그인을 사용할 프로젝트 레포에서:

1. Claude Code 설정에 이 플러그인 경로 추가
2. 프로젝트 레포 루트에 팀 공유 설정 파일 커밋:

   ```json
   {
     "pdf_spec_organizer": {
       "notion_database_id": "<feature-db-id>",
       "parent_page_id": "<parent-page-id>"
     }
   }
   ```
   파일명: `yeoboya-work-flow.config.json`

3. Python 의존성 설치:

   ```bash
   pip install -r skills/pdf-spec-organizer/scripts/requirements.txt
   ```

4. Tesseract 설치 (OCR fallback용):

   ```bash
   brew install tesseract tesseract-lang  # macOS
   ```

## 팀 리드 최초 셋업

부모 Notion 페이지 URL 을 준비한 뒤 팀 리드가 최초 셋업을 실행. DB 자동 생성 후 출력되는 `yeoboya-work-flow.config.json` 을 프로젝트 레포에 커밋한다.

## 문서

- 설계: [`docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md`](docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md)
- 수동 QA: [`docs/manual-qa.md`](docs/manual-qa.md)
