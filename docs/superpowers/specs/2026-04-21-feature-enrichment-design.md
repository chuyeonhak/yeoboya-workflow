# Feature Enrichment 설계

- 작성일: 2026-04-21
- 대상: `pdf-spec-organizer` v0.3.x → v0.4.0
- 상태: Draft (사용자 검토 대기)
- Supersedes: `2026-04-21-codebase-diff-filter-design.md` (사용자 요구 재해석 반영)

## 배경

PDF 기획서를 `/spec-from-pdf` 로 정리하면 피처 리스트와 누락 체크까지 나오지만, **개발 착수를 바로 하기에는 부족**하다. 개발자가 추가로 필요한 정보:

- 이 피처 구현에 어느 정도 걸릴까? (기간 추정)
- 타부서(백엔드/디자인/QA)에서 받아야 할 것 또는 조율할 것이 있는가?
- 기획서에 누락된 맥락(에러 흐름, 경계 조건)이 있는가?
- 우리 팀이 다른 팀에 요청해야 할 것이 있는가?

이 메타 정보를 Claude 가 **project-context.md**(팀 구성/과거 개발 사례/타팀 연락 채널)와 **iOS/Android 코드베이스**를 참고해 자동 제안하고, 개발자가 Phase 4 (개발자 노트) 편집 단계에서 검토/수정한다.

최종 산출물은 "개발 실행 가능한 Notion 스펙" 이며, 이후 `superpowers:writing-plans` → `superpowers:executing-plans` 로 넘겨 실제 구현 플랜이 된다.

## 목표

- Phase 3 (누락 체크) 직후 "피처 메타 정보 생성" 단계(Phase 3.5) 추가
- Config 에 `project_context_path` + `codebase_roots` 선언
- 각 피처의 메타 정보는 features.json → 초안 md → Notion Toggle 순으로 전파
- Phase 4 에서 개발자가 검토/수정
- Phase 5 Notion 페이지의 각 Toggle 에 "📊 개발 계획 메타" 섹션이 포함됨

## 비목표 (의도적 단순화)

- **자동 승인 안 함** — Claude 는 제안, 개발자가 Phase 4 에서 최종 판단
- **정확도 책임 지지 않음** — 기간 추정은 힌트, 팀 리더가 최종 조정
- **Notion 속성 신규 추가 안 함** — 본문 Toggle 내 섹션으로만
- **project-context.md 없으면 기능 스킵** — fallback 없음. v0.5 에서 `--no-enrich` 플래그 검토
- **메타 이력 보존 안 함** — 실행마다 새로 생성. 과거 실행과의 diff 는 v0.5+
- **기간을 숫자(days)로 강제 안 함** — 자유 문자열 ("2-3일", "1주일", "복잡도 따라 1-3주")

## 데이터 모델

### `features.json` 확장

각 피처에 `metadata` 객체 추가:

```json
{
  "feature_id": "uuid-...",
  "name": "알림 설정",
  "platform": ["iOS", "Android"],
  "excluded": false,
  "excluded_reason": null,
  "metadata": {
    "estimated_effort": "iOS 2-3일, Android 2-3일",
    "external_dependencies": [
      {
        "team": "백엔드",
        "item": "알림 설정 저장 API (POST /users/me/notification-settings)",
        "blocking": true,
        "note": "스키마는 백엔드와 협의 필요"
      }
    ],
    "planning_gaps": [
      "API 실패 시 UI 처리 정의 없음",
      "이전 설정값을 어디서 가져올지 명시 없음"
    ],
    "cross_team_requests": [
      {
        "team": "디자인",
        "item": "토글 off 상태 스타일 확정",
        "by": "개발 착수 전"
      }
    ]
  }
}
```

### 필드 정의

| 필드 | 타입 | 설명 |
|---|---|---|
| `estimated_effort` | string | 자유 텍스트. 플랫폼별 기간 기재 권장. 빈 문자열 가능 |
| `external_dependencies` | list of `{team, item, blocking, note}` | **타팀에서 받아야 할 것.** `blocking: true` 는 이게 없으면 개발 시작 불가 |
| `planning_gaps` | list of string | 기획서에 빠진 요구사항 (피처 맥락 기반 자유 지적) |
| `cross_team_requests` | list of `{team, item, by}` | **우리 팀이 다른 팀에 요청할 것.** `by` 는 필요 시점 |

