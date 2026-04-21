# Web Feature Filter 설계

- 작성일: 2026-04-21
- 대상: `pdf-spec-organizer` v0.2.x → v0.3.0
- 상태: Draft (사용자 검토 대기)

## 배경

iOS/Android 개발자가 기획 PDF 를 `/spec-from-pdf` 로 처리할 때, 기획서에는 **웹 기능과 네이티브 기능이 혼재**한다. 네이티브 개발팀은 웹 기능을 구현하지 않으므로 이를 Notion 에 정리하는 것은 노이즈. 사용자가 Phase 2 에서 **웹 전용 피처를 지정해 제외** 할 수 있게 한다.

## 목표

- Phase 2 구조화 끝에 "웹 전용 피처 번호 입력" 단계 추가
- 지정된 피처는 이후 Phase 3/4/5 에서 완전 스킵
- Notion 에 해당 피처는 존재 자체가 안 남음

## 비목표 (의도적 단순화)

- 웹/네이티브 **자동 분류 안 함** (Claude 는 힌트만 제공, 결정은 사용자)
- Notion 에 category 속성 저장 **안 함** (제외된 피처는 완전히 드롭)
- confidence score / evidence 저장 **안 함**
- 기존 실행의 제외 이력 기억 **안 함** (각 실행 독립)

> 사용자 명시적 요구: "그냥 개발자에게 물어봐서 체크하게만 해라". 복잡한 자동화는 의도적으로 배제.

## 데이터 모델

`features.json` 의 각 피처에 플래그 1개 추가:

```json
{
  "feature_id": "uuid-...",
  "name": "알림 설정",
  "platform": ["iOS", "Android"],
  "excluded": false,
  ...
}
```

- `excluded: true` 인 피처는 이후 Phase 에서 스킵
- 기본값 `false`
- `feature_id` 기반 플래그 → Phase 2 내 split/merge/rename 후에도 유지
- **Soft flag** (파일에서 drop 하지 않음) — 디버깅/되돌리기 용이

## Phase 2 UI

### 1. 구조화 결과 표시 (Claude 힌트 포함)

```
피처 5개 추출됨:
  1. 알림 설정 화면 (iOS, Android)
  2. 랭킹 리더보드 웹뷰 (공통)              💡 Claude: "웹 같음"
  3. 프로필 편집 (iOS, Android, 공통)       💡 Claude: "혼합 — s 3 으로 분리 권장"
  4. 로그인 플로우 (iOS, Android)
  5. PC 관리자 대시보드 (공통)              💡 Claude: "웹 같음 (PC)"

범례: iOS/Android 공통 = iOS+Android 둘 다 (웹 포함 아님)

이대로 진행할까요?
  y) 진행
  s N) 피처 N번 쪼개기
  m N,M) 피처 N,M 합치기
  r N) 피처 N번 리네이밍
  t N) 피처 N번 플랫폼 변경
  e) 에디터에서 수정
  c) 취소
>
```

**힌트 규칙:**
- Claude 가 각 피처의 `name` + `summary` + `requirements` 를 보고 "웹 같음", "혼합", "PC", "불명" 같은 짧은 힌트 첨언
- 부정 패턴 (`웹뷰`, `웹소켓`, `웹훅`, `웹 표준` 등) 이 네이티브 문맥에서 등장해도 웹으로 속단하지 않음
- 힌트는 **정보 제공용**. 사용자 pre-check 없음

### 2. 웹 제외 프롬프트 (기존 y 승인 직후 추가 단계)

사용자가 `y` 로 구조화 승인 후 아래 프롬프트:

```
웹 전용 피처 번호 입력 (네이티브 개발팀 작업 대상 아님):
  쉼표: 2, 5
  범위: 2-5
  전체 제외: all
  없음: none (또는 Enter)
> _
```

**입력 처리:**
- 쉼표 리스트 (`2, 5`, `2,5`) — 공백 허용
- 범위 (`2-5`) — 포함 양끝, inclusive
- `all` — 모든 피처를 excluded 로 (아래 안전장치 참조)
- `none` / Enter — 아무것도 제외 안 함

