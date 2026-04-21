# Publish to GitHub (Private) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `yeoboya-workflow` v0.1.1 을 `chuyeonhak` 계정의 private GitHub 저장소로 배포해, 팀원이 `git clone` 후 Claude Code settings 에 경로 등록해 쓸 수 있게 한다.

**Architecture:** 4개 파일 변경 (.gitignore / config.example / LICENSE / README) → 1개 준비 커밋 → `gh repo create --private --source=. --push` → 태그 별도 push → GitHub 에서 상태 확인.

**Tech Stack:** git, GitHub CLI (`gh`), Markdown.

**Spec reference:** `docs/superpowers/specs/2026-04-19-publish-to-github-design.md`

---

## File Structure Overview

| 경로 | 유형 | 이번 플랜에서 |
|---|---|---|
| `.gitignore` | 수정 | `yeoboya-workflow.config.json` 1 줄 추가 |
| `yeoboya-workflow.config.json.example` | 신규 | 팀원용 설정 템플릿 |
| `LICENSE` | 신규 | Proprietary 노티스 |
| `README.md` | 수정 | 절대 경로 `/Users/chuchu/...` → 상대 경로 |

---

## Task 1: 사전 상태 확인

**Files:** (읽기만)

- [ ] **Step 1: 현재 git 상태 + 원격 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && \
git status --short && \
echo "---" && \
git remote -v && \
echo "---" && \
git tag
```

Expected:
- `git status` 에 `?? yeoboya-workflow.config.json` 포함 (민감 파일이 untracked 상태)
- `git remote -v` 는 **비어있어야** 함 (아직 원격 없음). 이미 있으면 Task 7 전에 판단 필요
- `git tag` 에 `v0.1.0` 과 `v0.1.1` 둘 다 존재

- [ ] **Step 2: 절대 경로 대상 확인**

Run:
```bash
grep -n "/Users/chuchu/testPlugin" /Users/chuchu/testPlugin/README.md
```

Expected: 여러 라인 출력 (실제 라인은 파일 내용에 따라 다름). 각 매치 위치를 Task 5 에서 치환 대상.

민감 정보가 다른 파일에 있는지 스캔:
```bash
grep -rn "/Users/chuchu" /Users/chuchu/testPlugin --include="*.md" --exclude-dir=.venv --exclude-dir=docs | head -20
```

Expected: README.md 이외에서 매치 없거나 최소. 있다면 Task 5 범위 확장 고려.

`gh` CLI 인증 확인:
```bash
gh auth status 2>&1 | head -5
```

Expected: `Logged in to github.com account chuyeonhak` 포함. 실패 시 `gh auth login` 필요 (사용자 개입).

---

## Task 2: `.gitignore` 수정

**Files:**
- Modify: `/Users/chuchu/testPlugin/.gitignore`

- [ ] **Step 1: 현재 `.gitignore` 확인**

Run:
```bash
cat /Users/chuchu/testPlugin/.gitignore
```

Expected 출력 (내용 파악용):
```
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
/tmp/
*.DS_Store
```

- [ ] **Step 2: 파일 끝에 한 줄 추가**

Edit 도구 호출:
- `file_path`: `/Users/chuchu/testPlugin/.gitignore`
- `old_string`: `*.DS_Store\n` (파일 마지막 줄)
- `new_string`:
```
*.DS_Store
yeoboya-workflow.config.json
```

> **주의:** `old_string` 이 파일 마지막 줄이라 개행 처리에 유의. 실제 파일에는 `*.DS_Store` 뒤에 개행이 있을 수도 없을 수도 있음. Edit 실패 시 Read 로 실제 바이트 확인 후 재시도.

- [ ] **Step 3: 검증**

Run:
```bash
tail -3 /Users/chuchu/testPlugin/.gitignore
```

Expected: 마지막 라인이 `yeoboya-workflow.config.json`.

Run:
```bash
cd /Users/chuchu/testPlugin && git status --short | grep "yeoboya-workflow.config.json"
```

Expected: **출력 없음** (파일이 gitignore 에 매치되어 untracked 목록에서 사라짐).

---

## Task 3: `yeoboya-workflow.config.json.example` 생성

**Files:**
- Create: `/Users/chuchu/testPlugin/yeoboya-workflow.config.json.example`

- [ ] **Step 1: 파일 작성**

Write 도구로 `/Users/chuchu/testPlugin/yeoboya-workflow.config.json.example` 을 정확히 아래 내용으로 생성:

```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "<your-feature-db-id>",
    "notion_data_source_id": "<your-data-source-id>",
    "parent_page_id": "<your-parent-page-id>"
  }
}
```

- [ ] **Step 2: 유효성 검증**

Run:
```bash
python3 -c "import json; json.load(open('/Users/chuchu/testPlugin/yeoboya-workflow.config.json.example')); print('OK')"
```
Expected: `OK`

---

## Task 4: `LICENSE` 생성

**Files:**
- Create: `/Users/chuchu/testPlugin/LICENSE`

- [ ] **Step 1: 파일 작성**

Write 도구로 `/Users/chuchu/testPlugin/LICENSE` 을 정확히 아래 내용으로 생성:

```
Copyright (c) 2026 여보야 팀

