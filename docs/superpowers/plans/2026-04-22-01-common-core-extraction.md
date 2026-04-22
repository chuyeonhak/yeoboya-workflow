# Common Core Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `skills/pdf-spec-organizer/scripts/` 에 있는 재사용 가능한 Python 모듈 8개를 `skills/common/scripts/` 로 이동하고, 기존 import 경로를 복구한다. 기능 변경 없이 디렉터리 구조만 재정비한다.

**Architecture:** `common/scripts/` 를 신규 생성 → 8개 파일을 `git mv` → 각 파일의 상호 import 경로 수정 → 기존 `pdf-spec-organizer/scripts/` 에 남는 파일(`parse_pdf.py`, `ocr_fallback.py`, `migrate_to_per_pdf.py`)이 `common/` 을 참조하도록 `sys.path` hack 추가. 기존 13개 테스트는 import path 만 수정 후 100% 통과해야 한다.

**Tech Stack:** Python 3.x, pytest, git mv.

**Spec reference:** `docs/superpowers/specs/2026-04-22-spec-organizer-wrapper-design.md` (섹션 2.1, 2.2)

**PR 번호:** 1/8

---

## File Structure Overview

| 경로 | 유형 | 이번 플랜에서 |
|------|------|---------------|
| `skills/common/` | 생성 | 신규 디렉터리 |
| `skills/common/scripts/__init__.py` | 생성 | 빈 파일 (패키지 마커) |
| `skills/common/scripts/draft_registry.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/enrich_features.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/feature_id.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/note_extractor.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/note_merger.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/page_publisher.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/pdf_hash.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/pii_scan.py` | 이동 | 기존에서 이동 |
| `skills/common/scripts/requirements.txt` | 이동 | 기존에서 이동 |
| `skills/common/scripts/tests/` | 이동 | 해당 테스트 파일들 함께 이동 |
| `skills/pdf-spec-organizer/scripts/_path_setup.py` | 생성 | `common/scripts/` 를 `sys.path` 에 주입 |
| `skills/pdf-spec-organizer/scripts/parse_pdf.py` | 수정 | `_path_setup` import 추가 |
| `skills/pdf-spec-organizer/scripts/ocr_fallback.py` | 수정 | `_path_setup` import 추가 |
| `skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py` | 수정 | `_path_setup` import 추가 |
| `skills/pdf-spec-organizer/SKILL.md` | 수정 | scripts 경로 참조 업데이트 |

---

## Commit 1: 디렉터리 골격 + 테스트 샘플 준비

### Task 1.1: `common/scripts/` 디렉터리 생성

**Files:**
- Create: `skills/common/scripts/__init__.py`
- Create: `skills/common/scripts/tests/__init__.py`

- [ ] **Step 1: 디렉터리 트리 생성**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/common/scripts/tests/samples
```

- [ ] **Step 2: `__init__.py` 생성 (2개)**

`/Users/chuchu/testPlugin/skills/common/scripts/__init__.py`:
```python
# common scripts package
```

`/Users/chuchu/testPlugin/skills/common/scripts/tests/__init__.py`:
```python
# common scripts tests package
```

- [ ] **Step 3: 존재 검증**

```bash
ls -la /Users/chuchu/testPlugin/skills/common/scripts/__init__.py \
      /Users/chuchu/testPlugin/skills/common/scripts/tests/__init__.py
```
Expected: 두 파일 모두 존재, 크기 > 0 bytes.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/__init__.py skills/common/scripts/tests/__init__.py && \
git commit -m "feat(common): skills/common/scripts/ 패키지 골격 생성"
```

---

## Commit 2: 8개 스크립트 이동 (git mv 로 히스토리 보존)

### Task 2.1: 재사용 스크립트 일괄 이동

**Files:** 8개 이동

- [ ] **Step 1: git mv 실행**

