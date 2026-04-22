# 팀원 온보딩 HTML 설계 (v1)

**상태:** draft
**작성일:** 2026-04-22
**대상:** `yeoboya-workflow` 플러그인을 처음 접하는 iOS/Android 팀원
**산출물:** `docs/onboarding.html` — 단일 정적 HTML 파일

---

## 1. 요약

팀에 새로 합류한 iOS/Android 개발자가 **한 세션** 안에 `yeoboya-workflow` 플러그인 설치 → 첫 `/spec-from-pdf` 실행 → Notion 페이지 생성까지 완주할 수 있도록 돕는 단일 HTML 빠른 시작 가이드. 진행 상황은 localStorage 에 저장되어 페이지를 닫아도 이어 볼 수 있다.

## 2. 배경 · 동기

- 현재 온보딩 정보는 `README.md` 에 집중돼 있음. README 는 레퍼런스로서는 좋지만 **"처음 읽는 사람이 어디부터 손대야 하는지"** 알기 어려움.
- 체크리스트 형태로 단계별 완료 상태를 추적하면 "내가 어디까지 했지?" 문제를 없앨 수 있음.
- "왜 이 플러그인이 필요한지" 맥락이 설치 앞에 와야 신규 팀원 동기 부여가 됨 (현재 README 는 "뭐 하는 건가요" 블록은 있지만 스크롤 길어 쉽게 놓침).

## 3. 범위

### In-scope (v1)

- 단일 파일 `docs/onboarding.html`
- 4 섹션: Hero → Why → Checklist (6단계) → Next Steps
- localStorage 기반 체크리스트 진행 상태 저장/복원
- Tailwind CDN + Lucide Icons CDN 만 외부 의존
- 반응형 (모바일 1열, 데스크톱 다열)
- 기본 접근성 (키보드 토글, aria-*)

### Out-of-scope (v1)

- 다크모드 (v2 후보)
- 실시간 PDF 데모·샘플 실행 (D 옵션은 초기 brainstorming 에서 제외)
- GitHub Pages 배포 (사내 로컬 사용 전제)
- 다국어 (한국어만)
- 서버측 상태 동기화 (팀원 간 진행 상황 공유 X)

## 4. 파일 구조 · 배포

| 항목 | 결정 |
|---|---|
| 파일 경로 | `docs/onboarding.html` |
| 의존성 | Tailwind CDN (`https://cdn.tailwindcss.com`), Lucide Icons CDN |
| 실행 방식 | `open docs/onboarding.html` 로 브라우저 직접 열기 (서버 불필요) |
| 용량 목표 | 외부 CDN 제외 순수 HTML ~15-25 KB |
| 오프라인 | 최초 1회 온라인으로 CDN 캐시 후 오프라인 가능 |
| 진입 동선 | `README.md` 상단(제목·상태 배지 직후) 에 "**처음 오셨나요? →** [`docs/onboarding.html`](docs/onboarding.html) 빠른 시작" 한 줄 추가 |

## 5. 페이지 구조 (4 섹션)

### 5.1 Hero

