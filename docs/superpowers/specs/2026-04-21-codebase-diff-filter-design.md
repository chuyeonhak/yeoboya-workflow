# Codebase Diff Filter 설계

- 작성일: 2026-04-21
- 대상: `pdf-spec-organizer` v0.3.x → v0.4.0
- 상태: Draft (사용자 검토 대기)

## 배경

iOS/Android 개발자가 기획 PDF 를 `/spec-from-pdf` 로 처리할 때, **기획서의 피처 중 일부는 이미 코드베이스에 구현돼 있다**. 동일 피처를 Notion 에 재등록하면 개발 범위가 흐려지고, "이번 PDF 에서 진짜 개발해야 할 것" 을 구분하기 어렵다.

Phase 2 구조화 직후 코드베이스를 훑어 **이미 완전 구현된 피처를 개발자가 번호로 제외** 할 수 있게 한다. Claude 는 grep 기반 힌트만 제공하고, 제외 여부는 개발자가 결정한다.

최종적으로 이 플러그인의 Notion 산출물은 `superpowers:writing-plans` → `superpowers:executing-plans` 로 넘어가 "남은 개발 범위" 에 대한 실제 구현 플랜이 된다.

## 목표

- Phase 2-6 (웹 필터) **이후** 에 "구현 필터" 단계(Phase 2-7) 추가
- `--diff-with-code` 플래그가 있을 때만 실행 (opt-in)
- 각 피처의 `platform` 에 해당하는 `codebase_roots` 를 grep 으로 훑고, Claude 가 "구현됨 가능성" 이분법 힌트 제시
- 지정된 피처는 이후 Phase 3/4/5 에서 완전 스킵 (웹 필터 `excluded` 와 동일 매커니즘)
- Notion 에 제외된 피처는 존재 자체가 안 남음

## 비목표 (의도적 단순화)

- `partial` / 부분 구현 지원 **안 함** — v0.5 로 분리. LLM 오판이 Notion 본문에 박히는 리스크 회피
- Notion 에 `구현 상태` 속성 저장 **안 함** — 제외된 피처는 완전히 드롭
- `code_evidence` / 증거 리스트 본문 기록 **안 함** — 터미널 힌트에만 출력
- Agent 기반 심층 탐색 **안 함** — grep + Claude 판정 한 번으로 고정
- 자동 제외 **안 함** — Claude 는 힌트만, 사용자가 번호로 결정
- 다른 플랫폼 레포 조회 **안 함** — 각 피처는 `platform` 에 선언된 레포만 매칭
- 코드베이스 커밋 스냅샷 저장 **안 함** — 실행 시점의 working tree 로 판정. Resume 시 재판정 없음 (이미 결정된 `excluded` 만 유지)

> 사용자 명시적 요구: "재작성 = 개발할 것만 남긴다". 자동화는 의도적으로 배제.

## 데이터 모델

`features.json` 의 각 피처에 플래그 1개 추가:

```json
{
  "feature_id": "uuid-...",
  "name": "알림 설정",
  "platform": ["iOS", "Android"],
  "excluded": false,
  "excluded_reason": null
}
```

- `excluded_reason`: `null` | `"web"` | `"already_implemented"`
- `excluded: true` + `excluded_reason: "already_implemented"` → 코드베이스 비교로 제외된 피처
- 기본값 `excluded: false`, `excluded_reason: null`
- 한 피처는 한 가지 이유로만 제외됨 (웹이면서 이미 구현됨은 불가능 — Phase 2-6 에서 웹으로 제외된 피처는 Phase 2-7 에서 스킵)

### 웹 필터와의 관계

- 데이터 구조 공유: `excluded` 플래그는 양쪽이 함께 쓰고, `excluded_reason` 으로만 원인 구분
- Phase 3/4/5 의 기존 "excluded 스킵" 로직은 **변경 없이** 그대로 동작
- `excluded_reason` 은 UI 표시/감사용. 기능 분기에는 영향 없음

## Config 확장

`yeoboya-workflow.config.json` 에 선택 필드 추가:

```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "...",
    "notion_data_source_id": "...",
    "parent_page_id": "...",
    "codebase_roots": {
      "ios": "/Users/...../ios-repo",
      "android": "/Users/.../android-repo"
    }
  }
}
```