### Phase 3 누락 체크와의 관계

- Phase 3: 6개 고정 카테고리 (에러/빈상태/오프라인/권한/로딩/접근성) 기계적 체크 — **유지**
- `planning_gaps`: 피처 맥락 기반 자유 지적 — Phase 3.5 에서 Claude 가 생성

두 관점이 겹칠 수 있지만(에러 케이스 누락을 둘 다 지적할 수 있음) 서로 다른 층위이므로 **별개 섹션으로 보존**. Notion 본문에 "누락 체크" (체크리스트 형식) + "기획 누락 포인트" (자유 불릿) 두 섹션 모두 등장.

### `excluded` 피처 처리

`excluded == true` (웹 필터) 피처는 Phase 3.5 전체 스킵. `metadata` 필드 생성 안 함. 기존 excluded 스킵 로직과 동일.

## Config 확장

`yeoboya-workflow.config.json`:

```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "...",
    "notion_data_source_id": "...",
    "parent_page_id": "...",
    "project_context_path": "./docs/project-context.md",
    "codebase_roots": {
      "ios": "~/repos/myapp-ios",
      "android": "~/repos/myapp-android"
    }
  }
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `project_context_path` | 선택 (권장) | 없으면 Phase 3.5 스킵. 경로는 config 파일 기준 상대 경로 허용. `~` 확장 허용 |
| `codebase_roots.ios` | 선택 | iOS 레포 경로. 없으면 iOS 피처 메타 생성에 코드베이스 힌트 미사용 |
| `codebase_roots.android` | 선택 | Android 레포 경로. 동일 |

Phase 3.5 는 세 단계로 동작:
1. `project_context_path` 있음 + `codebase_roots` 있음 → 풀 메타 생성
2. `project_context_path` 있음 + `codebase_roots` 없음 → project-context + 피처 설명만으로 메타 생성. Phase 3.5 진입 직후 한 번만 경고 출력:
   ```
   ℹ️  codebase_roots 가 설정되지 않아 코드 힌트 없이 메타를 생성합니다.
     기간 추정 신뢰도가 낮을 수 있습니다. Phase 4 에서 개발자 검토를 권장합니다.
   ```
3. `project_context_path` 없음 → Phase 3.5 전체 스킵 (경고)

## `project-context.md` 포맷

팀이 1회 작성 후 커밋. 자유 마크다운, **권장 섹션**:

```markdown
# Project Context

## Team
- iOS: 2명 (Junior 1, Mid 1)
- Android: 1명 (Senior)
- 백엔드/디자인/QA: 별도 조직

## Current Sprint / Roadmap
- 2026 Q2: 회원 유입 개선 피처 중심
- 진행 중: 로그인 A/B, 프로필 개선

## Past Effort References
- 간단 UI (기본 컴포넌트): iOS 1일, Android 1일
- 신규 플로우 (2-3 화면 + API): iOS 3-5일, Android 3-5일
- A/B 테스트 추가: +1일
- 네이티브 기능 (카메라/권한): iOS 2-3일, Android 3-5일

## External Teams & Channels
- 백엔드: Slack #backend, 리드 @jieun, API 변경 최소 1주 전 요청
- 디자인: Notion "디자인 리소스 DB", 새 스타일 요청 2-3일
- QA: 매주 월 QA 회의, 새 피처는 전주 금 요청

## Known Constraints
- iOS 15+ / Android API 24+
- 푸시는 FCM 중앙화, APNs 직접 호출 금지
- 결제는 IAP 만 허용
```

- 섹션은 **권장** (강제 아님). 팀이 필요에 따라 추가/축소
- Claude 는 "있는 만큼" 참고
- 최대 파일 크기: 첫 **500 줄** 까지 사용 (그 이상이면 경고 + 절삭)
- 템플릿은 `references/project-context-template.md` 로 제공

## Phase 3.5 플로우

Phase 3 (누락 체크) 직후, Phase 4 (노트 + 미리보기) 이전에 삽입.

### 3.5-a. 선행 조건 확인

```
IF project_context_path 설정 없음 OR 경로 존재 안 함 OR 파일 비어있음
    경고: "project-context 미설정 — 피처 메타 정보 생성 스킵. 설정 가이드: README.md"
    Phase 4 로 진입