Proprietary — 여보야 팀 내부 사용 전용.
사전 서면 허가 없이 팀 외부 재배포/공개 금지.

All rights reserved.
```

- [ ] **Step 2: 확인**

Run:
```bash
cat /Users/chuchu/testPlugin/LICENSE
```
Expected: 위 5줄 정확히 출력.

---

## Task 5: README 절대 경로 → 상대 경로

**Files:**
- Modify: `/Users/chuchu/testPlugin/README.md`

- [ ] **Step 1: 절대 경로 매치 위치 파악**

Run:
```bash
grep -n "/Users/chuchu/testPlugin" /Users/chuchu/testPlugin/README.md
```

Expected: 여러 라인. Task 1 에서 이미 확인한 결과와 동일.

Run:
```bash
grep -cn "/Users/chuchu/testPlugin" /Users/chuchu/testPlugin/README.md
```
Expected: 매치 개수. 이 숫자를 Step 3 검증에 사용.

- [ ] **Step 2: Edit 으로 치환**

각 매치를 Edit 도구로 하나씩 치환. 가장 많이 등장하는 패턴들:

**치환 규칙:**
- `/Users/chuchu/testPlugin/evals/trigger-eval.json` → `<플러그인-루트>/evals/trigger-eval.json`
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer` → `<플러그인-루트>/skills/pdf-spec-organizer`
- `/Users/chuchu/testPlugin/` 로만 끝나는 참조 → `<플러그인-루트>/`
- `/Users/chuchu/testPlugin` (끝 슬래시 없음) → `<플러그인-루트>`

> **`<플러그인-루트>` 플레이스홀더 의미:** 팀원이 `git clone` 으로 체크아웃한 실제 로컬 경로 (예: `~/projects/yeoboya-workflow`). README 서두에 이 표기법을 명시하는 안내 한 줄 추가 권장.

**Edit 접근:** 가장 자주 등장하는 맥락이 `pip install -r /Users/chuchu/testPlugin/skills/...` 같은 명령 블록임. 각 Edit 호출 시 전체 명령이나 한 줄을 `old_string` 으로 주고 상대화된 버전을 `new_string` 으로 준다.

**`<플러그인-루트>` 설명 추가** (README 상단 "설치" 섹션 근처):

Edit 호출로 "설치" 섹션 시작 직후에 아래 한 줄 append:

```markdown
> **경로 표기 안내:** 이 문서에서 `<플러그인-루트>` 는 `git clone` 으로 받은 이 레포의 로컬 경로 (예: `~/projects/yeoboya-workflow`) 를 의미합니다.
```

정확한 위치는 README 의 실제 구조에 따라 조정. 기본 원칙: 경로 표기 사용 전에 한 번 설명.

- [ ] **Step 3: 검증**

Run:
```bash
grep -c "/Users/chuchu" /Users/chuchu/testPlugin/README.md
```

