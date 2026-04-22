# TODO — spec-organizer wrapper v1.0

> 설계/플랜 100% 완료, 구현 12.5% (PR 1/8) 완료. 작성일 2026-04-22.

## 🔗 핵심 참조

- **스펙**: `docs/superpowers/specs/2026-04-22-spec-organizer-wrapper-design.md`
- **플랜**: `docs/superpowers/plans/2026-04-22-0{1-8}-*.md`

## 🚦 진행 상태

- [x] **PR 1** — common 코어 추출 (`2026-04-22-01-common-core-extraction.md`) — **main 에 머지됨** (`1c1385e`)
- [ ] **PR 2** — routing.yaml + dispatcher + 24셀 회귀 테스트 (`2026-04-22-02-routing-dispatcher.md`) — 3일
- [ ] **PR 3** — work-type-schemas + field_collector + Notion 검색 (`2026-04-22-03-schemas-field-collector.md`) — 3일
- [ ] **PR 4** — spec-organizer wrapper 스킬 + Skill tool 연쇄 (`2026-04-22-04-spec-organizer-wrapper.md`) — 2일
- [ ] **PR 5** — bug-spec-organizer 스킬 (`2026-04-22-05-bug-spec-organizer.md`) — 3일
- [ ] **PR 6** — enhancement-spec-organizer 스킬 (`2026-04-22-06-enhancement-spec-organizer.md`) — 3일
- [ ] **PR 7** — checklist.yaml 이동 + `applies_to_work_type` 필터 (`2026-04-22-07-checklist-migration.md`) — 1일
- [ ] **PR 8** — 에러 처리 (Pydantic/backoff/OCR 차단) + deprecation shim (`2026-04-22-08-error-handling.md`) — 2일

총 남은 작업: **17 영업일 (≈ 3.5주)**. PR 5, 6, 7 은 PR 4 이후 병렬 가능.

## 🚨 즉시 처리 권고 (선택)

- [ ] 로컬 `main` 이 `origin/main` 보다 **11 commits 앞** — 필요 시 `git push origin main`

## 📝 다음 세션에서 재개하는 법

1. `cd /Users/chuchu/testPlugin`
2. `git worktree add .claude/worktrees/spec-organizer-pr2 -b feature/spec-organizer-pr2`
3. worktree 안에서 `docs/superpowers/plans/2026-04-22-02-routing-dispatcher.md` 플랜대로 TDD 실행
4. 필요 시 superpowers:subagent-driven-development 스킬 재호출

## 🎯 v1 완료 기준 (성공 정의)

- [ ] 기존 13개 단위 테스트 회귀 없음 (현재 ✅ 59 통과)
- [ ] 신규 단위 테스트 15+ PASS
- [ ] `evals/routing-matrix.json` 24/24 PASS
- [ ] 각 신규 스킬 trigger-eval 95%+ 정확도
- [ ] 4개 E2E 시나리오 (PDF 새 기능 / bug 최소 / enhancement URL / resume)
- [ ] `yeoboya-workflow.config.json` 변경 없이 기존 사용자 동작 확인
- [ ] README / CHANGELOG v1.0.0 업데이트

## ⏭ v1.5 이후 (이번 릴리스 제외)

- [ ] `common/scripts/requirements.txt` 분리 (PDF 전용 deps 이동)
- [ ] `/spec-migrate-work-type` 배치 커맨드 (기존 Notion 페이지 backfill)
- [ ] 기존 deprecated 커맨드 (`/spec-from-pdf`, `/spec-update`, `/spec-resume`) 완전 제거
- [ ] `enrich_features.py` 등 docstring 에서 "pdf-spec-organizer" 명시 제거
- [ ] brainstorming 핸드오프를 파일 기반으로 리팩터 (Skill tool 연쇄 → 파일)

## ⏭ v2 이후 (장기)

- [ ] 외부 링크 파싱 (GitHub Issue/Linear/Slack URL → 자동 필드 채움)
- [ ] PII 스캔을 자유 서술 텍스트까지 확장
- [ ] 다국어 지원 (영어 PDF 파싱 + 프롬프트 i18n)
- [ ] `/spec-promote` (work_type 변경 허용)
- [ ] `image_only + bug_fix` OCR 경로 (QA 스크린샷 단독 제보)
