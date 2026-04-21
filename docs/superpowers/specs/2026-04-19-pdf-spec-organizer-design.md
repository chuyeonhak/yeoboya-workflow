# yeoboya-workflow 플러그인 — PDF 스펙 정리 기능 설계

- 작성일: 2026-04-19
- 플러그인: `yeoboya-workflow` (umbrella, 기능 확장 예정)
- 첫 기능: `pdf-spec-organizer`
- 상태: Draft (사용자 검토 대기)

## 배경

iOS/Android 팀이 기획자로부터 복합 PDF(PRD + 디자인 시안 + 유저 플로우)를 받아 스펙을 읽는데, 양 팀이 각자 해석해서 엣지케이스가 구현 단계에서야 드러남. PDF → 정리된 Notion 피처 페이지로 변환하면서 **명세 누락을 사전에 체크**하고, 양 팀이 **같은 페이지에서 노트를 공유**하는 플러그인이 필요.

## 목표 (v1)

- 개발자가 `/spec-from-pdf <path>` 를 실행하면 정리된 Notion 피처 페이지가 생성된다.
- 체크리스트 기반으로 **명세 누락 항목**(에러/빈상태/오프라인/권한/로딩/접근성)이 피처별로 표시된다.
- iOS/Android 개발자가 같은 피처 페이지에 **플랫폼별 노트**를 남길 수 있다.
- 구조는 확장 가능해서 나중에 `source-of-truth` 교차 확인(코드베이스 + Notion 스펙 DB)이 붙을 수 있다.

## 비목표 (v1 제외)

- 기존 앱/스펙과의 충돌 체크 (v2로 연기, 단 확장 포인트만 남김)
- PDF 외 입력 (Notion/Figma/Slack 링크 등 — v3 가능성)
- checklist.yaml 의 severity/조건부 로직 (v2로 연기)

## 사용자 & 트리거

- **사용자**: iOS/Android 개발자 (기획자에게 PDF 받은 당사자가 직접 실행)
- **트리거**: `/spec-from-pdf <path>` 슬래시 커맨드
- **플래그**:
  - `--fast` : 개입①(구조화 확인), ③(충돌 처리) 자동 통과, 개입②(노트)만 강제
- **별도 커맨드** `/spec-resume` 가 중단된 세션 이어받기 담당 (아래 "추가 커맨드" 참조)

## 아키텍처 & 파일 구조

```
yeoboya-workflow/
├── .claude-plugin/
│   └── plugin.json              # name, description, version, keywords
├── commands/
│   ├── spec-from-pdf.md         # 진입점 (인자 검증 → skill 호출)
│   ├── spec-update.md           # 기존 Notion 페이지에 노트/체크만 갱신
│   └── spec-resume.md           # 중단된 세션 이어하기
├── skills/
│   └── pdf-spec-organizer/
│       ├── SKILL.md             # 전체 워크플로우 정의
│       ├── references/
│       │   ├── notion-schema.md     # Notion 피처 DB 스키마 정의
│       │   ├── review-format.md     # 미리보기 포맷 규약
│       │   ├── conflict-policy.md   # 충돌 처리 정책(병합 기본, 덮어쓰기 escape hatch)
│       │   └── source-of-truth.md   # v2 확장 포인트 스케치
│       └── scripts/
│           ├── parse-pdf.py         # 텍스트 추출 (PyPDF2)
│           ├── ocr-fallback.py      # Tesseract OCR fallback
│           └── pii-scan.py          # PII 패턴 감지 (경고용)
├── config/
│   └── pdf-spec-organizer/
│       ├── checklist.yaml       # 누락 체크 항목 (커스터마이즈 가능)
│       └── notion-schema.yaml   # DB 스키마 정의 (자동 생성 시 사용)
├── yeoboya-workflow.config.json  # ★ 프로젝트 레포에 커밋 — 팀 공유 DB ID
├── README.md
└── CHANGELOG.md
```

### 핵심 설계 원칙