Expected: **0** (절대 경로가 완전히 제거됨).

Run:
```bash
grep -c "<플러그인-루트>" /Users/chuchu/testPlugin/README.md
```

Expected: **1 이상** (치환된 상대 경로 표기가 존재).

---

## Task 6: 준비 변경 커밋

**Files:** (커밋 작업만)

- [ ] **Step 1: 변경 파일 확인**

Run:
```bash
cd /Users/chuchu/testPlugin && git status --short
```

Expected:
```
 M .gitignore
 M README.md
?? LICENSE
?? yeoboya-workflow.config.json.example
```

(실제 `yeoboya-workflow.config.json` 은 `.gitignore` 에 잡혀 나오지 않아야 함)

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add .gitignore README.md LICENSE yeoboya-workflow.config.json.example && \
git commit -m "chore: prep for public repo — proprietary license, config example, relative paths"
```

Expected: 커밋 성공. 4 파일, insertions/deletions 출력.

- [ ] **Step 3: 민감 파일 미포함 재확인**

Run:
```bash
git log -1 --stat
```

Expected: 커밋에 `yeoboya-workflow.config.json` (example 가 아닌 원본) 이 **포함되지 않음** 확인. example 만 있어야 함.

---

## Task 7: GitHub 원격 저장소 생성 + push

**Files:** (git 작업만)

- [ ] **Step 1: gh 인증 재확인**

Run:
```bash
gh auth status 2>&1 | head -5
```

Expected: `Logged in to github.com account chuyeonhak`.

- [ ] **Step 2: 기존 같은 이름 레포 충돌 확인**

Run:
```bash
gh repo view chuyeonhak/yeoboya-workflow 2>&1 | head -3
```

Expected (신규 생성 가능한 상태):
```
GraphQL: Could not resolve to a Repository with the name 'chuyeonhak/yeoboya-workflow'. (repository)
```

만약 레포가 이미 존재한다면 **중단하고 사용자에게 확인**. 삭제 후 재생성 또는 다른 이름 사용 결정.

- [ ] **Step 3: 레포 생성 + 현재 브랜치 push**

```bash
cd /Users/chuchu/testPlugin && \
gh repo create chuyeonhak/yeoboya-workflow \
  --private \
  --source=. \
  --description "여보야 팀 워크플로우 자동화 Claude Code 플러그인 — PDF 스펙 → Notion + 플랫폼별 개발자 노트 공유" \
  --push
```

Expected:
- `https://github.com/chuyeonhak/yeoboya-workflow` 생성 확인 메시지
- 현재 `main` 브랜치 + 모든 커밋 push 완료

- [ ] **Step 4: push 결과 확인**

Run:
```bash
git remote -v
```
Expected: `origin` 이 `https://github.com/chuyeonhak/yeoboya-workflow.git` 를 가리킴 (fetch + push 두 줄).

Run:
```bash
git log --oneline origin/main | head -5
```
Expected: 최근 5 커밋 (로컬과 동일).

---

## Task 8: 태그 push

**Files:** (git 작업만)

- [ ] **Step 1: 로컬 태그 확인**

Run:
```bash
git tag
```
Expected: `v0.1.0`, `v0.1.1` (2 개).

- [ ] **Step 2: 태그 push**

```bash
cd /Users/chuchu/testPlugin && git push origin v0.1.0 v0.1.1
```

Expected: `* [new tag]` 두 번.

- [ ] **Step 3: 원격 태그 확인**

Run:
```bash
gh release list --repo chuyeonhak/yeoboya-workflow 2>&1 | head -3
```

릴리스는 아직 없지만 태그만 있는 상태. 릴리스 자동 생성은 이 플랜 범위 밖 (추후 필요 시 `gh release create v0.1.1 --notes-file CHANGELOG.md` 로 생성).

Run:
```bash
git ls-remote --tags origin | grep -E "v0.1.0|v0.1.1"
```
Expected: 두 태그 SHA 출력.

---

## Task 9: 최종 검증

**Files:** (확인만)