ELSE
    project-context.md 로드 (500줄 초과 시 절삭 + 경고)
    Phase 3.5-b 진행
```

Phase 3.5 실패는 전체 실패 아님. 항상 **스킵 가능**하게.

### 3.5-b. 코드베이스 힌트 수집 (선택)

`codebase_roots` 설정된 플랫폼에 대해서만:

```bash
timeout 30 grep -rn \
  --include="*.swift" --include="*.m" --include="*.h" \
  --exclude-dir=".build" --exclude-dir="Pods" \
  --exclude-dir="DerivedData" --exclude-dir=".git" \
  -e "<keyword1>" -e "<keyword2>" -e "<keyword3>" \
  "<ios_root>" | head -10
```
Android 도 동일 (`.kt`/`.java`/`.xml`, `build`/`.gradle`/`.git` 제외).

- 각 피처의 키워드 2-3개는 Claude 가 피처 name/requirements 에서 추출
- grep 결과 상위 10 줄을 "관련 코드 힌트" 로 Claude 메타 생성 프롬프트에 포함
- grep 타임아웃/오류 → 해당 피처는 코드 힌트 없이 메타 생성

### 3.5-c. Claude 메타 정보 생성

`excluded == false` 피처마다 Claude 에게 한 번씩:

```
다음 정보로 이 피처의 개발 계획 메타 정보를 JSON 으로 생성.

[피처]
이름: <name>
플랫폼: <platform>
요약: <summary>
요구사항:
<requirements>

[Phase 3 누락 체크 결과]
누락: <missing>
명시: <satisfied>

[프로젝트 컨텍스트]
<project-context.md 본문>

[관련 코드 힌트]  # codebase_roots 설정 시만
<grep 결과 상위 10 줄>

요청 JSON 스키마:
{
  "estimated_effort": "string (플랫폼별 기간 권장)",
  "external_dependencies": [{"team": "...", "item": "...", "blocking": bool, "note": "..."}],
  "planning_gaps": ["string", ...],
  "cross_team_requests": [{"team": "...", "item": "...", "by": "string"}]
}

규칙:
- 빈 항목은 [] (빈 리스트) 또는 "" (빈 문자열) 허용
- 팀명은 project-context 의 "External Teams & Channels" 에서 언급된 이름 사용
- estimated_effort 는 project-context 의 "Past Effort References" 를 참고해 추정
- planning_gaps 는 Phase 3 누락 체크와 중복돼도 OK (관점이 다름)
```

Claude 응답을 JSON 파싱:
- 성공 → features.json 의 해당 피처 `metadata` 필드에 병합
- 파싱 실패 → 해당 피처 `metadata` 를 빈 구조 (`{"estimated_effort": "", "external_dependencies": [], "planning_gaps": [], "cross_team_requests": []}`) 로 fallback + 경고:
  ```
  ⚠️  피처 <name> 의 메타 생성 실패 (JSON 파싱 에러). 빈 값으로 계속합니다. Phase 4 에서 수동 작성하세요.
  ```

### 3.5-d. 결과 요약 출력

```
피처 메타 정보 생성 완료 (excluded 제외 3개 피처):

  1. 알림 설정 화면
     예상 기간: iOS 2-3일, Android 2-3일
     타팀 의존: 백엔드 — 알림 설정 저장 API (blocking)
     기획 누락: API 실패 UI, 이전 설정값 출처
     타팀 요청: 디자인 — 토글 off 상태 (개발 착수 전)

  2. 푸시 권한 요청 플로우
     예상 기간: iOS 1-2일, Android 2일
     타팀 의존: (없음)
     기획 누락: 권한 거부 시 재요청 UX
     타팀 요청: (없음)

  3. ...

