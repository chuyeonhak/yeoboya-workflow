# 터미널 / 미리보기 포맷 규약

Phase 4 의 미리보기 md 파일과 터미널 출력은 일관된 포맷을 따른다. v2 부터는 **PDF 1개 = 초안 1개 = Notion 페이지 1개** 구조이며, 피처는 Toggle 블록으로 배치된다.

## `/tmp/spec-draft-<hash>-<ts>/draft.md` 초안 파일 구조

```markdown
<!-- plugin-state
phase: 4
pdf_hash: <short-hash>
source_file: <filename>
created_at: <iso8601>
publish_state: idle
page_id:
last_block_sentinel_id:
-->

# <PDF 제목>

## 개요
<Claude 가 생성한 PDF 전체 요약 — 1~2문단>

## 피처별 상세

### 1. <피처명> {toggle="true"}
	<!-- feature_id: <uuid> -->
	<callout color="yellow_bg">🟡 Draft</callout>

	**플랫폼:** 공통 / iOS / Android

	**개요:** ...

	**화면:**
	![원본: <local-path>](https://placehold.co/...)

	**요구사항:**
	- 요구사항 1
	- 요구사항 2

	**누락 체크:**
	- [ ] 에러 케이스 — 명시 없음
	- [x] 빈 상태 — 명시됨

	<!-- meta_start -->
	#### 📊 개발 계획 메타

	**예상 기간:** iOS 2-3일, Android 2-3일

	**타팀 의존성:**
	- 🚫 [백엔드] 알림 설정 저장 API — blocking
	  - POST /users/me/notification-settings

	**기획 누락 포인트:**
	- API 실패 시 UI 처리 정의 없음
	- 이전 설정값 출처 명시 없음

	**타팀 요청 사항:**
	- [디자인] 토글 off 상태 스타일 확정 (개발 착수 전)

	> ℹ️ Claude 가 project-context 기반으로 제안한 값입니다. Phase 4 에서 검토/수정하세요.
	<!-- meta_end -->

	<!-- notes_ios_start -->
	### iOS
	<empty-block/>
	<!-- notes_ios_end -->

	<!-- notes_android_start -->
	### Android
	<empty-block/>
	<!-- notes_android_end -->

	<!-- notes_common_start -->
	### 공통 질문
	<empty-block/>
	<!-- notes_common_end -->

	<!-- publish_sentinel: feature_<short-id>_done -->

### 2. <피처명 2> {toggle="true"}
	<!-- feature_id: <uuid> -->
	...

## 메타
- 원본 PDF: <filename>
- PDF 해시: <short-hash>
- 생성자: <user>
- 생성일: <iso8601>
```

### 왜 마커가 많은가?

- `<!-- feature_id: ... -->` — Toggle rename/reorder 후에도 노트 보존 병합이 가능한 안정적 식별자.
- `<!-- notes_*_start|end -->` — `/spec-update` 시 해당 섹션만 정확히 교체/추출.
- `<!-- meta_start|end -->` — Phase 3.5 가 생성한 "📊 개발 계획 메타" 섹션 경계. note_extractor/merger 가 노트 섹션과 동일하게 보존한다.
- `<!-- publish_sentinel: ... -->` — Phase 5 chunked publish 재개용 커서.
- `<!-- plugin-state ... -->` — `/spec-resume` phase 판정용. Notion 퍼블리시 시에는 필터링 후 제거.

## Phase 5 에서 추가되는 sentinel

Chunked publish 가 진행됨에 따라 페이지 하단에 `<!-- publish_sentinel: chunk_N_done -->` 블록이 append 된다. 마지막 chunk 뒤에는 `<!-- publish_sentinel: complete -->` 가 들어간다.

## 터미널 출력 규약

각 Phase 시작/종료를 간결히 표시:

