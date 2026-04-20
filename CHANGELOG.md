# Changelog

## v0.2.0 — 2026-04-20

### Changed
- `pdf-spec-organizer`: 1 PDF = 1 Notion page (with features as Toggle blocks). v1 per-feature page behavior removed.
- `/spec-update`: new `--feature="<name>"` flag for toggle-level edit.
- `/spec-resume`: partial-append resume via `publish_state` + sentinel markers.
- Notion page body format updated: `feature_id`, `notes_*_start|end`, `publish_sentinel` markers.

### Added
- `scripts/feature_id.py` — UUID4 generation + name resolution.
- `scripts/note_extractor.py` — parse notes by `feature_id`.
- `scripts/note_merger.py` — inject preserved notes into new draft.
- `scripts/page_publisher.py` — chunked block payload + sentinel-based resume cursor.
- `scripts/migrate_to_per_pdf.py` — one-time consolidation planner (dry-run).
- `draft_registry.py`: `page_id`, `publish_state` fields, `partial_success` status.

### Migration
- v1 per-feature pages are consolidated via `migrate_to_per_pdf.py` dry-run + SKILL-orchestrated apply.
- New DB properties required: `migrated_to` (URL), `archived` (Checkbox).
- v1 drafts (`phase: 4`) fall back to full re-publish on `/spec-resume`.

모든 주목할 만한 변경 사항을 이 파일에 기록합니다.

## [0.1.1] - 2026-04-19

### Changed
- `pdf-spec-organizer` 스킬 description 을 자연어 트리거에 최적화 (사용자 실제 어휘 7종 반영, skill-creator "pushy" 원칙 적용, `/spec-update` 경로 명시)
- 트리거 eval 2 반복 튜닝 결과 **20/20 (100%)** 달성 — Iter1 90% → Iter2 100%. 실패 사례(기존 페이지 노트 추가) 해결
- SKILL.md Phase 5 세부(충돌 처리 프롬프트, 이미지 업로드 fallback) 를 `references/conflict-policy.md` 로 이동 (SKILL.md 길이 감축)

### Added
- SKILL.md 의 Precondition 4개 + Phase 5개 섹션에 "왜 이 단계가 있는가" 주석 추가 (LLM 의도 이해도 향상)
- `evals/trigger-eval.json` — 20 개 description 트리거 eval query (should-trigger 10 + should-not-trigger 10)
- README 에 `skill-creator` 의 `run_loop.py` 실행 가이드 추가 (description 자동 튜닝 루프)

## [0.1.0] - 2026-04-19

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