검토/수정은 Phase 4 (개발자 노트) 에서 진행됩니다.
계속하려면 Enter.
```

이 시점에선 **확인만**. 편집은 Phase 4 에서.

`--fast` 모드: 프롬프트 스킵, 바로 Phase 4.

## Phase 4 (개발자 노트) 확장

### 4-2. 초안 md 렌더 확장

각 피처 Toggle 내에 기존 요구사항 뒤, 기존 노트 섹션 앞에 **메타 섹션** 삽입:

```markdown
### 1. 알림 설정 화면 {toggle="true"}
<!-- feature_id: <uuid> -->

**플랫폼:** iOS, Android
**요약:** 사용자가 알림 on/off 를 설정한다.

**요구사항:**
- 푸시 알림 on/off 토글
- 이메일 알림 on/off 토글
- 변경 즉시 서버에 반영

**누락 체크 (Phase 3):**
- ⚠️ 누락: 에러 케이스, 오프라인 처리
- ✓ 명시: 빈 상태, 로딩 상태, 접근성

<!-- meta_start -->
#### 📊 개발 계획 메타

**예상 기간:** iOS 2-3일, Android 2-3일

**타팀 의존성:**
- 🚫 [백엔드] 알림 설정 저장 API (POST /users/me/notification-settings) — blocking
  - 스키마는 백엔드와 협의 필요

**기획 누락 포인트:**
- API 실패 시 UI 처리 정의 없음
- 이전 설정값을 어디서 가져올지 명시 없음

**타팀 요청 사항:**
- [디자인] 토글 off 상태 스타일 확정 (개발 착수 전)

> ℹ️ Claude 가 project-context 기반으로 제안한 값입니다. 필요 시 아래 마커 내에서 자유 편집하세요.
<!-- meta_end -->

<!-- notes_ios_start -->
## iOS 노트
<empty-block/>
<!-- notes_ios_end -->

<!-- notes_android_start -->
## Android 노트
<empty-block/>
<!-- notes_android_end -->

<!-- notes_common_start -->
## 공통 노트
<empty-block/>
<!-- notes_common_end -->

<!-- publish_sentinel: feature_<short_id>_done -->
```

### 포맷 규칙

- `<!-- meta_start -->` / `<!-- meta_end -->` 마커로 감싸 Update/Resume 파서가 인식
- 메타 내부 하위 섹션 순서 고정: 예상 기간 → 타팀 의존성 → 기획 누락 → 타팀 요청 (없어도 헤딩 유지)
- 타팀 의존성: `blocking: true` → 🚫 접두, `false` → ℹ️ 접두
- 빈 리스트는 "(없음)" 출력

포맷 규약 전문은 `references/review-format.md` 의 "메타 섹션 포맷" 신규 섹션에.

### 4-3 → 4-5. 미리보기 확장

미리보기 요약에 메타 완성도 포함:
```
- 알림 설정 화면: 메타 ✓, iOS 노트 ✓, Android 노트 ✗, 공통 노트 ✗
```

메타 섹션 전체가 빈 값(기간 ""+리스트 모두 빈)이면 `메타 ✗` 로 표시.

### 4-6. --fast 모드

- 메타 섹션은 Claude 가 생성한 값 그대로 유지 (편집 프롬프트 스킵)
- 개발자 노트(iOS/Android/공통) 도 빈 상태로 Phase 5 진입 (기존 fast 동작)

## Phase 5 (퍼블리시) 영향

- Toggle 블록에 `meta_start/end` 포함되므로 기존 chunked publish 가 그대로 처리
- 별도 Notion 속성 신규 없음
- 요약 로그에 "X개 피처에 메타 생성됨" 추가 (project-context 미설정 시 "0개")

## Resume 모드 호환

### 초안 헤더

`plugin-state` 헤더 구조 **변경 없음**. 메타는 본문 md 에 포함되므로 Resume 가 자동 보존.

### 단, 신규 필드 누락 시 fallback

v0.3 이전 draft 를 v0.4 로 resume 시 features.json 에 `metadata` 필드가 없을 수 있다. Resume 로직:
```
IF features.json 에 metadata 필드 없음
    각 피처에 빈 metadata 삽입: {estimated_effort: "", external_dependencies: [], planning_gaps: [], cross_team_requests: []}
    경고: "v0.3 초안 — 메타 정보 없이 계속합니다. Phase 3.5 재실행하려면 fresh /spec-from-pdf 필요"