- `codebase_roots` 전체가 없거나 비어있으면 → Phase 2-7 스킵 (경고만)
- 한쪽 플랫폼만 선언 (예: ios 만) → 해당 플랫폼 피처만 판정, 반대쪽 피처는 "판정 스킵"
- 공통 피처(`platform: ["iOS", "Android"]`): 양쪽 경로 모두 선언돼야 힌트 제공. 한쪽만 있으면 "판정 스킵"
- 상대 경로도 허용 (레포 루트 기준). Python 에서 `os.path.expanduser` + `os.path.realpath` 정규화

### 왜 config 인가

아키텍처 리뷰 권고:
- `$PWD` 자동 감지는 모노레포/멀티 플랫폼 환경에서 `*.xcodeproj` 와 `build.gradle` 이 동시 탐지 → 모호
- 기존 `notion_database_id` 와 동일한 "팀 공유 설정 파일" 패턴을 유지해 일관성
- 팀원마다 레포 위치가 다르면 `codebase_roots` 를 상대경로로 커밋 (또는 개인별 override 는 v0.5 에서 검토)

## Phase 2-7 플로우

Phase 2 최종 배치:
```
2-1. 피처 추출
2-2. 피처 목록 리뷰 (y/s/m/r/t/e/c)
2-3. 사용자 입력 처리 루프
2-4. 취소 정리
2-5. feature_id 확정
2-6. 웹 전용 피처 제외 (v0.3.0)
2-7. 구현 필터 (v0.4.0, --diff-with-code 플래그 필요)
```

### 2-7-a. 선행 조건 확인

- `--diff-with-code` 플래그가 없으면 → Phase 2-7 전체 스킵, 곧장 Phase 3 으로
- 플래그 있지만 `codebase_roots` 없음 → 경고 후 스킵:
  ```
  ⚠️  --diff-with-code 요청됐지만 codebase_roots 가 설정되지 않았습니다.
    yeoboya-workflow.config.json 에 codebase_roots.ios / codebase_roots.android 를 추가하세요.
    이번 실행에선 비교 스킵합니다.
  ```

### 2-7-b. 대상 피처 필터링

Phase 2-6 에서 `excluded == true` 로 표시된 피처는 **스킵**. 나머지 `excluded == false` 피처에 대해서만 비교.

### 2-7-c. 피처별 판정 (`source_of_truth.py`)

각 피처에 대해:

1. `platform` 배열에 선언된 플랫폼 중 `codebase_roots` 에 경로가 있는 것만 대상
2. Claude 가 피처의 `name` + `summary` + `requirements` 에서 영문 키워드 2-3개 추출
   - 예: "알림 설정 화면" + "푸시 권한 요청" → `["Notification", "Settings", "Push", "Permission"]`
3. 각 플랫폼별 grep 실행:
   ```bash
   timeout 30 grep -rn \
     --include="*.swift" --include="*.m" --include="*.h" \
     --exclude-dir=".build" --exclude-dir="Pods" \
     --exclude-dir="DerivedData" --exclude-dir=".git" \
     -e "<keyword1>" -e "<keyword2>" -e "<keyword3>" \
     "<ios_root>" | head -30
   ```
   Android:
   ```bash
   timeout 30 grep -rn \
     --include="*.kt" --include="*.java" --include="*.xml" \
     --exclude-dir="build" --exclude-dir=".gradle" \
     --exclude-dir=".git" --exclude-dir="node_modules" \
     -e "<keyword1>" -e "<keyword2>" -e "<keyword3>" \
     "<android_root>" | head -30
   ```
4. grep 결과(매칭 파일/라인 리스트) + 피처 설명을 Claude 에게 던져 **이분법 판정**:
   - `"implemented_hint"`: true | false
   - `"evidence_summary"`: 1줄 (화면에만 출력, features.json 에 저장 안 함)
5. 결과는 Claude 의 메모리/임시 JSON 에만 유지. `features.json` 에는 저장 안 함 (사용자 선택 시만 `excluded` 설정)

### 2-7-d. 공통 피처 규칙

`platform: ["iOS", "Android"]` 피처는:
- 양쪽 레포 모두 설정 + 양쪽에서 "구현됨 가능성" → 힌트 제공
- 한쪽만 "구현됨" → 힌트 제공하되 표시에 "(한쪽만 구현됨으로 보임)" 안내
- 양쪽 모두 미확인 → 힌트 없음
- 경로 미설정 플랫폼이 하나라도 있으면 → 판정 스킵, "판정 스킵 (경로 미설정)"

자동 제외는 절대 안 함. 개발자가 번호로 결정.

### 2-7-f. 힌트 표현 규칙

