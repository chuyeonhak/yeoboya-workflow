---
name: spec-update
description: 기존 Notion 피처 페이지의 iOS/Android/공통 노트를 갱신한다. 전체 페이지 또는 특정 피처 Toggle 단위 편집 가능.
argument-hint: <notion-page-url> [--feature="<name>"]
allowed-tools: Bash Read Write Edit mcp__claude_ai_Notion__*
---

# /spec-update

기존 Notion PDF 페이지의 노트 섹션을 수정한다. 새 PDF 를 돌리지 않고 노트만 append/교체한다. 피처 이름을 지정하면 해당 Toggle 만, 미지정 시 전체 페이지 편집.

## 사용법

```
/spec-update https://www.notion.so/.../<page>                                   # 전체
/spec-update https://www.notion.so/.../<page> --feature="로그인 유도 팝업(A/B)"   # 해당 피처만
```

## 동작

1. Notion URL 에서 page ID 추출
2. `--feature=` 플래그 파싱 (공백/괄호/슬래시 포함 가능)
3. `pdf-spec-organizer` Skill 을 **Update 모드**로 실행

## 인자 처리

```bash
# CLAUDE_PLUGIN_ROOT 가드 (미설정 시 커맨드 파일 상대경로로 폴백)
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  export CLAUDE_PLUGIN_ROOT
fi

URL=""
FEATURE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --feature=*) FEATURE="${1#--feature=}"; shift;;
    --feature) FEATURE="$2"; shift 2;;
    *)
      if [ -z "$URL" ]; then URL="$1"; shift
      else echo "❌ 알 수 없는 인자: $1" >&2; exit 2
      fi
      ;;
  esac
done

if [ -z "$URL" ]; then
  echo "❌ Notion 페이지 URL 이 필요합니다." >&2
  exit 2
fi

# page ID 추출: URL 끝의 32자 hex 또는 UUID 형식
PAGE_ID=$(echo "$URL" | grep -oE "[0-9a-f]{32}" | tail -1)
if [ -z "$PAGE_ID" ]; then
  PAGE_ID=$(echo "$URL" | grep -oE "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" | tail -1)
fi

if [ -z "$PAGE_ID" ]; then
  echo "❌ URL 에서 페이지 ID 를 추출할 수 없습니다: $URL" >&2
  exit 1
fi

export NOTION_PAGE_ID="$PAGE_ID"
export NOTION_PAGE_URL="$URL"
export FEATURE_NAME="$FEATURE"
export MODE="update"
```

이후 Skill 을 진입점으로 호출. Skill 은 `MODE=update` + (`FEATURE_NAME` 유무) 로 전체/부분 모드를 판별.
