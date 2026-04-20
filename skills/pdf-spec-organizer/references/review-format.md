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

피처 7개 추출됨:
  1. 앱 시작 플로우 개방 (공통)
  2. 메인화면 비로그인 UI 제어 (공통)
  ...

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
