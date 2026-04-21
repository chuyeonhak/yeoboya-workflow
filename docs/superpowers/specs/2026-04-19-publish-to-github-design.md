# GitHub Private Repo 배포 설계

- 작성일: 2026-04-19
- 대상: `yeoboya-workflow` v0.1.1
- 저장소: `https://github.com/chuyeonhak/yeoboya-workflow` (Private)
- 상태: Draft (사용자 검토 대기)

## 배경

`yeoboya-workflow` v0.1.1 이 로컬 git 저장소에 안정적으로 릴리스됨. 팀원들이 이 플러그인을 사용하려면 원격 저장소에서 git clone 후 Claude Code settings 에 경로 등록해야 함. 외부 공개 전 민감 정보 정리 + 템플릿 파일 추가가 필요.

## 목표

- `chuyeonhak` 계정의 **Private GitHub 저장소** 로 전체 커밋 히스토리 + 태그 push
- 팀원이 `git clone` → Claude Code settings 경로 등록 → `config.json` 작성 → 사용 개시
- 민감 정보(실제 Notion DB ID 등) 외부 노출 방지

## 비목표

- Plugin Marketplace 등록 (v0.2 이후 고려)
- 공개 배포 / OSS 라이선스 (팀 내부 전용)
- CI/CD 셋업 (추후)

## 배포 방식

- **팀원 설치 플로우**: 수동 `git clone` + `~/.claude/settings.json` 에 플러그인 경로 등록
- **업데이트**: `git pull` (브랜치 기반, 태그 checkout 도 가능)

## 변경 대상 파일

| 경로 | 유형 | 설명 |
|---|---|---|
| `.gitignore` | 수정 | `yeoboya-workflow.config.json` 한 줄 추가 |
| `yeoboya-workflow.config.json.example` | 신규 | 팀원이 복사해 쓰는 템플릿 |
| `LICENSE` | 신규 | Proprietary 노티스 (여보야 팀 내부 전용) |
| `README.md` | 수정 | 절대 경로 `/Users/chuchu/...` → 상대 경로 |

## 각 파일 상세

### `.gitignore` 추가

```
yeoboya-workflow.config.json
```

로컬 드라이런 중 생성된 실제 Notion DB ID 가 들어있는 `yeoboya-workflow.config.json` 이 실수로 커밋되지 않도록 명시.

### `yeoboya-workflow.config.json.example` (신규)

```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "<your-feature-db-id>",
    "notion_data_source_id": "<your-data-source-id>",
    "parent_page_id": "<your-parent-page-id>"
  }
}
```

팀원은 이 파일을 **자신이 사용하는 프로젝트 레포 루트** 에 `yeoboya-workflow.config.json` 로 복사한 뒤 각 필드를 자기 Notion DB 값으로 채움.

### `LICENSE` (신규)

```
Copyright (c) 2026 여보야 팀

Proprietary — 여보야 팀 내부 사용 전용.
사전 서면 허가 없이 팀 외부 재배포/공개 금지.

All rights reserved.
```

### `README.md` 절대 경로 치환

치환 대상 라인 예시 (실제 파일에서 정확히 확인 필요):
- `/Users/chuchu/testPlugin/evals/trigger-eval.json` → `evals/trigger-eval.json`
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer` → `skills/pdf-spec-organizer`
- `run_loop.py` 실행 예시의 절대 경로는 **레포 루트 기준 상대 경로** 로 변경

치환 원칙: 레포 체크아웃 위치에 의존하지 않도록, 사용자가 알아야 할 상대 경로 (플러그인 레포 내부) 는 상대로, 사용자 환경별로 다른 경로 (예: venv, 다운로드 폴더) 는 `<placeholder>` 로.

## Push 플로우

```
1. 위 4개 파일 변경 (.gitignore 수정, example/LICENSE 신규, README 수정)
2. 커밋: "chore: prep for public repo — proprietary license, config example, relative paths"
3. gh repo create chuyeonhak/yeoboya-workflow --private --source=. --push
   → 현재 main 브랜치 + 모든 커밋 히스토리 push
4. git push origin v0.1.0 v0.1.1
   → 태그 별도 push
5. gh repo view chuyeonhak/yeoboya-workflow 로 확인
```

## 검증 기준

- `gh repo view chuyeonhak/yeoboya-workflow` 이 **private** 저장소 정상 표시
- `git log --oneline` 이 원격과 동기화됨 (약 32 커밋 + 2 태그)
- `yeoboya-workflow.config.json` 은 원격에 **존재하지 않음** (gitignored)
- `config.json.example` 은 원격에 존재
- 원격 README 렌더링에서 절대 경로 `/Users/chuchu/...` 검색 시 **0 hit**
- 팀원이 빈 디렉토리에서 `git clone` → 명령어 실행 가능한 상태

## 오픈 이슈

- 팀원 읽기/쓰기 권한 관리: 초기엔 개인 계정으로 push → 팀 콜라보레이터 초대로 접근 부여 (사용자 판단)
- 장기적으로 조직 계정 (예: `yeoboya/yeoboya-workflow`) 로 이관 가능성 — 이번 플랜 범위 밖
- CI/CD (pytest 자동 실행) — v0.2 이후 고려