- `skills/`, `commands/`, `config/` 아래 **기능별 독립 디렉토리** → 새 기능 추가 시 기존 파일 건드리지 않음
- 커맨드는 얇은 진입점, 실제 로직은 skill
- Notion 접근은 `mcp__claude_ai_Notion__*` MCP 재사용, 플러그인이 직접 API 안 호출
- **설정 파일은 `${CLAUDE_PLUGIN_ROOT}/config/pdf-spec-organizer/*.yaml` 을 skill에서 동적 로드**
- **팀 공유 DB ID 는 프로젝트 레포 루트의 `yeoboya-workflow.config.json` 에 커밋** (개인별 표류 방지)
- 사용자별 일시 상태는 `${CLAUDE_PLUGIN_DATA}` (세션 draft 등)

## 데이터 플로우

```
[사용자] /spec-from-pdf ~/Downloads/feature-spec.pdf [--fast]
     ↓
[커맨드] 경로 검증 → 절대경로 정규화 → PDF 해시 계산 → skill 호출
     ↓
[Phase 1 — 파싱] (자동)
  scripts/parse-pdf.py: 텍스트 + 이미지 추출 → JSON
  텍스트량이 임계치 미만이면 scripts/ocr-fallback.py (Tesseract) 실행
  scripts/pii-scan.py: PII 패턴 감지 → 발견 시 경고 (차단 아님)
  이미지는 임시 폴더에 저장 (Phase 5에서 Notion 파일 업로드)
     ↓
[Phase 2 — 구조화 + 개입 ①] (대화형)
  Claude가 피처 N개로 분류 + 플랫폼 태깅
  → 사용자 확인: y / 쪼개기 / 합치기 / 리네이밍 / edit(에디터 fallback)
  → 플랫폼 태깅은 명시적 확인 필수 (--fast 에서도 이 단계는 생략 안 함)
     ↓
[Phase 3 — 누락 체크] (자동)
  checklist.yaml 로드 → 피처별 applies_to 교집합으로 필터링 → 누락 항목 목록화
  출력 끝에 안내: "의도된 제외는 다음 단계 노트에 적어주세요"
     ↓
[Phase 4 — 개발자 노트 + 미리보기 + 개입 ②] (대화형 / 에디터)
  요약 + 체크 + 빈 노트 섹션(iOS/Android/공통)을 /tmp/spec-draft-<hash>-<ts>.md 렌더
  → 사용자: 플랫폼별 노트 작성 (자신의 플랫폼 섹션만 채움)
  → 최종 확인: y / edit / 취소
     ↓
[Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③]
  Notion 피처 DB에 동명 피처 조회
  존재하면:
    - "최근 생성자 + 생성일 + 같은 PDF 해시 여부" 표시
    - 사용자 선택: [병합(기본)] / 덮어쓰기 / 새 버전 / 취소
      - 병합: 내가 작성한 플랫폼 섹션만 append, 타 플랫폼 노트 보존
      - 새 버전: 기존 페이지에 `이전버전` Relation 으로 연결, 새 페이지 생성
  5분 내 같은 PDF 해시 실행 기록 있으면 "동시 실행 경고" 표시
  (기록 출처: `${CLAUDE_PLUGIN_DATA}/draft-registry.json`)
  이미지를 Notion 파일 API 로 업로드 → 페이지 생성/갱신
  성공 시 URL 출력, /tmp 초안은 TTL 정책에 따라 예약 삭제
```

### 개입 포인트 요약

| # | 단계 | 무엇을 | `--fast` 동작 |
|---|---|---|---|
| ① | Phase 2 후 | 피처 경계 + 플랫폼 태깅 확인 | 피처 경계 자동 통과, **플랫폼 태깅은 여전히 명시 확인** |
| ② | Phase 4 | 개발자 노트 작성 | 항상 강제 (유일한 인간 가치 입력) |
| ③ | Phase 5 직전 | 충돌 처리 | 기본값(병합) 자동 적용, 파괴적 선택만 확인 |

## Notion 피처 DB 스키마

### DB 속성 (Properties)

| 속성 | 타입 | 설명 |
|---|---|---|
| **이름** | Title | 피처명 |
| **플랫폼** | Multi-select | `iOS`, `Android`, `공통` |
| **상태** | Select | `Draft`, `In Review`, `Ready`, `In Dev`, `Done` |
| **원본 PDF** | Text | **파일명만 저장** (홈 경로 노출 방지) |
| **PDF 해시** | Text | SHA-256 short hash (동시 실행 감지/버전 매칭용) |
| **소스 링크** | URL (Multi) | PRD / Jira / Figma URL 등 |
| **이전 버전** | Relation (self) | 새 버전 생성 시 연결 |
| **관련 피처** | Relation (self) | 피처 의존/충돌 추적 (v2 source-of-truth 기반) |
| **생성자** | Person | 플러그인 실행자 |
| **생성일** | Created time | 자동 |
| **누락 항목** | Multi-select | checklist.yaml 의 id 값들 |