```

`/spec-resume` 는 Phase 3.5 를 **다시 실행하지 않음**. 이미 편집 중인 draft 는 개발자의 결정을 존중.

## Update 모드 (`/spec-update`) 영향

`/spec-update <url>` 로 기존 페이지 수정 시:

1. 페이지 fetch → draft 재구성 시 meta 섹션도 복원
2. `note_extractor.py` 확장: `<!-- meta_start|end -->` 도 feature_id 별로 추출
3. `note_merger.py` 확장: meta 섹션도 병합 (사용자 편집본 > fresh 페이지 > base)
4. `--feature=` 플래그로 특정 Toggle 만 편집할 때도 meta 섹션 접근 가능

Update 모드에서는 Phase 3.5 재실행 **하지 않음**. 기존 메타 보존 + 사용자 편집만.

## 엣지 케이스 요약

| 케이스 | 동작 |
|---|---|
| `project_context_path` 미설정 | Phase 3.5 전체 스킵 + 경고. Phase 4 로 진입, meta 섹션 생성 안 됨 |
| 경로 존재 안 함 | 동일 (스킵 + 경고) |
| 파일 비어있음 | 동일 (스킵 + 경고) |
| 500줄 초과 | 절삭 + 경고, 계속 진행 |
| `codebase_roots` 미설정 | project-context 만으로 메타 생성 (기간 추정 신뢰도 하락 경고) |
| iOS 레포만 설정 | iOS 피처는 코드 힌트 포함, Android 피처는 project-context 만 |
| Claude JSON 파싱 실패 | 해당 피처 빈 메타 + 경고, 나머지 계속 |
| grep timeout 30s | 해당 피처 코드 힌트 없이 메타 생성 |
| excluded 피처 | Phase 3.5 건너뛰기 (기존 excluded 로직) |
| 모든 피처 excluded | Phase 3.5 실행 안 함, Phase 4 도 빈 draft 로 |
| `--fast` | Phase 3.5 요약만 출력 (프롬프트 없이 Enter), Phase 4 도 편집 스킵 |
| 메타 전부 빈 값 | Phase 4 미리보기에 "메타 ✗" 경고만, 차단 아님 |
| Resume (v0.3 draft) | features.json 에 빈 메타 fallback, Phase 3.5 재실행 안 함 |
| Update 모드 | 기존 meta 보존, Phase 3.5 재실행 안 함, 사용자 편집만 |

## 영향 파일

| 경로 | 유형 | 내용 |
|---|---|---|
| `skills/pdf-spec-organizer/SKILL.md` | 수정 | Phase 3.5 섹션 신규. Phase 4 초안 포맷 확장. Phase 5/Resume/Update 에 meta 처리 추가 |
| `skills/pdf-spec-organizer/scripts/enrich_features.py` | 신규 | project-context 로드, 코드베이스 grep, Claude 프롬프트 orchestration, JSON 파싱/fallback |
| `skills/pdf-spec-organizer/scripts/note_extractor.py` | 수정 | `<!-- meta_start|end -->` 블록도 feature_id 별로 추출 |
| `skills/pdf-spec-organizer/scripts/note_merger.py` | 수정 | meta 섹션도 병합 (사용자 > fresh > base 우선순위) |
| `skills/pdf-spec-organizer/references/review-format.md` | 수정 | "메타 섹션 포맷" 섹션 신규 |
| `skills/pdf-spec-organizer/references/project-context-template.md` | 신규 | `project-context.md` 템플릿 + 작성 가이드 |
| `skills/pdf-spec-organizer/scripts/tests/test_enrich_features.py` | 신규 | pytest: LLM mock, JSON 파싱 fallback, project-context 절삭, grep wrapper |
| `skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py` | 수정 | meta 섹션 추출 테스트 추가 |
| `skills/pdf-spec-organizer/scripts/tests/test_note_merger.py` | 수정 | meta 섹션 병합 테스트 추가 |
| `yeoboya-workflow.config.json.example` | 수정 | `project_context_path`, `codebase_roots` 예시 |
| `CHANGELOG.md` | 수정 | `[0.4.0] - 2026-04-21` Added/Changed/Compatibility |
| `README.md` | 수정 | "프로젝트 컨텍스트 셋업" 섹션, `codebase_roots` 가이드 |

Notion DB 스키마 변경 **없음**.

## 검증 기준

### 수동 테스트 시나리오

1. **풀 셋업:** project-context.md + codebase_roots 모두 설정 → Phase 3.5 가 메타 생성 → Phase 4 초안 Toggle 에 메타 섹션 포함 → Phase 5 Notion 페이지에 메타 블록 존재
2. **context 만:** codebase_roots 없음 → 메타 생성되지만 "기간 추정 신뢰도 하락" 경고 → Phase 4 에 섹션 존재
3. **context 없음:** Phase 3.5 전체 스킵 + 경고 → Phase 4 meta 섹션 등장 안 함 (기존 v0.3 동작과 동일)
4. **Phase 4 편집:** 에디터에서 meta 섹션 수정 → 저장 → Phase 5 에서 편집본이 Notion 에 반영
5. **JSON 파싱 실패 시뮬레이션:** Claude 응답을 의도적으로 깨트림 → 빈 메타 fallback + 경고 → Phase 4 진행 가능
6. **excluded 피처:** 웹 필터로 제외된 피처는 메타 생성 안 됨
7. **Resume:** Phase 4 중단 → `/spec-resume --resume-latest` → 메타 섹션 유지
8. **v0.3 draft resume:** 구 draft 를 resume → 빈 메타 fallback + 경고
9. **Update:** `/spec-update <url>` → meta 섹션 그대로 복원 → 사용자 편집 → Notion 반영
10. **`--fast`:** 프롬프트 스킵, 메타 Claude 제안값 그대로 퍼블리시
11. **project-context.md 큼 (1000+ lines):** 절삭 경고 후 계속 진행
12. **큰 PDF (10 피처):** 메타 생성 시간/토큰 사용량 측정 (오픈 이슈 튜닝용)

### 자동 테스트 (pytest)

- `enrich_features.py`:
  - project-context 로드 (경로 정규화, 500줄 절삭)
  - 코드베이스 grep 커맨드 조립 (플랫폼별)
  - Claude 호출 mock → JSON 파싱 성공/실패
  - 빈 메타 fallback 동작
- `note_extractor.py` / `note_merger.py`: meta 섹션 추출/병합
- 기존 18 pytest 회귀 없음

## 오픈 이슈

- **메타 정확도 측정:** v0.4 측정 안 함. 실사용 데이터로 v0.5 튜닝
- **project-context.md 구조화 필요성:** 현재 자유 마크다운. 필드별 YAML frontmatter 또는 정해진 섹션 강제 필요성은 실사용 후 판단
- **기간 추정 calibration:** project-context 의 "Past Effort References" 를 Claude 가 얼마나 잘 활용하는지 튜닝 포인트. v0.5 에서 사후 실측 (실제 걸린 시간 vs 추정) 트래킹 검토
- **팀명 표준화:** external_dependencies / cross_team_requests 의 `team` 필드가 자유 문자열 → 같은 팀이 "백엔드" vs "Backend" 로 다르게 표기될 수 있음. project-context 의 "External Teams" 목록과 매칭 강제 여부 검토
- **Phase 3 누락 체크 vs planning_gaps:** 별도 섹션 유지. 실사용 피드백에 따라 통합/분리 재결정
- **메타 이력 보존:** 과거 실행 메타와 diff 비교 필요성 (v0.5+)
- **Notion 속성으로 전환:** blocking 의존성 등을 Notion 필터 가능 속성으로 노출하면 대시보드 유용 (v0.5+)
- **토큰 비용:** 피처 N 개마다 project-context 전체 + 코드 힌트 → Claude 호출. 피처 10개 이상 PDF 에서 비용 증가. project-context 를 한 번만 로드하고 N개 피처를 배치 처리하는 방식 검토 (v0.5+)
- **Template 제공:** `references/project-context-template.md` 외에 `/spec-init-context` 같은 helper command 로 초기 생성 지원 (v0.5+)