```
[Phase 1/5] PDF 파싱 중...
[Phase 1/5] 완료 (12 페이지, 12 이미지 추출)

[Phase 2/5] 구조화 중...
[Phase 2/5] 완료

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

Phase 5 진행 중에는 chunk 별 진행도 표시:

```
[Phase 5/5] 퍼블리시 중...
  ✓ shell 페이지 생성 (page_id: 34820097...)
  ✓ chunk 0/3 append 완료 (42 blocks)
  ✓ chunk 1/3 append 완료 (38 blocks)
  ✓ chunk 2/3 append 완료 (29 blocks)
  ✓ complete sentinel 기록
```

## Phase 별 프롬프트

Phase 2 완료 후: 위 메뉴

### 웹 전용 피처 제외 프롬프트 (Phase 2-6)

구조화 승인(`y`) 직후 아래 프롬프트 표시:

```
웹 전용 피처 번호 입력 (네이티브 개발팀 작업 대상 아님):
  쉼표: 2, 5
  범위: 2-5
  전체 제외: all
  없음: none (또는 Enter)

※ 일부만 웹인 피처는 먼저 `s N` 으로 분리한 뒤 이 단계에서 제외하세요.
> _
```

입력 처리:
- 쉼표 리스트 (`2, 5` 또는 `2,5`): 공백 허용
- 범위 (`2-5`): 포함 양끝 (inclusive)
- `all`: "모든 피처 제외합니다. Phase 3 이후 스킵되며 Notion 에 아무것도 생성되지 않습니다. 확실합니까? (y/N)" 이중 확인
- `none` 또는 Enter: 아무것도 제외 안 함

유효성 오류:
- 범위 밖 숫자 → "N 은 존재하지 않습니다. 1-<max> 사이 숫자 필요" + 재입력
- 형식 오류 → "형식 오류. 쉼표/범위/all/none 중 선택" + 재입력

결과: `features.json` 의 해당 피처에 `excluded: true` 플래그 설정.

Phase 3 완료 후:

### 피처 메타 정보 생성 요약 (Phase 3.5)

`project_context_path` 설정이 있을 때 Phase 3 직후 아래 요약이 출력된다:

```
피처 메타 정보 생성 완료 (excluded 제외 <N>개 피처):

  1. <피처명>
     예상 기간: iOS 2-3일, Android 2-3일
     타팀 의존: 백엔드 — 알림 설정 저장 API (blocking)
     기획 누락: API 실패 UI, 이전 설정값 출처
     타팀 요청: 디자인 — 토글 off 상태 (개발 착수 전)

  2. ...

검토/수정은 Phase 4 (개발자 노트) 에서 진행됩니다.
계속하려면 Enter.
```

표시 규칙:
- "(없음)" 으로 표시되는 필드: 해당 피처에서 비어있는 항목
- `codebase_roots` 미설정: 시작 시 한 번만 "기간 추정 신뢰도 하락" 경고 출력
- `project_context_path` 미설정: Phase 3.5 전체 스킵 + "설정 가이드는 README" 경고
- `--fast`: 요약만 출력, Enter 없이 Phase 4 로 진입

#### 메타 섹션 포맷 (초안 md)

각 피처 Toggle 내 `<!-- meta_start -->` ~ `<!-- meta_end -->` 사이. 하위 섹션 순서 고정:
1. `#### 📊 개발 계획 메타` 헤딩
2. `**예상 기간:**` — 자유 문자열. 빈 값이면 "(미정)"
3. `**타팀 의존성:**` — 리스트. blocking → `🚫`, non-blocking → `ℹ️`. 빈 리스트 → "(없음)"
4. `**기획 누락 포인트:**` — 불릿 리스트. 빈 리스트 → "(없음)"
5. `**타팀 요청 사항:**` — 리스트 `[팀] 아이템 (by)`. 빈 리스트 → "(없음)"
6. 마지막에 `> ℹ️ Claude 가 project-context 기반으로 제안한 값입니다. Phase 4 에서 검토/수정하세요.`