UI 에 출력되는 힌트 라벨은 2-7-c/d 의 판정 결과에서 다음 규칙으로 파생:

| 상황 | UI 라벨 |
|---|---|
| 단일 플랫폼 피처 + `implemented_hint: true` | "구현됨 가능성 높음" |
| 공통 피처 + 양쪽 모두 `implemented_hint: true` | "구현됨 가능성 높음" |
| 공통 피처 + 한쪽만 `implemented_hint: true` | "구현됨 가능성 있음 (한쪽만 구현됨으로 보임)" |
| 단일 플랫폼 피처 + `implemented_hint: false` | "구현 미확인" |
| 공통 피처 + 양쪽 모두 `implemented_hint: false` | "구현 미확인" |
| 경로 미설정, grep timeout/error, Claude 판정 실패 | "판정 스킵 (<이유>)" |

"높음" 과 "있음" 은 개발자 주의 수준 차이를 시사. `--fast` 자동 수용은 "높음" 만 대상 (아래 참조).

### 2-7-e. 타임아웃/오류

- grep 이 30초 초과 → 해당 피처 "판정 스킵 (grep timeout)"
- grep 종료코드 ≠ 0/1 (1은 "매치 없음", 정상) → "판정 스킵 (grep error: <code>)"
- 레포 경로 존재하지 않음 → 해당 플랫폼 조용히 스킵 + 최초 1회만 경고
- Claude 판정 실패(출력 포맷 불일치 등) → 해당 피처 "판정 스킵"

Phase 2-7 전체는 **실패 아니라 스킵**. 원본 피처 리스트는 온전히 Phase 3 으로 넘어감.

## Phase 2-7 UI

### 1. 힌트 출력

```
코드베이스 비교 결과 (iOS 레포 기준, 5개 피처 중 4개 조회):

  1. 알림 설정 화면 (iOS)                    → 구현됨 가능성 높음 (NotificationSettingsViewController.swift:42)
  2. 푸시 권한 요청 플로우 (iOS, Android)     → 구현됨 가능성 있음 (PushPermission.swift:18, 한쪽만 구현됨으로 보임)
  3. 빈 상태 UI (공통)                       → 판정 스킵 (공통 피처, Android 경로 미설정)
  4. 로그인 유도 팝업(A/B) (iOS)             → 구현 미확인
  5. 회원가입 플로우 (Android)                → 판정 스킵 (iOS 레포 기준 실행)

※ "구현됨 가능성" 힌트는 grep 기반 추정입니다. 최종 제외 여부는 직접 판단하세요.
```

"힌트 표시" 포맷 규약은 `references/review-format.md` 에 공식화.

### 2. 제외 프롬프트 (웹 필터와 동일 파서)

```
이미 완전 구현된 피처 번호 입력 (Notion 에서 제외됩니다):
  쉼표: 1, 2
  범위: 1-2
  전체 제외: all
  없음: none (또는 Enter)
> _
```

**입력 처리:** 웹 필터(Phase 2-6)와 동일 파서 재활용:
- 쉼표 리스트, 범위, `all`, `none`/Enter 전부 동일 문법
- 범위 밖 숫자 → "N 은 존재하지 않습니다. 1-<max> 사이 숫자 필요" + 재입력
- 형식 오류 → "형식 오류. 쉼표/범위/all/none 중 선택" + 재입력

### 3. `all` 안전장치

`all` 입력 시 이중 확인:
```
모든 피처를 이미 구현됨으로 표시합니다. Phase 3 이후 스킵되며 Notion 에 아무것도 생성되지 않습니다. 확실합니까? (y/N)
```
- `y` 만 진행
- `N` / Enter → 재입력

### 4. `--fast` 모드

`--fast --diff-with-code` 조합일 때:
- 힌트 표시 후 프롬프트 대신 자동 안내:
  ```
  [--fast 모드] 힌트를 그대로 수용합니까?
    "구현됨 가능성 높음" 피처만 자동 제외됩니다.
    "구현됨 가능성 있음 (한쪽만)" / "구현 미확인" / "판정 스킵" 은 유지됩니다.

    자동 제외 대상: 1, 4
    유지: 2, 3, 5

  모두 맞으면 y, 수정하려면 번호 입력:
  >
  ```
- `y` → UI 라벨이 **정확히 "구현됨 가능성 높음"** 인 피처만 `excluded: true`, `excluded_reason: "already_implemented"` 처리
- "한쪽만 구현됨" 공통 피처는 자동 제외 **안 함** — 개발자가 담당 플랫폼을 아직 구현 안 했을 수 있으므로 수동 결정 필수
- 번호 입력 → 수동 모드 (일반 프롬프트로 재진입)