- 플러그인 이름 (h1)
- 한 줄 설명 (README 첫 문장 재활용)
- 현재 버전 배지 (`v0.4.0` — README 상태 줄 참조)
- CTA 버튼: "**체크리스트 시작 →**" (클릭 시 #checklist 로 스크롤)

### 5.2 Why

README "왜 만들었나" 의 3가지 반복 문제를 **카드 3개** 로 요약:

| 카드 | 제목 | 핵심 문장 |
|---|---|---|
| 1 | 같은 PDF 를 두 번 읽기 | iOS/Android 가 각자 해석 → 구현 단계에서 어긋남 발견 |
| 2 | 엣지케이스를 구현 말미에 발견 | 에러·빈 상태·오프라인·권한·로딩·접근성 6개가 매번 빠짐 |
| 3 | 개발 기간 추정이 암묵지 | 과거 사례 없이 감으로만 대답, 신규 팀원이 감당 못 함 |

반응형: 모바일 1열, md (≥768px) 3열.

### 5.3 Checklist (메인 영역)

상단 sticky 진행률 바: "**3 / 6 완료**" + `<progress>` 또는 Tailwind 바. `role="progressbar"` + `aria-valuenow` + `aria-valuemax=6`.

6 단계:

| # | 제목 | 설명 (1-2 문장) | 명령어/링크 | 완료 조건 |
|---|---|---|---|---|
| 1 | 사전 준비 확인 | Notion MCP 연결됨, Tesseract 설치됨, Superpowers 플러그인 설치됨 (**단일 체크박스** — 3개를 각각 확인한 뒤 사용자가 한 번에 체크) | `brew install tesseract tesseract-lang` (Tesseract 만 해당) | 3개 모두 OK 상태 확인 |
| 2 | 플러그인 레포 확보 | GitHub 에서 `yeoboya-workflow` 레포 클론 | `git clone <repo-url>` | 로컬 경로 확보 |
| 3 | Claude Code 에 플러그인 등록 | `/plugin` 으로 등록 또는 `~/.claude/settings.json` 경로 추가 후 재시작 | `/plugin` | 커맨드 팔레트에 `/spec-from-pdf` 뜸 |
| 4 | 팀 공유 config 확인 | 프로젝트 레포 루트에 `yeoboya-workflow.config.json` 있는지 확인 | (파일 존재 여부만 확인) | 파일 존재 — 없으면 팀 리드에게 요청 |
| 5 | 샘플 PDF 로 첫 실행 | 가벼운 샘플 PDF 로 `/spec-from-pdf <path>` | `/spec-from-pdf ~/Downloads/sample.pdf` | Phase 1-5 모두 진행 |
| 6 | Notion 페이지 확인 | 생성된 Notion URL 열어 피처 DB 에 새 페이지 확인 | (URL 은 Phase 5 출력) | 페이지가 피처 DB 에 보임 |

각 항목 UI:
- `<input type="checkbox" id="step-N">` + `<label for="step-N">` 제목
- 설명 단락 (1-2 문장)
- 명령어/링크 블록 (있는 경우, `<pre><code>` Tailwind mono 스타일)
- 완료 조건 (작은 회색 텍스트, Lucide `check-circle` 아이콘 prefix)
- 완료 상태 스타일: `opacity-60` + 제목 `line-through`

### 5.4 Next Steps

첫 실행 성공 이후 이어 볼 문서들, `README.md` 섹션으로 점프:

- **일상 사용법** — 워크플로우 7 단계 + `--fast` 플래그 (`README.md#일상-사용법`)
- **협업 시나리오** — iOS/Android 가 같은 Notion 페이지에서 노트 공유 (`README.md#팀-협업-시나리오`)
- **`/spec-update` / `/spec-resume`** — 기존 페이지 갱신, 중단 세션 재개 (`README.md#커맨드-레퍼런스`)
- **트러블슈팅** — 자주 나는 문제·해결 (`README.md#트러블슈팅`)

## 6. JS 동작 명세

```js
// localStorage schema
{
  "yeoboya-onboarding:v1": {
    "step1": true,
    "step2": true,
    "step3": false,
    "step4": false,
    "step5": false,
    "step6": false
  }
}
```

### 이벤트 흐름

1. **페이지 로드** — localStorage 읽어서 각 체크박스 `checked` 속성 복원. 진행률 바 초기 계산.
2. **체크박스 change** — localStorage 해당 키 업데이트. 진행률 바 재계산. 항목 스타일(opacity/line-through) 토글.
3. **"진행 상태 초기화" 버튼 클릭** — `confirm()` 후 localStorage 해당 키 제거 + 체크박스 전체 해제 + 진행률 0 으로 리셋.

### 초기화 버튼 위치

푸터 좌측, 작은 secondary 스타일 (`text-slate-500 hover:text-slate-700 text-sm underline`).

## 7. 스타일 가이드

| 항목 | 값 |
|---|---|
| 배경 | `bg-slate-50` |
| 본문 텍스트 | `text-slate-900` |
| 부가 텍스트 | `text-slate-500`, `text-slate-600` |
| 카드 | `bg-white rounded-xl shadow-sm border border-slate-200 p-6` |
| CTA 버튼 | `bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium` |
| 완료 체크 색 | `text-emerald-500` (Lucide `check-circle`) |
| 완료 항목 | `opacity-60 line-through` |
| 코드블록 | `bg-slate-900 text-slate-100 rounded-md px-3 py-2 font-mono text-sm` |
| 한글 폰트 | `font-family: -apple-system, "Apple SD Gothic Neo", BlinkMacSystemFont, sans-serif;` (시스템 폰트, 추가 로딩 없음) |
| 반응형 | 기본 모바일 1열, `md:` (≥768px) 에서 Hero 2열·Why 3열 |

## 8. 접근성 요구사항

- 체크박스: 실제 `<input type="checkbox">` + `<label>` 연결, 키보드 `Space` 토글 가능
- 진행률 바: `role="progressbar"` + `aria-valuenow` + `aria-valuemax` + `aria-label="온보딩 진행률"`
- 섹션: `<section aria-labelledby="section-id">`, 제목에 해당 id
- 아이콘: `aria-hidden="true"` (의미는 텍스트로 전달)
- CTA 버튼: `<a>` 로 `href="#checklist"` (키보드 포커스 가능)

## 9. README 진입점 (변경 최소화)

README 상단 **"상태:" 줄 바로 아래, `---` 구분선 바로 위**에 1 줄 추가. 빈 줄을 사이에 두어 기존 문단과 시각적으로 분리:

```markdown
**상태:** v0.4.0 — 프로젝트 컨텍스트 기반 피처 메타 자동 제안 기능 추가

**처음 오셨나요?** → [`docs/onboarding.html`](docs/onboarding.html) 에서 빠른 시작 가이드.

---
```

## 10. 테스트 · QA 체크리스트

수동 QA (빌드/테스트 자동화 없이 단일 HTML 이므로 수동 확인):

- [ ] `open docs/onboarding.html` 으로 페이지 정상 로드
- [ ] 체크박스 6개 전부 클릭 가능, 각각 완료 스타일 토글
- [ ] 체크 후 새로고침 → 상태 유지
- [ ] "진행 상태 초기화" 클릭 → confirm 후 전체 해제
- [ ] 진행률 바 숫자·너비 실시간 반영
- [ ] 모바일 뷰포트 (Chrome DevTools 375px) 에서 깨짐 없음
- [ ] md (768px) 이상에서 Why 카드 3열 정렬
- [ ] 키보드만으로 모든 체크박스·CTA 에 포커스·조작 가능
- [ ] README 링크 점프 동작 (`#일상-사용법` 등)
- [ ] 최초 1회 온라인 로드 후, 오프라인으로 재방문 시에도 (브라우저 HTTP 캐시 활용) 레이아웃 깨지지 않음

## 11. 향후 확장 (v2+, YAGNI — 지금 만들지 말 것)

- 다크모드 (`prefers-color-scheme`)
- GitHub Pages 배포 + 공개 소개 페이지 분리
- 체크리스트 단계 커스터마이즈 (팀별 설정 JSON)
- 다국어 (영어)

---

## 결정 로그

| 결정 | 선택 | 근거 |
|---|---|---|
| 대상 | 팀원(iOS/Android) 사내용 | Q1: A |
| 타입 | 빠른 시작 가이드 + 인터랙티브 체크리스트 | Q2: B + C |
| 데모 포함 여부 | 제외 | 사용자 직접 "D는 필요없을 것 같아" |
| "왜 만들었나" 섹션 | 포함 | 사용자 추가 요청 |
| 체크리스트 범위 | 표준 (사전 준비 → 첫 실행 성공) | Q4: B |
| 기술 스택 | Tailwind CDN + 단일 HTML | Q5: B |
| 섹션 구성 | Hero → Why → Checklist → Next Steps | Q6: A |
