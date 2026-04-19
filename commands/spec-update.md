---
name: spec-update
description: 기존 Notion 피처 페이지의 개발자 노트/누락 체크만 갱신한다. 새 PDF 파싱 없이 노트 수정 전용.
argument-hint: <notion-page-url>
allowed-tools: Bash Read Write Edit mcp__claude_ai_Notion__*
---

# /spec-update

기존 Notion 페이지의 노트 섹션을 수정한다. 새 PDF 를 돌리지 않고 내 플랫폼의 노트만 append/교체.

## 사용법

```
/spec-update https://www.notion.so/.../알림-설정-화면-abc123
```

## 동작

1. Notion URL 에서 page ID 추출
2. `pdf-spec-organizer` Skill 을 **Update 모드**로 실행
3. Phase 4 (노트 작성) + Phase 5 (병합 퍼블리시) 만 수행

## 인자 처리

```bash
URL="$1"

if [ -z "$URL" ]; then
  echo "❌ Notion 페이지 URL 이 필요합니다." >&2
  exit 2
fi

# page ID 추출: URL 끝의 32자 hex (하이픈 있을 수 있음)
PAGE_ID=$(echo "$URL" | grep -oE "[0-9a-f]{32}" | tail -1)

if [ -z "$PAGE_ID" ]; then
  # 하이픈 포함 UUID 형식 시도
  PAGE_ID=$(echo "$URL" | grep -oE "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" | tail -1)
fi

if [ -z "$PAGE_ID" ]; then
  echo "❌ URL 에서 페이지 ID 를 추출할 수 없습니다: $URL" >&2
  exit 1
fi

export NOTION_PAGE_ID="$PAGE_ID"
export MODE="update"
```

이후 Skill 을 진입점으로 호출. Skill 은 `MODE=update` 를 인식해 Update 모드 로직 실행.
