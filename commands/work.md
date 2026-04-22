---
name: work
description: 일감(작업) 스펙 작성의 통합 진입점. 작업 유형(새 기능/버그 수정/기능 강화)과 PDF 유무를 묻고, 적절한 하위 워크플로우로 라우팅한다.
argument-hint: [--type=<feature|bug|enhancement>] [--pdf=<path>] [--no-pdf]
allowed-tools: Bash Read
---

# /work

일감 단위 스펙 작성 진입점. 작업 유형과 입력 자료(PDF 유무)를 확인한 뒤 적절한 하위 커맨드로 이어준다.

## 사용법

```
/work                                              # 대화형 — 전부 물어봄
/work --type=feature --pdf=~/Downloads/spec.pdf   # 한 번에 지정
/work --type=bug --no-pdf                         # PDF 없는 단순 작업
```

## 동작

Claude 가 아래 순서로 대화를 진행한다.

### Step 1. 작업 유형 확인

인자에 `--type=` 가 **없으면** 사용자에게 물어본다:

```
어떤 작업을 하시나요?
  1) 새 기능 (feature)
  2) 버그 수정 (bug)
  3) 기능 강화 (enhancement)
번호 또는 이름을 입력하세요.
```

입력을 `feature` / `bug` / `enhancement` 중 하나로 정규화. 알 수 없으면 재질문.

### Step 2. PDF 유무 확인

인자에 `--pdf=` / `--no-pdf` 가 **모두 없으면** 물어본다:

```
기획 PDF 가 있나요?
  - 있으면: 파일 경로를 입력 (예: ~/Downloads/spec.pdf)
  - 없으면: "없음" 또는 빈 줄 입력
```

경로가 입력되면 `~`/상대경로를 절대경로로 정규화하고 파일 존재를 확인 (없으면 재질문).

### Step 3. 라우팅

| 조건 | 처리 |
|---|---|
| PDF 있음 | `/spec-from-pdf <absolute-path>` 로 위임 (작업 유형은 초안 메타에 기록) |
| PDF 없음 | 아래 "PDF 없는 경우" 안내 출력 후 종료 |

#### PDF 없는 경우 (임시)

`/work` 는 진입점만 제공하고, PDF 없는 경로의 스펙 작성 자동화는 **다음 릴리스에서 지원 예정**. 현재는 아래 메시지를 출력한다:

```
ℹ️  PDF 없는 단순 작업용 스펙 경로는 아직 자동화되지 않았습니다.
    다음 중 하나로 진행해주세요:
      · Claude 에게 직접 스펙 초안을 요청 (예: "로그인 버그 수정 스펙 작성해줘")
      · 기존 Notion 페이지가 있으면 /spec-update <url> 로 이어 편집
      · 기획 PDF 가 생기면 /spec-from-pdf 로 전체 파이프라인 실행

    작업 유형: <정규화된 type>
```

## 인자 처리

```bash
TYPE=""
PDF_PATH=""
NO_PDF=""

while [ $# -gt 0 ]; do
  case "$1" in
    --type=*) TYPE="${1#--type=}"; shift;;
    --type)   TYPE="$2"; shift 2;;
    --pdf=*)  PDF_PATH="${1#--pdf=}"; shift;;
    --pdf)    PDF_PATH="$2"; shift 2;;
    --no-pdf) NO_PDF="1"; shift;;
    *)        echo "❌ 알 수 없는 인자: $1" >&2; exit 2;;
  esac
done

# 타입 정규화
case "$TYPE" in
  ""|feature|bug|enhancement) ;;  # 빈 값은 대화로 물어봄
  새기능|"새 기능"|1) TYPE="feature";;
  버그|"버그 수정"|2) TYPE="bug";;
  강화|"기능 강화"|3) TYPE="enhancement";;
  *) echo "❌ --type 값은 feature/bug/enhancement 중 하나여야 합니다: $TYPE" >&2; exit 2;;
esac

# PDF 경로 정규화
if [ -n "$PDF_PATH" ] && [ -n "$NO_PDF" ]; then
  echo "❌ --pdf 와 --no-pdf 를 동시에 지정할 수 없습니다." >&2
  exit 2
fi

if [ -n "$PDF_PATH" ]; then
  PDF_PATH=$(python3 -c "import sys, os; print(os.path.realpath(os.path.expanduser(sys.argv[1])))" "$PDF_PATH")
  if [ ! -f "$PDF_PATH" ]; then
    echo "❌ 파일을 찾을 수 없습니다: $PDF_PATH" >&2
    exit 1
  fi
fi

export WORK_TYPE="$TYPE"
export PDF_PATH NO_PDF
```

위 환경변수를 기반으로 Claude 가 Step 1 → Step 2 → Step 3 을 순차 수행한다.
빈 값인 경우에만 사용자에게 질문하고, 이미 지정된 값은 그대로 사용한다.

## 향후 확장

- PDF 없는 경우의 자동 스펙 작성 경로 (Superpowers 연계)
- 작업 유형별 템플릿 차등 (bug 는 재현 스텝/근본 원인, feature 는 AC/플로우)
- 완성된 스펙을 `superpowers:writing-plans` 로 자동 이어주기
