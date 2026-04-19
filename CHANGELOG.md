# Changelog

모든 주목할 만한 변경 사항을 이 파일에 기록합니다.

## [Unreleased]

### Added
- `pdf-spec-organizer` 기능 초기 구현
  - `/spec-from-pdf`, `/spec-update`, `/spec-resume` 커맨드
  - PDF 파싱 + OCR fallback + PII 스캔
  - Notion 피처 DB 자동 생성 및 페이지 퍼블리시
  - 플랫폼별 개발자 노트 섹션 (iOS / Android / 공통)
  - 병합 기본 충돌 처리, 동시 실행 감지

### Planned (v0.2)
- Source-of-truth 인터페이스 (기존 스펙/코드베이스 충돌 체크)
- `checklist.yaml` severity / 조건부 필드