**유효성 검사:**
- 범위 밖 숫자 (예: 피처 5개인데 `7`) → "7 은 존재하지 않습니다. 1-5 사이 숫자 필요" + 재입력
- 비숫자/형식 오류 → "형식 오류. 쉼표/범위/all/none 중 선택" + 재입력

**안전장치:**
- `all` 입력 시: "모든 피처 제외합니다. Phase 3 이후 스킵되며 Notion 에 아무것도 생성되지 않습니다. 확실합니까? (y/N)" 이중 확인
- `y` 만 진행, `N` 또는 Enter → 재입력

### 3. 혼합 피처 안내

프롬프트 하단에 안내 한 줄:

```
※ 일부만 웹인 피처는 먼저 `s N` 으로 분리한 뒤 이 단계에서 제외하세요.
```

사용자가 원하면 `c` 로 취소 → Phase 2 구조화로 돌아가 split 후 재진입.

## 다른 Phase 영향

| Phase | 처리 |
|---|---|
| **3 (누락 체크)** | `excluded == false` 피처만 checklist 적용 |
| **4 (노트)** | 초안 md 에 `excluded` 피처 자체 등장 안 함. 노트 섹션도 생성 안 됨 |
| **5 (퍼블리시)** | `excluded` 피처는 Notion DB 조회/생성 대상에서 완전 제외 |

## Resume 모드 호환

`/spec-resume` 로 중단된 세션 복구 시:
- 초안 md 의 `<!-- plugin-state -->` 헤더에 `excluded_ids: [<uuid>, ...]` 직렬화
- Resume 진입 시 해당 ID 를 features.json 에 플래그 복원
- 이후 동작 기존과 동일

## 엣지 케이스 요약

| 케이스 | 동작 |
|---|---|
| Enter 만 입력 | `excluded` 없음, 모든 피처 포함 |
| 잘못된 번호 (예: `99`) | 오류 + 재입력 |
| `all` 입력 | 이중 확인 후 진행 |
| Phase 2 split 후 다시 제외 지정 | feature_id 기반이라 유지됨 |
| 혼합 피처 (일부만 웹) | 안내만. `s N` 분리 권장 |
| 재실행 (같은 PDF) | 이전 excluded 기억 안 함, 매번 새로 판단 |
| 전체 피처가 웹 (필터 후 0개) | "퍼블리시할 피처 없음. 종료" 메시지 후 정상 종료 (실패 아님) |
| Phase 2 취소 (`c`) | `excluded` 플래그 리셋, features.json 정리 |

## 영향 파일

| 경로 | 유형 | 내용 |
|---|---|---|
| `skills/pdf-spec-organizer/SKILL.md` | 수정 | Phase 2 에 웹 제외 단계 추가 (2-6), Phase 3/4/5 에 excluded 스킵 로직 반영, Resume 모드에 excluded_ids 직렬화 추가 |
| `skills/pdf-spec-organizer/references/review-format.md` | 수정 | 새 프롬프트 포맷 + 힌트 표기 규약 |
| `CHANGELOG.md` | 수정 | `[Unreleased]` 또는 `[0.3.0]` 엔트리 |
| `evals/trigger-eval.json` | 선택 | 필터 시나리오 query 추가 (v2에서) |

Python 스크립트는 **변경 없음** — SKILL.md 의 LLM 지시만으로 구현 가능.

## 검증 기준

- 수동 테스트 시나리오:
  - (a) 샘플 PDF 로 실행 → Claude 힌트 표시 확인
  - (b) 웹 피처 번호 입력 → Phase 5 에서 해당 피처 Notion 미생성 확인
  - (c) `all` 입력 → 이중 확인 + 정상 종료
  - (d) Enter → 모든 피처 포함 진행
  - (e) `/spec-resume` 로 재개 시 excluded 유지 확인
- 기존 18 pytest 회귀 없음 (Python 변경 없음)

## 오픈 이슈

- Claude 힌트 정확도: v1 에서는 측정 안 함. 실사용 데이터로 v2 에서 튜닝 여부 결정
- 혼합 피처 분리 UX: `s N` 사용 안내가 충분한지, 전용 `split-web N` 같은 명령이 필요한지 실사용 후 판단
- 대형 PDF (20+ 피처) 에서 번호 입력 피로: v1 에선 range/all 로 완화. 정말 불편하면 v2 에서 체크박스 TUI 고려