> `버전(Text "v2")` 은 검색 깨짐 우려로 제외. 대신 `이전버전(Relation)` 사용.

### 페이지 본문 블록 구조

```
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

### 팀 DB 공유 전략

- 프로젝트 레포 루트에 **`yeoboya-workflow.config.json` 커밋**:
  ```json
  {
    "pdf_spec_organizer": {
      "notion_database_id": "<feature-db-id>",
      "parent_page_id": "<parent-page-id>"
    }
  }
  ```
- 파일이 없으면 skill 이 "팀 리드가 먼저 셋업하고 커밋하세요" 안내. 개인 임의 셋업 차단.
- 최초 셋업 명령(팀 리드용): 부모 페이지 URL 입력 → DB 자동 생성 → `yeoboya-workflow.config.json` 초안 출력(사용자가 커밋).

## `checklist.yaml` 포맷 (v1)

```yaml
version: 1

items:
  - id: error_cases
    name: 에러 케이스
    description: 네트워크/서버 오류 발생 시 UX
    applies_to: [iOS, Android, 공통]

  - id: empty_state
    name: 빈 상태
    description: 데이터 없거나 초기 진입 시 화면
    applies_to: [iOS, Android, 공통]

  - id: offline
    name: 오프라인 처리
    description: 네트워크 끊김 시 동작 (캐시 / 재시도)
    applies_to: [iOS, Android, 공통]

  - id: permissions
    name: 권한
    description: 카메라/위치/알림/사진 권한 요청 및 거부 플로우
    applies_to: [iOS, Android]

  - id: loading
    name: 로딩 상태
    description: 비동기 작업 인디케이터 / 스켈레톤
    applies_to: [iOS, Android, 공통]

  - id: a11y
    name: 접근성
    description: 스크린리더, 컬러 대비, 터치 타겟 크기
    applies_to: [iOS, Android, 공통]