## 다른 Phase 영향

| Phase | 처리 |
|---|---|
| **3 (누락 체크)** | `excluded == false` 피처만 checklist 적용. `excluded_reason` 무관 (기존 로직 그대로) |
| **4 (노트)** | 초안 md 에 `excluded` 피처 등장 안 함. 노트 섹션도 생성 안 됨 |
| **5 (퍼블리시)** | `excluded` 피처는 Notion DB 조회/생성 대상 완전 제외. 요약 로그에 이유별 카운트:<br>`"2개 피처가 웹 전용으로, 3개 피처가 이미 구현된 것으로 제외됨"` |

Phase 3/4/5 의 코드 로직은 **변경 없음**. `excluded_reason` 은 Phase 5 의 사용자 안내 메시지에만 사용.

## Resume 모드 호환

`/spec-resume` 로 중단된 세션 복구 시:

초안 md 의 `<!-- plugin-state -->` 헤더에 기존 `excluded_ids` + 신규 `excluded_reasons` 직렬화:

```
<!-- plugin-state
phase: 4
pdf_hash: abc123
source_file: spec.pdf
created_at: 2026-04-21T12:34:56
publish_state: idle
page_id:
last_block_sentinel_id:
excluded_ids:
  - <uuid-1>
  - <uuid-2>
excluded_reasons:
  <uuid-1>: web
  <uuid-2>: already_implemented
-->
```

- Resume 진입 시 `excluded_ids` + `excluded_reasons` 를 features.json 에 복원
- `excluded_reasons` 키가 없는 구 초안 (v0.3 이하) → 모든 excluded_ids 를 `"web"` 으로 간주 (하위 호환). Phase 5 요약 메시지만 "웹 전용" 으로 표시됨 — 실제 기능 동작은 동일
- Phase 2-7 자체는 Resume 에서 **다시 실행 안 함** (이미 결정된 excluded 상태 유지). 코드베이스가 변경됐다 해도 기존 결정 존중

### 재실행 시나리오

같은 PDF 를 `/spec-from-pdf <same.pdf> --diff-with-code` 로 다시 실행하면:
- 새 /tmp 작업 폴더 생성, 이전 실행 기억 없음
- Phase 2-7 는 처음부터 다시 수행 (이전 exclude 이력 기억 안 함)
- 개발자가 이전과 다르게 판단해도 정상

## 엣지 케이스 요약

| 케이스 | 동작 |
|---|---|
| `--diff-with-code` 없이 실행 | Phase 2-7 전체 스킵 |
| `codebase_roots` 없음 + 플래그 있음 | 경고 + 스킵 |
| `codebase_roots.ios` 만 설정 | Android 피처는 전부 "판정 스킵" |
| 설정된 경로가 존재 안 함 | 최초 1회 경고 + 해당 플랫폼 스킵 |
| 공통 피처 + 양쪽 설정 + 한쪽만 구현 | "한쪽만 구현됨으로 보임" 힌트 (자동 제외 안 함) |
| 공통 피처 + 한쪽 경로만 설정 | "판정 스킵 (경로 미설정)" |
| 모든 피처가 판정 스킵 | 힌트는 전부 스킵 메시지, 프롬프트는 `none` / Enter 로 자연 통과 |
| Phase 2-6 에서 이미 excluded 된 피처 | Phase 2-7 스킵 (이중 판정 안 함) |
| `all` 입력 | 이중 확인 후 진행. 전부 `excluded: true`, `excluded_reason: "already_implemented"` |
| grep timeout | 해당 피처만 "판정 스킵", 나머지 진행 |
| grep 전부 실패 | Phase 2-7 전체 스킵, Phase 3 으로 진행 |
| `--fast --diff-with-code` | 힌트 자동 수용 또는 수동 번호 입력 |
| Phase 2-7 취소 (`c`) | Phase 2-6 결과는 유지, Phase 2-7 결정만 롤백, 2-2 로 돌아감 |
| Phase 3/4 에서 취소 후 resume | `excluded_ids` + `excluded_reasons` 복원, Phase 2-7 재실행 안 함 |

## 영향 파일

