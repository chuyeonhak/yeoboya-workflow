# Changelog

## [Unreleased]

### Added
- `/work` 커맨드 — 일감 단위 스펙 작성 통합 진입점. 작업 유형(`feature` / `bug` / `enhancement`) 과 PDF 유무를 대화 또는 플래그(`--type` / `--pdf` / `--no-pdf`) 로 받아 하위 워크플로우로 라우팅. PDF 있으면 `/spec-from-pdf` 로 위임, 없으면 `conversation-spec-organizer` 로 연결 (배선은 v0.5 예정).
- `skills/conversation-spec-organizer/SKILL.md` — PDF 없는 경로용 3-Phase 설계 문서 (Brainstorming → 스펙 구조화 → Notion publish). 실제 구현은 v0.5.

### Changed (Internal — v1.0 준비)
- 재사용 Python 모듈 8개를 `skills/common/scripts/` 로 이동 (히스토리 보존된 `git mv`)
- `skills/pdf-spec-organizer/scripts/_path_setup.py` 신설해 `common/scripts/` 참조
- 외부 API/동작 변경 없음 (기존 사용자 영향 없음)

## [0.4.0] - 2026-04-21

### Added
- Phase 3.5 **피처 메타 정보 생성 단계** — `project_context_path` 가 설정되면 Phase 3 직후 각 피처에 `예상 기간 / 타팀 의존성 / 기획 누락 / 타팀 요청사항` 메타를 자동 제안. 개발자는 Phase 4 에서 검토/수정.
- 코드베이스 탐색에 Claude Code `Explore` subagent 사용 (`superpowers:dispatching-parallel-agents` 원칙으로 피처 3+ 는 병렬 dispatch). 토큰 한도 접근 시 `thoroughness` 를 자동 `quick` 강등.
- `scripts/enrich_features.py` — `load-context` (500줄 절삭) + `merge-metadata` (features.json 병합, JSON 파싱 실패 시 빈 구조 fallback).
- `references/project-context-template.md` — 팀이 복사해서 쓸 템플릿.
- `<!-- meta_start|end -->` 블록이 Phase 4 초안 md 와 Notion Toggle 본문에 포함됨.

### Changed
- `note_extractor.py` / `note_merger.py` 가 `<!-- meta_start|end -->` 블록도 노트 섹션과 동등하게 추출/병합.
- `features.json` 스키마: 각 피처에 `metadata` 객체(`estimated_effort` / `external_dependencies` / `planning_gaps` / `cross_team_requests`) 추가.
- `yeoboya-workflow.config.json.example` 에 `project_context_path` + `codebase_roots` 예시.
- Phase 4 미리보기 요약에 "메타 ✓/✗" 컬럼 추가.
- Phase 5 성공 로그에 메타 생성 카운트 + 웹 필터 제외 카운트 표시.

### Compatibility
- v0.3 이하 draft 를 `/spec-resume` 로 재개하면 `metadata` 필드가 없다 → 빈 구조로 fallback, Phase 3.5 재실행 없음 (경고 출력).
- `project_context_path` 미설정 시 Phase 3.5 전체 스킵 (기존 v0.3 동작 그대로).
- 기존 pytest 회귀 없음 (총 59 tests pass; 신규 10 / 기존 49).

## [0.3.0] - 2026-04-21

### Added
- Phase 2-6 **웹 피처 필터링 단계** — 네이티브 개발팀이 웹 전용 피처를 한 번에 제외 (`excluded: true` 플래그). 제외된 피처는 Phase 3/4/5 에서 완전 스킵, Notion 에 생성 안 됨.
- Claude 힌트 — 각 피처 옆에 "웹 같음", "혼합" 등 짧은 태깅 (자동 제외 아님, 사용자 판단 보조용).
- Resume 모드에 `excluded_ids` 직렬화 — 중단된 세션 복구 시 제외 상태 유지.

### Changed
- Phase 3/4/5 워크플로우: `excluded == false` 인 피처만 처리.
- `features.json` 스키마: 각 피처 객체에 `excluded: bool` 필드 추가 (기본 false).

### Compatibility
- v0.2 이전 초안은 `excluded_ids` 헤더가 없어도 resume 정상 동작 (하위 호환).
- Python 스크립트 변경 없음, 기존 18 pytest 그대로 통과.

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
