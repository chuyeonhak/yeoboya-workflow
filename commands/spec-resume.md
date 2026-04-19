---
name: spec-resume
description: 중단된 /spec-from-pdf 세션을 이어받는다. --resume-latest 또는 초안 경로 지정 가능.
argument-hint: [--resume-latest | <draft-path>]
allowed-tools: Bash Read Write Edit mcp__claude_ai_Notion__*
---

# /spec-resume

중단된 세션을 Phase 진행 상태부터 이어받는다.

## 사용법

```
/spec-resume --resume-latest
/spec-resume /tmp/spec-draft-abc123-1700000000/draft.md
```

## 동작

1. 초안 경로를 결정 (최근 실행 or 명시된 경로)
2. 초안의 `<!-- plugin-state -->` 헤더에서 `phase` 읽기
3. `pdf-spec-organizer` Skill 을 **Resume 모드**로 진입 (해당 Phase 부터 재실행)

## 인자 처리

```bash
ARG="$1"

if [ -z "$ARG" ]; then
  echo "❌ --resume-latest 또는 초안 경로가 필요합니다." >&2
  exit 2
fi

if [ "$ARG" = "--resume-latest" ]; then
  # draft_registry 에서 running/failed 최신 조회
  LATEST=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" list-latest --count 10 \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
for e in data['entries']:
    if e['status'] in ('running', 'failed'):
        print(e['draft_path']); break
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

Skill 은 `MODE=resume` 를 인식해 Resume 모드 로직 실행. 초안의 `plugin-state` 헤더에서 phase 를 읽어 이어받기.
