# spec-organizer Wrapper 스킬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `skills/spec-organizer/` wrapper 스킬을 만들고, `dispatcher.py` 결과에 따라 Skill tool 로 서브 스킬을 연쇄 호출하는 로직을 완성한다. trigger-eval 95%+ 정확도 달성.

**Architecture:** `spec-organizer/SKILL.md` 는 얇은 라우팅 레이어. 시작 시 `dispatcher.py` 호출 → `route` 결과 분기. `skill: X` 라우트 → Skill tool 로 X 호출. `action: redirect` → superpowers:brainstorming. `action: prompt/block/error` → 사용자 응답 처리.

**Tech Stack:** Markdown (SKILL.md), Python (scripts), Skill tool.

**Spec reference:** `docs/superpowers/specs/2026-04-22-spec-organizer-wrapper-design.md` (섹션 2, 6)

**PR 번호:** 4/8

**Depends on:** PR 1, 2, 3

---

## File Structure Overview

| 경로 | 유형 | 책임 |
|------|------|------|
| `skills/spec-organizer/SKILL.md` | 생성 | 얇은 라우팅 로직 (~200줄) |
| `skills/spec-organizer/scripts/entry.py` | 생성 | dispatcher 호출 + 결과 직렬화 |
| `skills/spec-organizer/scripts/_path_setup.py` | 생성 | common 참조 설정 |
| `skills/spec-organizer/scripts/tests/test_entry.py` | 생성 | |
| `evals/trigger-eval.json` | 수정 | spec-organizer 용으로 업데이트 |
| `.claude-plugin/plugin.json` | 수정 | skills 목록에 spec-organizer 추가 |

---

## Commit 1: 디렉터리 구조 + 경로 세팅

### Task 1.1: 스킬 디렉터리 생성

- [ ] **Step 1: 디렉터리 구조**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/spec-organizer/scripts/tests
```

- [ ] **Step 2: `_path_setup.py` 복사**

(PR 1 에서 만든 `pdf-spec-organizer/scripts/_path_setup.py` 와 동일 패턴)

`/Users/chuchu/testPlugin/skills/spec-organizer/scripts/_path_setup.py`:

```python
"""common/scripts/ 를 sys.path 에 주입."""
import sys
from pathlib import Path

COMMON_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "common" / "scripts"
)

if str(COMMON_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_SCRIPTS_DIR))

if not COMMON_SCRIPTS_DIR.exists():
    raise ImportError(f"common/scripts/ not found at {COMMON_SCRIPTS_DIR}")
