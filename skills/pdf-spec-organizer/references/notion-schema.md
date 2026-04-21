# Notion 피처 DB 스키마 상세

이 문서는 SKILL.md 에서 참조하는 Notion DB 스키마 상세 정의이다.
실제 DB 자동 생성 시 사용하는 프로그램적 스키마는 `config/pdf-spec-organizer/notion-schema.yaml` 이다.

## DB 속성

| 속성 | 타입 | Notion API 타입 | 설명 |
|---|---|---|---|
| 이름 | Title | `title` | 피처명 (예: "알림 설정 화면") |
| 플랫폼 | Multi-select | `multi_select` | `iOS`, `Android`, `공통` |
| 상태 | Select | `select` | `Draft`, `In Review`, `Ready`, `In Dev`, `Done` |
| 원본 PDF | Text | `rich_text` | **파일명만** (홈 경로 노출 방지) |
| PDF 해시 | Text | `rich_text` | SHA-256 앞 12자 |
| 소스 링크 | URL | `url` | 다건은 본문 링크 블록에 추가 |
| 이전 버전 | Relation (self) | `relation` | 새 버전 생성 시 연결 |
| 관련 피처 | Relation (self) | `relation` | v2 source-of-truth 기반 |
| 생성자 | Person | `people` | 플러그인 실행자 |
| 생성일 | Created time | `created_time` | 자동 |
| 누락 항목 | Multi-select | `multi_select` | `checklist.yaml` 의 id |

## 페이지 본문 블록 구조

```markdown
# <피처명>

## 개요
<Claude 추출 1-2문단>

## 화면 / 플로우
<Notion 업로드된 이미지 + 캡션>

## 요구사항
- ...

## 누락 체크
- [ ] 에러 케이스
- [x] 빈 상태 (명시됨)
- [ ] 오프라인 처리
...

## 개발자 노트
### iOS
<Phase 4 입력, 없으면 빈 상태>

### Android
<Phase 4 입력>

### 공통 질문
<양 팀 논의 거리>

## 메타
- 원본 PDF: `<filename>`
- PDF 해시: `<short-hash>`
- 생성자: <user>
- 생성일: <date>
```

## 팀 DB 공유 전략

`yeoboya-workflow.config.json` 을 프로젝트 레포 루트에 커밋:

```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "<feature-db-id>",
    "parent_page_id": "<parent-page-id>"
  }
}
```

- 파일이 없으면 skill 이 "팀 리드가 먼저 셋업하고 커밋하세요" 안내
- 최초 셋업: 부모 Notion 페이지 URL 입력 → DB 자동 생성 → 설정 파일 초안 출력 → 사용자가 커밋

## v2 확장

- 관련 피처 Relation 을 활용한 의존/충돌 추적
- Source-of-truth 인터페이스는 `references/source-of-truth.md` 참조