```bash
cd /Users/chuchu/testPlugin && \
git mv skills/pdf-spec-organizer/scripts/draft_registry.py  skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/enrich_features.py skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/feature_id.py      skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/note_extractor.py  skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/note_merger.py     skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/page_publisher.py  skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/pdf_hash.py        skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/pii_scan.py        skills/common/scripts/ && \
git mv skills/pdf-spec-organizer/scripts/requirements.txt   skills/common/scripts/
```

- [ ] **Step 2: 이동 확인**

```bash
ls /Users/chuchu/testPlugin/skills/common/scripts/ | sort
```
Expected 출력 (정렬):
```
__init__.py
draft_registry.py
enrich_features.py
feature_id.py
note_extractor.py
note_merger.py
page_publisher.py
pdf_hash.py
pii_scan.py
requirements.txt
tests
```

- [ ] **Step 3: 원본 디렉터리 남은 파일 확인**

```bash
ls /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/ | sort
```
Expected: `migrate_to_per_pdf.py`, `ocr_fallback.py`, `parse_pdf.py`, `tests` 4개만 존재 (+ `__pycache__` 가능).

- [ ] **Step 4: 커밋 (파일 이동만)**

```bash
cd /Users/chuchu/testPlugin && \
git commit -m "refactor(common): 재사용 스크립트 8개를 common/scripts/ 로 이동

- draft_registry, enrich_features, feature_id, note_extractor,
  note_merger, page_publisher, pdf_hash, pii_scan, requirements.txt
- PDF 전용(parse_pdf, ocr_fallback, migrate_to_per_pdf)은 잔류"
```

---

### Task 2.2: 테스트 파일 이동

**Files:** 8개 테스트 + samples

- [ ] **Step 1: 해당 테스트 파일 이동**

```bash
cd /Users/chuchu/testPlugin && \
git mv skills/pdf-spec-organizer/scripts/tests/test_draft_registry.py  skills/common/scripts/tests/ && \
git mv skills/pdf-spec-organizer/scripts/tests/test_enrich_features.py skills/common/scripts/tests/ && \
git mv skills/pdf-spec-organizer/scripts/tests/test_feature_id.py      skills/common/scripts/tests/ && \
git mv skills/pdf-spec-organizer/scripts/tests/test_note_extractor.py  skills/common/scripts/tests/ && \
git mv skills/pdf-spec-organizer/scripts/tests/test_note_merger.py     skills/common/scripts/tests/ && \
git mv skills/pdf-spec-organizer/scripts/tests/test_page_publisher.py  skills/common/scripts/tests/ && \
git mv skills/pdf-spec-organizer/scripts/tests/test_pdf_hash.py        skills/common/scripts/tests/ && \
git mv skills/pdf-spec-organizer/scripts/tests/test_pii_scan.py        skills/common/scripts/tests/
```

- [ ] **Step 2: samples 디렉터리 상태 확인**