| 경로 | 유형 | 내용 |
|---|---|---|
| `skills/pdf-spec-organizer/SKILL.md` | 수정 | Phase 2-7 섹션 추가. Phase 3/4/5 의 excluded 스킵은 기존 로직 그대로 (excluded_reason 만 표시용으로 읽음). Resume 섹션에 excluded_reasons 직렬화/복원 추가 |
| `skills/pdf-spec-organizer/references/source-of-truth.md` | 수정 | v1 비활성 상태 → v2 활성 문서로 갱신. Notion 매칭 경로는 v0.5+ 로 이월 명시 |
| `skills/pdf-spec-organizer/references/review-format.md` | 수정 | Phase 2-7 힌트/프롬프트 포맷 규약 |
| `skills/pdf-spec-organizer/scripts/source_of_truth.py` | 신규 | 키워드 추출 → grep → Claude 판정 orchestration. CLI: `python source_of_truth.py diff --features-file <path> --config <path>` |
| `skills/pdf-spec-organizer/scripts/tests/test_source_of_truth.py` | 신규 | pytest: 키워드 추출 (LLM mock), grep wrapper, 판정 결과 파싱 |
| `yeoboya-workflow.config.json.example` | 수정 | `codebase_roots` 예시 + 주석 |
| `commands/spec-from-pdf.md` | 수정 | `--diff-with-code` 플래그 파싱 + 환경변수 export |
| `CHANGELOG.md` | 수정 | `[0.4.0] - 2026-04-21` Added/Changed/Compatibility |
| `README.md` | 수정 | `--diff-with-code` 사용 예시, `codebase_roots` 셋업 가이드 |
| `evals/trigger-eval.json` | 선택 | 구현 필터 시나리오 query 추가 (v0.5 에서) |

Notion 스키마 변경 **없음** — `excluded` 재활용.

## 검증 기준

### 수동 테스트 시나리오

1. **Baseline (플래그 없음):** 샘플 PDF 를 `--diff-with-code` 없이 실행 → Phase 2-7 스킵 확인, 기존 v0.3 과 동작 동일
2. **Config 미설정:** `--diff-with-code` + `codebase_roots` 없음 → 경고 후 스킵
3. **iOS 만 설정:** `codebase_roots.ios` 만 → iOS 피처만 힌트, Android 피처는 "판정 스킵"
4. **공통 피처, 양쪽 설정:** 양쪽 grep 결과 집계 → "한쪽만" 안내 케이스 확인
5. **정상 제외 플로우:** 힌트 후 `1, 3` 입력 → Phase 5 에서 해당 피처 Notion 미생성
6. **`all` 이중 확인:** all → y → 모든 피처 제외 → 정상 종료
7. **`--fast --diff-with-code`:** 힌트 자동 수용 플로우
8. **Resume:** Phase 4 중단 → `/spec-resume --resume-latest` → `excluded_reasons` 복원, Phase 2-7 재실행 안 함
9. **v0.3 초안 resume:** `excluded_reasons` 없는 초안 → 전부 `"web"` 로 간주, 기능 동작 정상
10. **grep timeout:** 고의로 긴 경로 설정 → "판정 스킵" 개별 처리

### 자동 테스트

- pytest: `source_of_truth.py` 의 키워드 추출 (LLM 호출 mock), grep 커맨드 생성, 결과 파싱, config 로드/기본값
- 기존 18 pytest 회귀 없음

## 오픈 이슈

- **키워드 추출 정확도:** 한국어 피처명 → 영문 키워드 번역 품질이 판정 품질 좌우. v0.4 에서 측정 안 함. 실사용 데이터로 v0.5 튜닝 여부 결정
- **코드베이스 커밋 해시 스냅샷:** 현재 working tree 기준 판정 → 중간에 새 코드 추가돼도 Resume 시 재판정 안 함. v0.5 에서 `git HEAD` 기록 여부 검토
- **Partial 지원 (v0.5+):** "부분 구현" 판정 + 증거를 Notion 페이지 본문에 남기는 기능. false positive 관리 방안 (튜닝/검증/롤백) 필요
- **Notion 기존 페이지 매칭 (v0.5+):** 코드베이스가 아닌 Notion 기존 피처 DB 와의 중복/관련 피처 연결. `관련_피처` Relation 속성 + 유사도 판정
- **`codebase_roots` 개인 override:** 팀원마다 레포 위치가 다를 때 `~/.yeoboya-workflow.config.json` 같은 개인 설정 병합 필요 여부. v0.4 는 단일 config 파일로 시작
- **Agent 기반 심층 탐색:** grep false negative 를 `Explore` subagent 로 보강하는 옵션. 토큰 비용/속도 트레이드오프 확인 후 v0.5+ 결정