```

- 필수 필드: `id`, `name`, `description`, `applies_to`
- `version` 필드로 스키마 진화 관리
- v2 확장: `severity`, `only_if` 조건, 피처 타입별 필터

## 에러 처리

| 단계 | 실패 원인 | 처리 |
|---|---|---|
| 커맨드 진입 | PDF 경로 없음 / 파일 아님 | 즉시 중단, 구체 메시지 |
| Phase 1 파싱 | PDF 암호화/손상 | 중단, 힌트 제공 |
| Phase 1 의존성 | PyPDF2 / Tesseract 없음 | 중단, 설치 명령 안내 |
| Phase 1 OCR | 이미지 전용 페이지 텍스트 추출 실패 | Tesseract fallback, 품질 경고 표시 |
| Phase 1 PII | 이메일/전화/주민번호 감지 | 경고 출력 (차단 아님), 사용자 진행 확인 |
| Phase 2 구조화 | 빈 피처 리스트 / 파싱 실패 | 재확인 → 취소 |
| Phase 2 대화형 | 사용자 취소 | /tmp 초안 정리, 종료 |
| Phase 3 체크 | checklist.yaml 없음/파싱 실패 | 기본값 fallback, 경고 |
| Phase 4 에디터 | 비정상 종료 / 빈 저장 | 노트 없이 진행 확인 |
| Phase 5 DB 미설정 | 레포에 `yeoboya-workflow.config.json` 없음 | 팀 리드 셋업 가이드, 중단 |
| Phase 5 Notion 조회 | MCP 실패 / 네트워크 | 재시도 1회 → 실패 시 초안 보존 |
| Phase 5 이미지 업로드 | Notion 파일 API 실패 | 해당 이미지는 캡션만 남기고 경고 |
| Phase 5 퍼블리시 중 부분 실패 | 페이지는 만들어졌는데 본문 추가 실패 | `/spec-resume --resume-latest` 로 이어쓰기 가이드 |

### 공통 정책

- Phase 5 전까지 Notion 부작용 없음 → 취소 안전
- 에러 메시지 형식: "원인 + 다음 행동 제안"
- `/tmp/spec-draft-<hash>-<ts>.md` TTL:
  - 성공 퍼블리시: 3일 후 자동 삭제
  - 실패/취소: 7일 후 자동 삭제
  - `${CLAUDE_PLUGIN_DATA}/draft-registry.json` 에 TTL 관리
- 초안 파일에 **Phase 진행 상태 직렬화** (어디까지 성공했는지) → `/spec-resume` 가 이어받음

## 보안 / 개인정보

- `원본 PDF` 속성은 **파일명만** 저장 (홈 경로 노출 방지)
- Phase 1 PII 스캔: 이메일/전화/주민번호 패턴 감지 시 경고
- `/tmp` 초안 TTL 정책 (위 참조)
- PDF 원본은 Notion에 업로드하지 않음 (참조만). 사용자 요청 시에만 명시적 업로드

## 테스트 전략 (v1)

### 수동 QA (`docs/manual-qa.md` 체크리스트)

- [ ] 정상 PDF 전체 플로우 (텍스트 중심)
- [ ] 정상 PDF (이미지/스크린샷 중심, OCR 경로)
- [ ] 각 개입 포인트에서 "취소" → Notion 변경 없음
- [ ] checklist 항목 제거 후 실행 → 스킵 확인
- [ ] 같은 스펙 재실행 → 병합 기본값 동작 확인
- [ ] 5분 내 동일 PDF 해시 재실행 → 경고 표시
- [ ] 다른 플랫폼 개발자가 병합 실행 → 타 플랫폼 노트 보존 확인
- [ ] 잘못된 경로 / 암호 PDF / 빈 PDF → 에러 메시지
- [ ] `--fast` 플래그 → 개입 ① ③ 자동 통과, 노트는 강제
- [ ] `--resume-latest` → 중단 지점부터 이어받기
- [ ] `/spec-update <notion-url>` → 노트/체크 갱신
- [ ] `yeoboya-workflow.config.json` 없을 때 → 셋업 가이드

### 자동화

- `scripts/parse-pdf.py`, `scripts/ocr-fallback.py`, `scripts/pii-scan.py` 는 `scripts/tests/` 에서 Python 단위 테스트
- `samples/` 디렉토리에 샘플 PDF 1-2개 + 기대 출력 스냅샷

### 테스트 범위 밖

- Notion API / MCP 자체 동작 (외부 의존)
- Claude 판단 품질 (프롬프트 튜닝 영역)

## 확장 포인트 (v2 이후)

1. **Source-of-truth 인터페이스** (v2 충돌 체크)
   - `references/source-of-truth.md` 에 인터페이스 스케치
   - 입력: 제안된 피처 리스트 + `관련 피처` Relation
   - 출력: 기존 Notion 피처 DB 쿼리 결과 + 코드베이스 grep 결과 요약
   - Claude 가 충돌/중복/유사 피처 판단

2. **Checklist 확장** (v2)
   - `severity`, `only_if` 조건 추가. `version: 2` 로 스키마 진화

3. **다른 워크플로우 기능 추가** (umbrella 전략)
   - `skills/<new>/`, `commands/<new>/`, `config/<new>/` 독립 추가

4. **PDF 외 입력** (v3)
   - `/spec-from-notion <url>`, `/spec-from-figma <url>` — Phase 2-5 공유, Phase 1만 분기

## 추가 커맨드 요약

- `/spec-from-pdf <path> [--fast]` : 메인 진입점
- `/spec-update <notion-url>` : 기존 페이지의 노트/체크 갱신 (Phase 2/3/5 스킵, 4만)
- `/spec-resume [--resume-latest | <draft-path>]` : 중단된 세션 이어하기

## 오픈 이슈 (구현 계획 단계에서 결정)

- Notion 파일 업로드 API 구체 스펙 확인 — 사용자 환경 MCP 가 파일 업로드 지원하는지 점검 필요
- PDF 해시 계산 방식: 파일 바이트 전체 SHA-256 short (앞 12자)
- `--fast` 플래그 동작 시 플랫폼 태깅 확인을 생략 안 함 — 구현 시 명확한 UX 필요
- Tesseract 의존성: macOS `brew install tesseract` 가이드, 없을 때 설치 명령 출력
