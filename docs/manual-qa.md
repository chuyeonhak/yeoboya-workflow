# 수동 QA 체크리스트 — pdf-spec-organizer

각 릴리스 전 반드시 확인. 샘플 PDF 는 `skills/pdf-spec-organizer/scripts/tests/samples/` 사용.

## 사전 준비

- [ ] Python 의존성 설치 완료 (`pip install -r skills/common/scripts/requirements.txt`)
- [ ] Tesseract 설치 완료 (`brew install tesseract tesseract-lang`)
- [ ] `yeoboya-workflow.config.json` 프로젝트 레포 루트에 존재
- [ ] Claude Code 에 Notion MCP 연결됨

## 정상 플로우

### 텍스트 위주 PDF
- [ ] `/spec-from-pdf tests/samples/minimal.pdf` 실행
- [ ] Phase 1~5 모두 통과
- [ ] Notion 페이지가 생성되고 URL 이 출력됨
- [ ] 페이지 열어보면 섹션 구조가 `references/review-format.md` 와 일치
- [ ] 속성(플랫폼/상태/PDF_해시/누락_항목) 모두 채워져 있음

### 이미지 위주 PDF
- [ ] `/spec-from-pdf tests/samples/image_only.pdf` 실행
- [ ] OCR fallback 이 트리거되고 "품질 낮을 수 있음" 경고 출력
- [ ] Notion 페이지에 이미지가 포함됨 (placeholder 라도)

### `--fast` 플래그
- [ ] `/spec-from-pdf tests/samples/minimal.pdf --fast` 실행
- [ ] 개입 ①(피처 경계)는 자동 통과, 플랫폼 태깅 확인은 여전히 발생
- [ ] 개입 ②(노트)는 강제 — 에디터 열림
- [ ] 개입 ③(충돌)은 기본값(병합) 자동 적용. 덮어쓰기/새버전은 발생 안 해야 정상

## 취소 경로

- [ ] Phase 2 에서 `c` → Notion 에 아무것도 안 만들어졌는지 확인
- [ ] Phase 4 에서 `c` → 동일
- [ ] Phase 5 충돌 시 `4) 건너뛰기` → 해당 피처만 스킵, 나머지 정상

## 동시 실행 감지

- [ ] 같은 PDF 로 두 세션 빠르게 실행 (5분 이내)
- [ ] 두 번째 실행에 "5분 내 동일 PDF" 경고 표시

## 병합 동작

- [ ] 사용자 A 가 피처 생성 (iOS 노트 작성)
- [ ] 사용자 B 가 같은 PDF 로 병합 실행 (Android 노트 작성)
- [ ] Notion 페이지에 iOS + Android 노트 **둘 다** 남아 있음

## 에러 케이스

- [ ] 존재하지 않는 경로 → 구체 에러 메시지
- [ ] 암호화 PDF → 중단 + 힌트
- [ ] PII 패턴 포함 PDF → 경고 후 사용자 확인
- [ ] `yeoboya-workflow.config.json` 없음 → 셋업 가이드 + 중단
- [ ] Notion MCP 실패 → 재시도 1회 후 초안 보존 + `/spec-resume` 가이드

## Resume

- [ ] Phase 3 에서 Ctrl+C → `/spec-resume --resume-latest` 로 Phase 4 부터 재개
- [ ] 초안 파일 직접 지정 `/spec-resume <path>` 동작 확인

## Update

- [ ] 기존 페이지 URL 에 `/spec-update <url>` → Phase 4 만 실행됨
- [ ] 내 플랫폼 노트만 갱신, 타 플랫폼 노트 보존

## TTL / 정리

- [ ] 성공 실행 후 3일 지난 초안이 gc 로 자동 삭제되는지 (시간 조작 필요 시 `draft_registry gc` + ttl-seconds 로 시뮬)
- [ ] 실패 실행 후 7일 TTL 확인

## 알려진 이슈

- Notion MCP 의 로컬 이미지 업로드 미지원 시 placeholder URL + 캡션으로 대체됨. v0.2 에서 S3/imgur 중계 계획.