```

- [ ] **Step 3: tests conftest**

`/Users/chuchu/testPlugin/skills/spec-organizer/scripts/tests/conftest.py`:

```python
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
COMMON_DIR = SCRIPTS_DIR.parent.parent / "common" / "scripts"
for d in (SCRIPTS_DIR, COMMON_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
```

---

## Commit 2: `entry.py` — 디스패처 호출 + JSON 출력

### Task 2.1: 진입점 스크립트

- [ ] **Step 1: 테스트**

`/Users/chuchu/testPlugin/skills/spec-organizer/scripts/tests/test_entry.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

ENTRY = Path(__file__).resolve().parent.parent / "entry.py"


def run_entry(*args):
    result = subprocess.run(
        [sys.executable, str(ENTRY), *args],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_pdf_with_hint(tmp_path):
    pdf = tmp_path / "s.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    out = run_entry(str(pdf), "--work-type", "새 기능")
    assert out["route"]["id"] == "pdf_single_new"
    assert out["work_type"] == "new_feature"


def test_text_bug_no_hint():
    out = run_entry("로그인", "버그")
    assert out["work_type"] == "bug_fix"
    assert out["route"]["id"] == "text_or_link_bug"


def test_empty():
    out = run_entry()
    assert out["route"]["id"] == "empty"
```

- [ ] **Step 2: 구현**

`/Users/chuchu/testPlugin/skills/spec-organizer/scripts/entry.py`:

```python
"""spec-organizer 의 디스패치 진입점.

Usage:
    python entry.py [ARGS...] [--work-type=HINT] [--mode=create|resume|update]

Output: stdout 에 JSON
    {
      "route": {...},      // routing.yaml 매치 결과
      "work_type": "bug_fix" | "new_feature" | "enhancement" | null,
      "mode": "create",
      "profile": {         // InputProfile 요약
        "pdf_count": 1,
        "image_count": 0,
        "urls": [...],
        "has_text_or_link": true,
        "free_text": "..."
      }
    }
"""
import argparse
import json
import sys
from dataclasses import asdict

from _path_setup import COMMON_SCRIPTS_DIR  # noqa: F401
from dispatcher import dispatch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("args", nargs="*", help="raw input args")
    parser.add_argument("--work-type", default=None)
    parser.add_argument("--mode", default="create", choices=["create", "resume", "update"])
    parsed = parser.parse_args()

    result = dispatch(parsed.args, work_type_hint=parsed.work_type, mode=parsed.mode)

    # JSON 직렬화용 정리
    output = {
        "mode": result["mode"],
        "work_type": result["work_type"].value if result["work_type"] else None,
        "route": result["route"],
        "profile": {
            "pdf_count": result["profile"].pdf_count,
            "image_count": result["profile"].image_count,
            "urls": result["profile"].urls,
            "pdf_paths": [str(p) for p in result["profile"].pdf_paths],
            "image_paths": [str(p) for p in result["profile"].image_paths],
            "free_text": result["profile"].free_text,
            "has_text_or_link": result["profile"].has_text_or_link,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/spec-organizer/scripts/tests && \
python3 -m pytest test_entry.py -v 2>&1 | tail -10
cd /Users/chuchu/testPlugin && \
git add skills/spec-organizer/ && \
git commit -m "feat(spec-organizer): entry.py 디스패처 진입점"
```

---

## Commit 3: `SKILL.md` — 얇은 라우팅 레이어

### Task 3.1: SKILL.md 작성

**Files:**
- Create: `skills/spec-organizer/SKILL.md`

- [ ] **Step 1: 파일 작성**

```markdown
---
name: spec-organizer
description: 여보야 iOS/Android 팀의 스펙 작성 진입점. PDF 기획서, 버그 리포트, 기능 개선 요청 등 다양한 입력을 받아 적절한 전문 스킬로 라우팅한다. 자연어 트리거 키워드: "PDF 스펙", "버그 리포트", "기능 강화", "새 기능 정리", "Notion 스펙 만들어줘", "로그인 버그 정리".
allowed-tools:
  - Bash
  - Read
  - Skill
  - mcp__claude_ai_Notion__*
---

# spec-organizer

여보야 iOS/Android 팀 스펙 작성의 **단일 진입점**. 입력 유형을 판별해 적절한 서브 스킬로 위임한다.

## 실행 흐름

### Phase 0: 디스패치

사용자 입력(인자 + 자연어)을 받으면 `scripts/entry.py` 를 호출해 라우팅 결과를 얻는다.

```bash
python skills/spec-organizer/scripts/entry.py [사용자_입력...] --work-type="$WORK_TYPE_HINT"
```

결과 JSON:
```json
{
  "mode": "create",
  "work_type": "bug_fix",
  "route": { "id": "...", "skill": "bug-spec-organizer", "phases": {...} },
  "profile": {...}
}
```

### Phase 1: 라우트 해석 및 분기

- **`route.skill` 이 있으면** (e.g. `bug-spec-organizer`): Skill tool 로 해당 스킬 호출
  - 컨텍스트 전달: `profile`, `work_type`, `phases`, `pdf_paths`, `free_text`, `urls`
- **`route.action == "redirect"`**: `route.target` (예: `superpowers:brainstorming`) 을 Skill tool 로 호출
  - 반환 후 `reentry_route` 로 매트릭스 재평가
- **`route.action == "prompt"`**: 사용자에게 `route.question` 또는 `choices` 를 제시하고 응답 수집 후 재디스패치
- **`route.action == "block"`**: `route.message` 출력 후 종료
- **`route.action == "error"`**: stderr 에 에러 + 종료 코드 1

### Phase 2: 서브 스킬 위임

서브 스킬 호출 시 다음 환경 변수/컨텍스트 전달:

```
PROFILE_JSON=$(...)
WORK_TYPE=bug_fix
PHASES={"1":"parse_only","3":"full","5":"full"}
MODE=create
```

서브 스킬이 처리 완료 후 반환 메시지 수신 → 사용자에게 최종 결과 요약.

## 자연어 트리거 예시

| 사용자 발화 | 기대 동작 |
|-------------|----------|
| "이 PDF 스펙 만들어줘" (PDF 첨부) | PDF + 새 기능 → pdf-spec-organizer |
| "로그인 버그 정리" | 텍스트 + 버그 → bug-spec-organizer |
| "다크모드 개선 방안 문서화" | 텍스트 + 강화 → enhancement-spec-organizer |
| "새 결제 시스템 기획" (PDF 없음) | 텍스트 + 새 기능 → brainstorming 리다이렉트 |

## Deprecated 커맨드 흡수

기존 `/spec-from-pdf`, `/spec-update`, `/spec-resume` 호출이 들어오면:
- 로그에 경고: `[DEPRECATED] ... 는 v1.5 에서 제거됩니다`
- 즉시 이 스킬로 위임 (`--mode=create/update/resume` 와 work_type_hint 자동 세팅)

## 에러 처리

- `entry.py` 실패 (exit code ≠ 0): stderr 출력 후 사용자에게 "디스패치 실패, 입력을 다시 확인해주세요" 안내
- Skill tool 호출 실패: 재시도 1회, 재실패 시 fallback 경로 제안 (raw Notion 수동 생성 등)

## 참조

- 설계 문서: `docs/superpowers/specs/2026-04-22-spec-organizer-wrapper-design.md`
- 라우팅 매트릭스: `skills/common/config/routing.yaml`
- work-type 스키마: `skills/common/config/work-type-schemas/*.yaml`
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/spec-organizer/SKILL.md && \
git commit -m "feat(spec-organizer): SKILL.md 얇은 라우팅 레이어"
```

---

## Commit 4: `trigger-eval.json` 업데이트

### Task 4.1: spec-organizer 용 트리거 평가

**Files:**
- Modify: `evals/trigger-eval.json` (기존 pdf-spec-organizer 용 → spec-organizer 용)

- [ ] **Step 1: 기존 파일 백업**

```bash
cp /Users/chuchu/testPlugin/evals/trigger-eval.json \
   /Users/chuchu/testPlugin/evals/trigger-eval-pdf-legacy.json
```

- [ ] **Step 2: spec-organizer 용 신규 작성**

`/Users/chuchu/testPlugin/evals/trigger-eval.json`:

```json
{
  "skill": "spec-organizer",
  "version": 1,
  "cases": [
    {"query": "이 PDF로 스펙 만들어줘", "should_trigger": true},
    {"query": "로그인 버그 정리해줘", "should_trigger": true},
    {"query": "다크모드 개선 방안 문서화", "should_trigger": true},
    {"query": "기획서를 Notion에 정리", "should_trigger": true},
    {"query": "이 기능 누락된 엣지케이스 있어?", "should_trigger": true},
    {"query": "/spec-from-pdf 써줘", "should_trigger": true},
    {"query": "새 결제 시스템 기획", "should_trigger": true},
    {"query": "QA 스크린샷 받아서 버그 리포트", "should_trigger": true},
    {"query": "로그인 개선 아이디어 있어", "should_trigger": true},
    {"query": "iOS/Android 동시 스펙 작성", "should_trigger": true},

    {"query": "이 코드 리팩터링해줘", "should_trigger": false},
    {"query": "파이썬 튜토리얼 알려줘", "should_trigger": false},
    {"query": "번역 좀 해줘", "should_trigger": false},
    {"query": "데이터베이스 스키마 설계", "should_trigger": false},
    {"query": "API 문서 작성", "should_trigger": false},
    {"query": "CI 파이프라인 설정", "should_trigger": false},
    {"query": "유닛 테스트 작성해줘", "should_trigger": false},
    {"query": "서버 배포 방법", "should_trigger": false},
    {"query": "로그 분석해줘", "should_trigger": false},
    {"query": "SQL 쿼리 최적화", "should_trigger": false}
  ]
}
```

- [ ] **Step 3: 실행 (사용자 스모크 테스트)**

이 eval 은 실제 트리거를 자동 측정할 수 없으므로, 수동 검증:
- 각 `should_trigger: true` 쿼리를 Claude Code 에 입력 → `spec-organizer` 스킬 트리거 확인
- `should_trigger: false` 쿼리는 트리거되지 않아야 함

목표 정확도 ≥95% (= 19/20 이상).

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add evals/trigger-eval.json evals/trigger-eval-pdf-legacy.json && \
git commit -m "test(evals): trigger-eval 을 spec-organizer 용으로 업데이트"
```

---

## Commit 5: `.claude-plugin/plugin.json` 등록

### Task 5.1: 플러그인 매니페스트 업데이트

- [ ] **Step 1: 현재 파일 확인**

```bash
cat /Users/chuchu/testPlugin/.claude-plugin/plugin.json
```

- [ ] **Step 2: `skills` 배열에 신규 항목 추가**

Edit 도구로 `skills` 배열에 다음 추가:

```json
{ "name": "spec-organizer", "path": "skills/spec-organizer" }
```

(기존 `pdf-spec-organizer` 항목은 유지)

- [ ] **Step 3: commands 의 deprecation 메타 추가 (선택)**

기존 `/spec-from-pdf`, `/spec-update`, `/spec-resume` 에 deprecated 플래그:

```json
{ "name": "spec-from-pdf", "path": "commands/spec-from-pdf.md", "deprecated": true }
```

- [ ] **Step 4: 검증 + 커밋**

```bash
python3 -c "
import json
with open('/Users/chuchu/testPlugin/.claude-plugin/plugin.json') as f:
    data = json.load(f)
assert any(s.get('name') == 'spec-organizer' for s in data.get('skills', []))
print('plugin.json OK')
"
cd /Users/chuchu/testPlugin && \
git add .claude-plugin/plugin.json && \
git commit -m "feat(plugin): spec-organizer 스킬 등록 + 레거시 deprecated 마킹"
```

---

## 완료 기준 (PR 4 Definition of Done)

- [ ] `skills/spec-organizer/` 디렉터리 및 `SKILL.md` (~200줄)
- [ ] `entry.py` + 테스트 PASS
- [ ] `trigger-eval.json` 20 케이스 (10/10 구성)
- [ ] `plugin.json` 에 등록
- [ ] 수동 스모크 테스트: "이 PDF 스펙 만들어줘" / "로그인 버그 정리" 둘 다 spec-organizer 트리거 확인

---

## 다음 플랜

→ `docs/superpowers/plans/2026-04-22-05-bug-spec-organizer.md` (PR 5)
