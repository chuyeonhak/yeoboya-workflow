---
name: spec-resume
description: 중단된 /spec-from-pdf 세션을 이어받는다. 퍼블리시 도중 중단된 부분 append (partial_success) 도 재개 가능.
argument-hint: [--resume-latest | <draft-path>]
allowed-tools: Bash Read Write Edit mcp__claude_ai_Notion__*
---

# /spec-resume

중단된 세션을 Phase 진행 상태부터 이어받는다. Phase 5 도중 chunked publish 가 부분 실패한 경우에도 sentinel 기반으로 재개.

## 사용법

```
/spec-resume --resume-latest
/spec-resume /tmp/spec-draft-abc123-1700000000/draft.md
```

## 동작

1. 초안 경로 결정 (최근 실행 or 명시된 경로)
2. 초안의 `<!-- plugin-state -->` 헤더에서 `phase`, `publish_state`, `page_id` 읽기
3. `pdf-spec-organizer` Skill 을 **Resume 모드**로 진입 (해당 지점부터 재실행)

## 인자 처리

```bash
# CLAUDE_PLUGIN_ROOT 가드
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  export CLAUDE_PLUGIN_ROOT
fi

ARG="$1"

if [ -z "$ARG" ]; then
  echo "❌ --resume-latest 또는 초안 경로가 필요합니다." >&2
  exit 2
fi

if [ "$ARG" = "--resume-latest" ]; then
  LATEST=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/common/scripts/draft_registry.py" list-latest --count 10 \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
# prefer partial_success / failed / running
priority = {'partial_success': 0, 'failed': 1, 'running': 2}
candidates = [e for e in data['entries'] if e.get('status') in priority]
if not candidates:
    sys.exit(1)
candidates.sort(key=lambda e: (priority.get(e['status'], 99), -e['created_at']))
print(candidates[0]['draft_path'])
")
  if [ -z "$LATEST" ]; then
    echo "❌ 이어받을 초안이 없습니다." >&2
    exit 1
  fi
  DRAFT_PATH="$LATEST"
else
  DRAFT_PATH=$(python3 -c "import sys, os; print(os.path.realpath(os.path.expanduser(sys.argv[1])))" "$ARG")
fi

if [ ! -f "$DRAFT_PATH" ]; then
  echo "❌ 초안 파일이 없습니다: $DRAFT_PATH" >&2
  exit 1
fi

export DRAFT_PATH
export MODE="resume"
```

Skill 은 `MODE=resume` 를 인식해 Resume 모드 로직 실행. 초안의 `plugin-state` 헤더에서 `phase` + `publish_state` 를 읽어 이어받기.