- [ ] **Step 1: GitHub 레포 메타 확인**

Run:
```bash
gh repo view chuyeonhak/yeoboya-workflow --json visibility,defaultBranchRef,url
```

Expected:
- `visibility` == `PRIVATE`
- `defaultBranchRef.name` == `main`
- `url` == `https://github.com/chuyeonhak/yeoboya-workflow`

- [ ] **Step 2: 민감 파일 원격 부재 확인**

Run:
```bash
gh api repos/chuyeonhak/yeoboya-workflow/contents/yeoboya-workflow.config.json 2>&1 | head -3
```

Expected: `"status":"404"` 또는 `"Not Found"` (파일이 없어야 함).

Run:
```bash
gh api repos/chuyeonhak/yeoboya-workflow/contents/yeoboya-workflow.config.json.example 2>&1 | grep -o '"name":"[^"]*"'
```

Expected: `"name":"yeoboya-workflow.config.json.example"` (example 파일은 존재).

- [ ] **Step 3: 절대 경로 원격 스캔**

Run:
```bash
gh api repos/chuyeonhak/yeoboya-workflow/contents/README.md --jq '.content' | base64 -d | grep -c "/Users/chuchu"
```

Expected: `0` (원격 README 에서 홈 경로 0 hit).

- [ ] **Step 4: 커밋 히스토리 개수 일치**

Run:
```bash
git rev-list --count HEAD
```
로컬 커밋 수 기록.

Run:
```bash
git rev-list --count origin/main
```
원격 커밋 수. 두 값 **일치** 해야 함.

- [ ] **Step 5: 팀원 온보딩 가이드 메모**

플랜 완료 후 사용자가 팀원에게 공유할 내용:

```
1. GitHub 에서 chuyeonhak/yeoboya-workflow 에 Collaborator 로 초대받기
2. git clone git@github.com:chuyeonhak/yeoboya-workflow.git ~/projects/yeoboya-workflow
3. ~/.claude/settings.json 에 플러그인 경로 등록
4. pip install -r <플러그인-루트>/skills/pdf-spec-organizer/scripts/requirements.txt
5. 자신 프로젝트 레포에 yeoboya-workflow.config.json.example 복사 → yeoboya-workflow.config.json 으로 rename → DB ID 채우기
6. Claude Code 재시작 → /spec-from-pdf 로 검증
```

이 가이드는 Task 9 산출물이지만 파일에 저장하는 것은 선택 (Slack 이나 위키 같은 별도 소통 채널에 공유하는 게 실용적).

---

## Task 10: 정리

**Files:** (선택적 cleanup)

- [ ] **Step 1: 임시 / 드라이런 산출물 정리**

Run:
```bash
ls /tmp/spec-draft-* /tmp/run_loop_output /tmp/skill-refactor-verify-* 2>/dev/null | head -10
```

기존 드라이런 폴더가 남아있을 수 있음. `/tmp` 는 자동 정리되므로 필수 아님. 수동 제거 원하면:

```bash
rm -rf /tmp/run_loop_output
```

- [ ] **Step 2: 로컬 `yeoboya-workflow.config.json` 유지 여부 결정**

이 파일은 드라이런 때 테스트용으로 만든 것. 이제 팀에 배포되면 **실제 팀 Notion DB** 로 이 파일을 실제 사용할지 결정:

- **유지** → 실제 팀 워크플로우의 단일 설정으로 사용 (이 레포가 팀 프로젝트 레포 역할)
- **삭제** → 테스트 종료, 사용자는 실제 프로젝트 레포에서 새 config 작성

사용자 판단 — 이번 플랜에서는 아무것도 안 함.

---

## Oracle 이슈 (이번 플랜 범위 밖)

- 팀원 Collaborator 초대 — GitHub Settings UI 에서 사용자가 수동 처리
- 조직 계정 (`yeoboya/*`) 으로 이관 — 장기 고려사항
- GitHub Actions (pytest 자동 실행) — v0.2 이후
- Release notes 자동 생성 (`gh release create v0.1.1 --notes-file ...`) — 필요 시 추후