```bash
ls /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/samples/ 2>&1
```
samples 가 공용이면 common 으로, PDF 전용이면 유지. 기본적으로 **PDF 전용 파일이 많을 것**이므로 유지하되, 필요 시 선택적으로 이동.

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git commit -m "refactor(common): 테스트 파일 8개를 common/scripts/tests/ 로 이동"
```

---

## Commit 3: 상호 import 경로 수정 (common 내부)

### Task 3.1: `common/scripts/` 내부 파일들의 import 업데이트

**Files:** `common/scripts/*.py` 중 다른 파일을 참조하는 것들

- [ ] **Step 1: 현재 상호 import 목록 파악**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/common/scripts && \
grep -n "^from \|^import " draft_registry.py enrich_features.py feature_id.py \
  note_extractor.py note_merger.py page_publisher.py pdf_hash.py pii_scan.py \
  | grep -v "^.*:.*import \(os\|sys\|re\|json\|pathlib\|typing\|dataclass\|collections\|datetime\|logging\|subprocess\|tempfile\|hashlib\)" \
  | grep -v "pytest\|pydantic\|yaml"
```

상대 import 가 있으면 그것이 수정 대상. 출력 예시:
```
enrich_features.py:15:from feature_id import FeatureID
enrich_features.py:16:from pdf_hash import compute_hash
note_merger.py:23:from note_extractor import extract_sections
```

- [ ] **Step 2: 상대 import 유지 여부 판단**

**같은 패키지 내부** 파일끼리의 import 는 경로 변경 없이 그대로 동작 (Python 모듈 해석은 파일 이동에 불변).

단, **절대 경로로 import** (예: `from skills.pdf_spec_organizer.scripts.feature_id import ...`) 하는 경우에만 수정 필요.

Run:
```bash
cd /Users/chuchu/testPlugin/skills/common/scripts && \
grep -rn "pdf_spec_organizer\|pdf-spec-organizer" *.py
```
Expected: 출력 없음 (= 수정 불필요). 출력이 있으면 Step 3 에서 수정.

- [ ] **Step 3: 출력이 있었을 경우만 Edit**

(출력이 없었다면 이 Step 은 스킵)

각 파일에 대해 Edit 도구로 `from pdf_spec_organizer.scripts.X` → `from X` 로 변경.

- [ ] **Step 4: 테스트 import 경로 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
grep -n "^from \|^import " test_*.py | grep -v "pytest\|unittest\|tempfile\|pathlib\|os\|sys\|json"
```
Expected: `from feature_id import ...`, `from note_extractor import ...` 등 **상대 import 만** 존재.

`pdf_spec_organizer` 절대 경로가 있으면 Edit 로 수정.

- [ ] **Step 5: 커밋 (변경이 있었을 때만)**

```bash
cd /Users/chuchu/testPlugin && \
git diff --cached --stat   # 변경 확인
git commit -m "refactor(common): 내부 import 경로를 common/scripts/ 기준으로 정규화"
```

변경 없으면 이 Step 스킵.

---

## Commit 4: `pdf-spec-organizer/scripts/` 의 `_path_setup` 도입

### Task 4.1: `_path_setup.py` 생성

**Files:**
- Create: `skills/pdf-spec-organizer/scripts/_path_setup.py`

- [ ] **Step 1: `_path_setup.py` 작성**

`/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/_path_setup.py`:

```python
"""Common scripts 경로를 sys.path 에 주입한다.

이 모듈을 import 하는 것만으로 common/scripts/ 의 모듈을 import 할 수 있게 된다.
import 순서: `_path_setup` 을 반드시 `from X import Y` 보다 먼저 호출해야 한다.

사용 예:
    from _path_setup import COMMON_SCRIPTS_DIR  # noqa: F401
    from pii_scan import scan_text              # common/scripts/pii_scan.py
"""
import sys
from pathlib import Path

COMMON_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "common" / "scripts"
)

if str(COMMON_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_SCRIPTS_DIR))

if not COMMON_SCRIPTS_DIR.exists():
    raise ImportError(
        f"common/scripts/ not found at {COMMON_SCRIPTS_DIR}. "
        f"plugin installation may be broken."
    )
```

- [ ] **Step 2: 빠른 실행 검증**

```bash
cd /Users/chuchu/testPlugin && \
python3 -c "
import sys
sys.path.insert(0, 'skills/pdf-spec-organizer/scripts')
import _path_setup
print('COMMON_SCRIPTS_DIR:', _path_setup.COMMON_SCRIPTS_DIR)
print('exists:', _path_setup.COMMON_SCRIPTS_DIR.exists())
# common 모듈 import 시도
import feature_id
print('feature_id imported from:', feature_id.__file__)
"
```
Expected:
```
COMMON_SCRIPTS_DIR: /Users/chuchu/testPlugin/skills/common/scripts
exists: True
feature_id imported from: /Users/chuchu/testPlugin/skills/common/scripts/feature_id.py
```

---

### Task 4.2: `parse_pdf.py` / `ocr_fallback.py` / `migrate_to_per_pdf.py` 가 common 참조

**Files:**
- Modify: `skills/pdf-spec-organizer/scripts/parse_pdf.py` (상단 import 블록)
- Modify: `skills/pdf-spec-organizer/scripts/ocr_fallback.py`
- Modify: `skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py`

- [ ] **Step 1: 각 파일이 어떤 common 모듈을 import 하는지 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts && \
for f in parse_pdf.py ocr_fallback.py migrate_to_per_pdf.py; do
  echo "=== $f ==="
  grep -E "^from \w+ import|^import \w+" "$f" | grep -v "^.*import \(os\|sys\|re\|json\|pathlib\|typing\|dataclass\|collections\|datetime\|logging\|subprocess\|tempfile\|hashlib\|fitz\|pytesseract\|PIL\)"
done
```

output 에 `pii_scan`, `pdf_hash`, `feature_id` 같은 common 모듈이 등장하면 해당 파일은 수정 필요.

- [ ] **Step 2: 파일마다 상단 import 블록에 `_path_setup` 삽입**

Edit 도구로 각 파일의 기존 import 블록 최상단에 다음 2줄 추가:

```python
from _path_setup import COMMON_SCRIPTS_DIR  # noqa: F401
```

**위치 규칙:** 표준 라이브러리 import 다음, 로컬 import 이전.

예 — `parse_pdf.py` 수정 전:
```python
import sys
import json
from pathlib import Path

from pdf_hash import compute_hash  # 기존: 같은 디렉터리 가정
```

수정 후:
```python
import sys
import json
from pathlib import Path

from _path_setup import COMMON_SCRIPTS_DIR  # noqa: F401
from pdf_hash import compute_hash
```

- [ ] **Step 3: 3개 파일 모두 수정 후 간단 실행**

```bash
cd /Users/chuchu/testPlugin && \
python3 -c "
import sys
sys.path.insert(0, 'skills/pdf-spec-organizer/scripts')
import parse_pdf
print('parse_pdf OK')
import ocr_fallback
print('ocr_fallback OK')
import migrate_to_per_pdf
print('migrate_to_per_pdf OK')
"
```
Expected: 세 줄 모두 "OK".

에러 발생 시 import 순서 재점검.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/pdf-spec-organizer/scripts/_path_setup.py \
        skills/pdf-spec-organizer/scripts/parse_pdf.py \
        skills/pdf-spec-organizer/scripts/ocr_fallback.py \
        skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py && \
git commit -m "refactor(pdf): _path_setup 으로 common/scripts/ 모듈 참조"
```

---

## Commit 5: 테스트 전체 재검증

### Task 5.1: `common/scripts/tests/` 실행

**Files:** (변경 없음 — 실행만)

- [ ] **Step 1: common 테스트 실행**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest -v 2>&1 | tail -30
```

Expected: **모든 테스트 PASS**. FAIL 이 있으면 import 경로 문제.

- [ ] **Step 2: FAIL 이 `ModuleNotFoundError` 인 경우 대처**

테스트 파일이 현재 디렉터리의 부모(= `scripts/`) 를 sys.path 에 추가해야 할 수도 있음. 각 `test_*.py` 최상단에 conftest 패턴 또는 다음을 추가:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

단, `pytest.ini` 또는 `conftest.py` 를 쓰는 게 더 깔끔. **Step 3 참고**.

- [ ] **Step 3: `conftest.py` 로 일괄 처리**

Create `/Users/chuchu/testPlugin/skills/common/scripts/tests/conftest.py`:

```python
"""pytest 공통 설정: 상위 디렉터리를 sys.path 에 자동 추가."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
```

- [ ] **Step 4: 재실행**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest -v 2>&1 | tail -30
```

Expected: 모든 테스트 PASS. 실패 남으면 개별 파일 디버깅.

---

### Task 5.2: `pdf-spec-organizer/scripts/tests/` 실행

- [ ] **Step 1: 잔여 테스트 확인**

```bash
ls /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/
```
Expected: `test_e2e_toggle_render.py`, `test_migrate_to_per_pdf.py`, `test_ocr_fallback.py`, `test_parse_pdf.py`, `samples/`.

- [ ] **Step 2: conftest 동일 패턴 생성**

Create `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/conftest.py`:

```python
"""pytest 공통 설정: scripts 디렉터리 + common/scripts 디렉터리 주입."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
COMMON_DIR = SCRIPTS_DIR.parent.parent / "common" / "scripts"

for d in (SCRIPTS_DIR, COMMON_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
```

- [ ] **Step 3: 실행**

```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests && \
python3 -m pytest -v 2>&1 | tail -30
```

Expected: 모든 테스트 PASS.

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/tests/conftest.py \
        skills/pdf-spec-organizer/scripts/tests/conftest.py && \
git commit -m "test(common,pdf): conftest.py 로 테스트 import 경로 해결"
```

---

## Commit 6: `SKILL.md` 의 scripts 경로 참조 갱신

### Task 6.1: `pdf-spec-organizer/SKILL.md` 내 scripts 경로 현대화

**Files:**
- Modify: `skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: 기존 경로 언급 위치 파악**

Run:
```bash
grep -n "scripts/\(feature_id\|pdf_hash\|pii_scan\|note_extractor\|note_merger\|page_publisher\|draft_registry\|enrich_features\)" \
  /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md | head -30
```

출력 라인 번호 모두가 수정 대상.

- [ ] **Step 2: 각 언급을 Edit 로 교체**

경로 변환 규칙:
- `skills/pdf-spec-organizer/scripts/feature_id.py` → `skills/common/scripts/feature_id.py`
- `skills/pdf-spec-organizer/scripts/pdf_hash.py` → `skills/common/scripts/pdf_hash.py`
- `skills/pdf-spec-organizer/scripts/pii_scan.py` → `skills/common/scripts/pii_scan.py`
- `skills/pdf-spec-organizer/scripts/note_extractor.py` → `skills/common/scripts/note_extractor.py`
- `skills/pdf-spec-organizer/scripts/note_merger.py` → `skills/common/scripts/note_merger.py`
- `skills/pdf-spec-organizer/scripts/page_publisher.py` → `skills/common/scripts/page_publisher.py`
- `skills/pdf-spec-organizer/scripts/draft_registry.py` → `skills/common/scripts/draft_registry.py`
- `skills/pdf-spec-organizer/scripts/enrich_features.py` → `skills/common/scripts/enrich_features.py`

**남아있는 경로(PDF 전용)는 그대로**:
- `skills/pdf-spec-organizer/scripts/parse_pdf.py`
- `skills/pdf-spec-organizer/scripts/ocr_fallback.py`
- `skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py`

Edit 도구로 각 경로를 일괄 `replace_all: true` 로 교체 가능.

- [ ] **Step 3: 검증**

```bash
grep -c "skills/pdf-spec-organizer/scripts/\(feature_id\|pdf_hash\|pii_scan\|note_extractor\|note_merger\|page_publisher\|draft_registry\|enrich_features\)" \
  /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: **0** (common 으로 모두 이동됨).

```bash
grep -c "skills/common/scripts/" /Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md
```
Expected: **>0** (최소 8개 이상 신규 참조).

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/pdf-spec-organizer/SKILL.md && \
git commit -m "docs(skill): scripts 경로 참조를 common/scripts/ 로 갱신"
```

---

## Commit 7: CHANGELOG 엔트리 + 최종 smoke test

### Task 7.1: CHANGELOG 업데이트

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: `[Unreleased]` 섹션 확인**

Run:
```bash
grep -n "^## \[Unreleased\]\|^## \[0\." /Users/chuchu/testPlugin/CHANGELOG.md | head -5
```

- [ ] **Step 2: Unreleased 아래에 Refactor 엔트리 추가**

Edit 도구로 `## [Unreleased]` 섹션 아래에 다음 추가:

```markdown
### Changed (Internal — v1.0 준비)
- 재사용 Python 모듈 8개를 `skills/common/scripts/` 로 이동 (히스토리 보존된 `git mv`)
- `skills/pdf-spec-organizer/scripts/` 에 `_path_setup.py` 신설해 `common/scripts/` 참조
- 각 스킬의 테스트 디렉터리에 `conftest.py` 추가로 import 경로 자동화
- 외부 API/동작 변경 없음 (기존 사용자 영향 없음)
```

- [ ] **Step 3: 검증**

```bash
grep -A 5 "Changed (Internal — v1.0 준비)" /Users/chuchu/testPlugin/CHANGELOG.md
```
Expected: 4줄 모두 출력.

---

### Task 7.2: 최종 smoke test

- [ ] **Step 1: 전체 테스트 재실행**

```bash
cd /Users/chuchu/testPlugin && \
python3 -m pytest skills/common/scripts/tests/ skills/pdf-spec-organizer/scripts/tests/ -v 2>&1 | tail -40
```

Expected: **모든 테스트 PASS**, 실패 0. 이전 13개 테스트 + 새 conftest 로 인한 변동 없음.

- [ ] **Step 2: import 회귀 확인**

```bash
cd /Users/chuchu/testPlugin && \
python3 -c "
import sys
sys.path.insert(0, 'skills/pdf-spec-organizer/scripts')
sys.path.insert(0, 'skills/common/scripts')

from parse_pdf import *      # PDF 전용
from pii_scan import *       # common
from feature_id import *     # common
from page_publisher import * # common
print('all imports OK')
"
```
Expected: `all imports OK`.

- [ ] **Step 3: git status 확인 (unstaged 없어야 함)**

```bash
cd /Users/chuchu/testPlugin && git status
```
Expected: "nothing to commit, working tree clean" 또는 `.pytest_cache/` 등 untracked 만.

- [ ] **Step 4: 최종 커밋 (CHANGELOG)**

```bash
cd /Users/chuchu/testPlugin && \
git add CHANGELOG.md && \
git commit -m "docs(changelog): v1.0 준비 — common/scripts/ 분리"
```

- [ ] **Step 5: PR 1 완료 커밋 요약**

```bash
cd /Users/chuchu/testPlugin && \
git log --oneline -8 | head -8
```

Expected: 최소 6개의 PR 1 관련 커밋 (feat → refactor → test → docs 순).

---

## 완료 기준 (PR 1 Definition of Done)

- [ ] `skills/common/scripts/` 에 8개 Python 파일 + `__init__.py` 존재
- [ ] `skills/common/scripts/tests/` 에 8개 test 파일 + `conftest.py` 존재
- [ ] `skills/pdf-spec-organizer/scripts/` 에 `parse_pdf.py`, `ocr_fallback.py`, `migrate_to_per_pdf.py`, `_path_setup.py` 만 존재
- [ ] `pytest` 전체 PASS (기존 13개 + 신규 conftest)
- [ ] `SKILL.md` 의 경로 참조 갱신 완료
- [ ] `git log` 에 히스토리 보존 확인 (`git log --follow skills/common/scripts/feature_id.py`)
- [ ] CHANGELOG `[Unreleased]` 에 엔트리 추가
- [ ] 외부 사용자 체감 동작 변화 없음 (`/spec-from-pdf` 실행 시 오류 없음)

---

## 다음 플랜

→ `docs/superpowers/plans/2026-04-22-02-routing-dispatcher.md` (PR 2: routing.yaml + dispatcher.py)
