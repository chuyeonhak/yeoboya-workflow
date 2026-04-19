---
name: spec-from-pdf
description: PDF 스펙(PRD+디자인+플로우)을 파싱해 Notion 피처 DB 페이지로 정리한다. 명세 누락 체크 + 플랫폼별 개발자 노트 공유.
argument-hint: <pdf-path> [--fast]
allowed-tools: Bash Read Write Edit Grep Glob mcp__claude_ai_Notion__*
---

# /spec-from-pdf

PDF 스펙을 Notion 피처 DB 페이지로 정리한다.

## 사용법

```
/spec-from-pdf ~/Downloads/feature-spec.pdf
/spec-from-pdf ~/Downloads/feature-spec.pdf --fast
```

## 동작

1. 인자를 절대 경로로 정규화
2. `pdf-spec-organizer` Skill 을 실행 (5 Phase 워크플로우)
3. 성공 시 생성된 Notion 페이지 URL 출력

## 인자 처리

아래 지시대로 인자를 검증하고 Skill 을 호출한다:

```bash
RAW_ARG="$1"
FAST_FLAG=""

# --fast 플래그 파싱
for a in "$@"; do
  if [ "$a" = "--fast" ]; then FAST_FLAG="--fast"; fi
done

# 경로 정규화
if [ -z "$RAW_ARG" ] || [ "$RAW_ARG" = "--fast" ]; then
  echo "❌ PDF 경로가 필요합니다. 사용법: /spec-from-pdf <pdf-path> [--fast]" >&2
  exit 2
fi

PDF_PATH=$(python3 -c "import sys, os; print(os.path.realpath(os.path.expanduser(sys.argv[1])))" "$RAW_ARG")

if [ ! -f "$PDF_PATH" ]; then
  echo "❌ 파일을 찾을 수 없습니다: $PDF_PATH" >&2
  exit 1
fi

if [ "${PDF_PATH##*.}" != "pdf" ] && [ "${PDF_PATH##*.}" != "PDF" ]; then
  echo "⚠️  .pdf 확장자가 아닙니다: $PDF_PATH. 계속 시도합니다."
fi

export PDF_PATH FAST_FLAG
```

이후 `pdf-spec-organizer` Skill 을 진입점으로 실행한다. Skill 은 위 환경변수를 읽어 워크플로우를 시작한다.

자세한 워크플로우는 `skills/pdf-spec-organizer/SKILL.md` 참조.
