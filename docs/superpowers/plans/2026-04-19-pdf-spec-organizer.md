# PDF Spec Organizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `yeoboya-workflow` 플러그인의 첫 기능 `pdf-spec-organizer` 를 구현한다. 복합 PDF 를 파싱해 Notion 피처 DB 페이지로 퍼블리시하고, 명세 누락 체크 + iOS/Android 플랫폼별 개발자 노트를 공유할 수 있게 한다.

**Architecture:** Claude Code 플러그인 + Python 보조 스크립트 하이브리드. 3개 슬래시 커맨드(`/spec-from-pdf`, `/spec-update`, `/spec-resume`)가 얇은 진입점이 되고, 하나의 Skill(`pdf-spec-organizer`)이 5단계 워크플로우(파싱→구조화→누락체크→노트+미리보기→충돌+퍼블리시)를 조율한다. PDF 파싱/OCR/PII 스캔은 Python 스크립트, Notion 접근은 기존 `mcp__claude_ai_Notion__*` MCP 재사용.

**Tech Stack:** Claude Code plugin manifest, Markdown (SKILL.md, commands, references), Python 3 + PyPDF2 + pdf2image + Pillow + pytesseract + PyYAML, pytest, Tesseract (외부 의존성).

**Spec reference:** `docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md`

**Plugin root:** `/Users/chuchu/testPlugin/` (최상위 디렉토리가 플러그인 루트. `.claude-plugin/plugin.json` 이 여기에 위치)

---

## File Structure Overview

| 경로 | 책임 |
|---|---|
| `.claude-plugin/plugin.json` | 매니페스트 (name, description, version, keywords) |
| `commands/spec-from-pdf.md` | 메인 진입점 슬래시 커맨드 |
| `commands/spec-update.md` | 기존 페이지 노트/체크 갱신 커맨드 |
| `commands/spec-resume.md` | 중단된 세션 이어받기 커맨드 |
| `skills/pdf-spec-organizer/SKILL.md` | 5단계 워크플로우 정의 |
| `skills/pdf-spec-organizer/references/notion-schema.md` | Notion 피처 DB 스키마 상세 |
| `skills/pdf-spec-organizer/references/review-format.md` | 터미널/미리보기 포맷 규약 |
| `skills/pdf-spec-organizer/references/conflict-policy.md` | 충돌 처리 정책 (병합 기본) |
| `skills/pdf-spec-organizer/references/source-of-truth.md` | v2 확장 포인트 스케치 |
| `skills/pdf-spec-organizer/scripts/parse_pdf.py` | PDF 텍스트+이미지 추출 |
| `skills/pdf-spec-organizer/scripts/ocr_fallback.py` | Tesseract OCR fallback |
| `skills/pdf-spec-organizer/scripts/pii_scan.py` | 이메일/전화/주민번호 정규식 스캔 |
| `skills/pdf-spec-organizer/scripts/pdf_hash.py` | SHA-256 short hash 계산 |
| `skills/pdf-spec-organizer/scripts/draft_registry.py` | /tmp 초안 TTL 관리 + 동시 실행 감지 |
| `skills/pdf-spec-organizer/scripts/requirements.txt` | Python 의존성 |
| `skills/pdf-spec-organizer/scripts/tests/test_parse_pdf.py` | parse_pdf 단위 테스트 |
| `skills/pdf-spec-organizer/scripts/tests/test_ocr_fallback.py` | ocr_fallback 단위 테스트 |
| `skills/pdf-spec-organizer/scripts/tests/test_pii_scan.py` | pii_scan 단위 테스트 |
| `skills/pdf-spec-organizer/scripts/tests/test_pdf_hash.py` | pdf_hash 단위 테스트 |
| `skills/pdf-spec-organizer/scripts/tests/test_draft_registry.py` | draft_registry 단위 테스트 |
| `skills/pdf-spec-organizer/scripts/tests/samples/minimal.pdf` | 작은 샘플 PDF (텍스트 위주) |
| `skills/pdf-spec-organizer/scripts/tests/samples/image_only.pdf` | OCR 경로 샘플 (이미지 위주) |
| `config/pdf-spec-organizer/checklist.yaml` | 기본 누락 체크 항목 |
| `config/pdf-spec-organizer/notion-schema.yaml` | DB 자동 생성용 스키마 |
| `config/pdf-spec-organizer/default-checklist.json` | checklist.yaml 로드 실패 fallback (하드코딩 기본값) |
| `docs/manual-qa.md` | 수동 QA 체크리스트 |
| `README.md` | 플러그인 소개, 설치, 사용법 |
| `CHANGELOG.md` | 버전 기록 |

> **참고:** `yeoboya-workflow.config.json` (팀 공유 DB ID) 은 **플러그인 레포가 아닌** 플러그인을 사용하는 프로젝트 레포의 루트에 커밋됩니다. 이 플랜에서는 README 에 가이드만 문서화합니다.

---

## Phase 0: 플러그인 뼈대

### Task 1: 플러그인 매니페스트 작성

**Files:**
- Create: `/Users/chuchu/testPlugin/.claude-plugin/plugin.json`

- [ ] **Step 1: 디렉토리 생성 및 파일 작성**

```bash
mkdir -p /Users/chuchu/testPlugin/.claude-plugin
```

파일 내용:

```json
{
  "name": "yeoboya-workflow",
  "description": "여보야 회사 워크플로우 자동화. PDF 스펙 → Notion 퍼블리시 + 누락 체크 + 플랫폼별 개발자 노트 공유.",
  "version": "0.1.0",
  "author": { "name": "여보야 팀" },
  "keywords": ["workflow", "pdf", "notion", "spec", "ios", "android"]
}
```

- [ ] **Step 2: JSON 유효성 검증**

Run: `python3 -c "import json; json.load(open('/Users/chuchu/testPlugin/.claude-plugin/plugin.json'))"`
Expected: 출력 없이 종료 (exit code 0)

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && git init 2>/dev/null; git add .claude-plugin/plugin.json && git commit -m "chore: initialize yeoboya-workflow plugin manifest"
```

---

### Task 2: README 및 CHANGELOG 스켈레톤

**Files:**
- Create: `/Users/chuchu/testPlugin/README.md`
- Create: `/Users/chuchu/testPlugin/CHANGELOG.md`

- [ ] **Step 1: README.md 작성**

```markdown
# yeoboya-workflow

여보야 회사 워크플로우 자동화 Claude Code 플러그인.

## 기능

### pdf-spec-organizer (v0.1)

복합 PDF 스펙(PRD + 디자인 + 플로우)을 Notion 피처 DB 페이지로 정리한다. iOS/Android 팀이 같은 페이지에서 플랫폼별 개발자 노트를 공유한다.

**커맨드:**
- `/spec-from-pdf <path> [--fast]` — PDF → Notion 페이지 생성
- `/spec-update <notion-url>` — 기존 페이지에 노트/체크만 갱신
- `/spec-resume [--resume-latest | <draft-path>]` — 중단된 세션 이어받기

## 설치

플러그인을 사용할 프로젝트 레포에서:

1. Claude Code 설정에 이 플러그인 경로 추가
2. 프로젝트 레포 루트에 팀 공유 설정 파일 커밋:

   ```json
   {
     "pdf_spec_organizer": {
       "notion_database_id": "<feature-db-id>",
       "parent_page_id": "<parent-page-id>"
     }
   }
   ```
   파일명: `yeoboya-workflow.config.json`

3. Python 의존성 설치:

   ```bash
   pip install -r skills/pdf-spec-organizer/scripts/requirements.txt
   ```

4. Tesseract 설치 (OCR fallback용):

   ```bash
   brew install tesseract tesseract-lang  # macOS
   ```

## 팀 리드 최초 셋업

부모 Notion 페이지 URL 을 준비한 뒤 팀 리드가 최초 셋업을 실행. DB 자동 생성 후 출력되는 `yeoboya-workflow.config.json` 을 프로젝트 레포에 커밋한다.

## 문서

- 설계: [`docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md`](docs/superpowers/specs/2026-04-19-pdf-spec-organizer-design.md)
- 수동 QA: [`docs/manual-qa.md`](docs/manual-qa.md)
```

- [ ] **Step 2: CHANGELOG.md 작성**

```markdown
# Changelog

모든 주목할 만한 변경 사항을 이 파일에 기록합니다.

## [Unreleased]

### Added
- `pdf-spec-organizer` 기능 초기 구현
  - `/spec-from-pdf`, `/spec-update`, `/spec-resume` 커맨드
  - PDF 파싱 + OCR fallback + PII 스캔
  - Notion 피처 DB 자동 생성 및 페이지 퍼블리시
  - 플랫폼별 개발자 노트 섹션 (iOS / Android / 공통)
  - 병합 기본 충돌 처리, 동시 실행 감지

### Planned (v0.2)
- Source-of-truth 인터페이스 (기존 스펙/코드베이스 충돌 체크)
- `checklist.yaml` severity / 조건부 필드
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add README.md CHANGELOG.md && git commit -m "docs: add README and CHANGELOG skeletons"
```

---

## Phase 1: Python 스크립트 (TDD)

### Task 3: Python 의존성 선언

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/requirements.txt`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/samples
```

- [ ] **Step 2: requirements.txt 작성**

```
PyPDF2==3.0.1
pdf2image==1.17.0
Pillow==10.3.0
pytesseract==0.3.10
PyYAML==6.0.1
pytest==8.2.0
```

- [ ] **Step 3: 로컬 venv 설치 검증**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -c "import PyPDF2, pdf2image, PIL, pytesseract, yaml, pytest; print('OK')"
```
Expected: `OK` 출력

- [ ] **Step 4: .gitignore 작성 (venv 제외)**

Create `/Users/chuchu/testPlugin/.gitignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
/tmp/
*.DS_Store
```

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add .gitignore skills/pdf-spec-organizer/scripts/requirements.txt && git commit -m "chore: declare python dependencies for pdf-spec-organizer scripts"
```

---

### Task 4: 샘플 PDF 준비

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/samples/minimal.pdf` (텍스트 위주)
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/samples/image_only.pdf` (이미지 위주)

- [ ] **Step 1: 텍스트 위주 샘플 생성**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts
source .venv/bin/activate
python3 -c "
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfWriter, PdfReader
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

c = canvas.Canvas('tests/samples/minimal.pdf', pagesize=A4)
c.drawString(100, 800, 'Feature: Notification Settings')
c.drawString(100, 780, 'Platform: iOS and Android')
c.drawString(100, 760, 'User can toggle push notifications.')
c.drawString(100, 740, 'Contact: admin@example.com')
c.showPage()
c.save()
print('minimal.pdf created')
"
```

reportlab 이 없으면 먼저 설치: `pip install reportlab==4.1.0` (그리고 requirements.txt 에 추가).

Expected: `minimal.pdf created`

- [ ] **Step 2: 이미지 위주 샘플 생성**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts
source .venv/bin/activate
python3 -c "
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

img = Image.new('RGB', (400, 200), 'white')
d = ImageDraw.Draw(img)
d.text((20, 80), 'SCREEN: Settings Screen Wireframe', fill='black')
img.save('tests/samples/screen.png')

c = canvas.Canvas('tests/samples/image_only.pdf', pagesize=A4)
c.drawImage(ImageReader('tests/samples/screen.png'), 100, 500, 400, 200)
c.showPage()
c.save()
print('image_only.pdf created')
"
```

Expected: `image_only.pdf created`

- [ ] **Step 3: requirements.txt 에 reportlab 추가 (샘플 생성용이라 dev 의존)**

Edit `requirements.txt` 마지막 줄에 추가: `reportlab==4.1.0`

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/tests/samples/ skills/pdf-spec-organizer/scripts/requirements.txt && git commit -m "test: add sample pdfs for parse_pdf tests"
```

---

### Task 5: `pdf_hash.py` TDD

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_pdf_hash.py`
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/pdf_hash.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_pdf_hash.py
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
SAMPLE = SCRIPTS_DIR / "tests" / "samples" / "minimal.pdf"


def test_pdf_hash_returns_12_char_hex():
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(SAMPLE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    hash_value = result.stdout.strip()
    assert len(hash_value) == 12
    assert all(c in "0123456789abcdef" for c in hash_value)


def test_pdf_hash_deterministic():
    r1 = subprocess.run([sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(SAMPLE)], capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(SAMPLE)], capture_output=True, text=True)
    assert r1.stdout == r2.stdout


def test_pdf_hash_missing_file_exits_nonzero(tmp_path):
    missing = tmp_path / "does_not_exist.pdf"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pdf_hash.py"), str(missing)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "not found" in result.stderr.lower() or "no such" in result.stderr.lower()
```

- [ ] **Step 2: 실패 확인**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts
source .venv/bin/activate
pytest tests/test_pdf_hash.py -v
```
Expected: FAIL (pdf_hash.py 없음)

- [ ] **Step 3: 최소 구현**

```python
# pdf_hash.py
"""Compute short SHA-256 hash (first 12 hex chars) of a PDF file."""
import hashlib
import sys
from pathlib import Path


def short_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: pdf_hash.py <pdf-path>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    print(short_hash(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_pdf_hash.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/pdf_hash.py skills/pdf-spec-organizer/scripts/tests/test_pdf_hash.py && git commit -m "feat: add pdf_hash.py with short sha256"
```

---

### Task 6: `parse_pdf.py` TDD — 텍스트 추출

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_parse_pdf.py`
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/parse_pdf.py`

- [ ] **Step 1: 실패 테스트 작성 (텍스트 추출)**

```python
# tests/test_parse_pdf.py
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
MINIMAL = SCRIPTS_DIR / "tests" / "samples" / "minimal.pdf"
IMAGE_ONLY = SCRIPTS_DIR / "tests" / "samples" / "image_only.pdf"


def run_parse(pdf_path: Path, out_dir: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "parse_pdf.py"), str(pdf_path), "--out-dir", str(out_dir)],
        capture_output=True,
        text=True,
    )


def test_parse_pdf_outputs_json_with_pages(tmp_path):
    result = run_parse(MINIMAL, tmp_path)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "pages" in data
    assert isinstance(data["pages"], list)
    assert len(data["pages"]) >= 1
    page = data["pages"][0]
    assert set(page.keys()) >= {"page_num", "text", "has_text"}
    assert "Notification" in page["text"] or "notification" in page["text"].lower()
    assert page["has_text"] is True


def test_parse_pdf_image_only_pdf_has_text_false(tmp_path):
    result = run_parse(IMAGE_ONLY, tmp_path)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    # image-only pdf should either produce empty text or has_text=False
    if data["pages"]:
        assert not data["pages"][0]["text"].strip() or data["pages"][0]["has_text"] is False


def test_parse_pdf_missing_file_exits_nonzero(tmp_path):
    missing = tmp_path / "missing.pdf"
    result = run_parse(missing, tmp_path)
    assert result.returncode != 0
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_parse_pdf.py -v`
Expected: FAIL (parse_pdf.py 없음)

- [ ] **Step 3: 구현 (텍스트만)**

```python
# parse_pdf.py
"""Extract text and image references from a PDF.

Usage: parse_pdf.py <pdf-path> --out-dir <dir>

Output (stdout): JSON
{
  "pages": [
    {"page_num": 1, "text": "...", "has_text": true}
  ],
  "images": [
    {"page_num": 1, "idx": 0, "path": "/tmp/.../page_1_img_0.png"}
  ],
  "meta": {"total_pages": N, "encrypted": false}
}

Exit codes:
  0: success
  1: file not found or corrupt
  2: usage error
  3: pdf encrypted (no password support in v1)
"""
import argparse
import json
import sys
from pathlib import Path

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError, DependencyError

TEXT_MIN_CHARS = 10  # 페이지에 텍스트가 있다고 볼 최소 글자 수


def extract_pages(reader: PdfReader) -> list[dict]:
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append({
            "page_num": i,
            "text": text,
            "has_text": len(text.strip()) >= TEXT_MIN_CHARS,
        })
    return pages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.pdf_path.is_file():
        print(f"file not found: {args.pdf_path}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(args.pdf_path))
    except PdfReadError as exc:
        print(f"failed to read pdf: {exc}", file=sys.stderr)
        return 1
    except DependencyError as exc:
        print(f"missing dependency: {exc}", file=sys.stderr)
        return 1

    if reader.is_encrypted:
        print("pdf is encrypted", file=sys.stderr)
        return 3

    pages = extract_pages(reader)
    output = {
        "pages": pages,
        "images": [],
        "meta": {"total_pages": len(pages), "encrypted": False},
    }
    json.dump(output, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_parse_pdf.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/parse_pdf.py skills/pdf-spec-organizer/scripts/tests/test_parse_pdf.py && git commit -m "feat: add parse_pdf.py with text extraction"
```

---

### Task 7: `parse_pdf.py` — 이미지 추출 확장

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/parse_pdf.py`
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_parse_pdf.py`

- [ ] **Step 1: 실패 테스트 추가**

`test_parse_pdf.py` 에 추가:

```python
def test_parse_pdf_extracts_images_for_image_only_pdf(tmp_path):
    result = run_parse(IMAGE_ONLY, tmp_path)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "images" in data
    assert len(data["images"]) >= 1
    img = data["images"][0]
    assert set(img.keys()) >= {"page_num", "idx", "path"}
    assert Path(img["path"]).is_file()
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_parse_pdf.py::test_parse_pdf_extracts_images_for_image_only_pdf -v`
Expected: FAIL (images 가 빈 리스트)

- [ ] **Step 3: 이미지 추출 구현 (pdf2image 로 페이지 자체를 렌더)**

`parse_pdf.py` 의 `main()` 에서 `extract_pages()` 다음에 추가:

```python
from pdf2image import convert_from_path

def extract_page_images(pdf_path: Path, out_dir: Path, pages_info: list[dict]) -> list[dict]:
    """Render each page (or text-missing page) as PNG and return references.

    Strategy: pdf2image renders each page to an image. We save one image per page
    for pages where text is missing OR always (to attach visual context in Notion).
    For v1 we save images for EVERY page to keep downstream simple.
    """
    images = []
    try:
        pil_images = convert_from_path(str(pdf_path), dpi=150)
    except Exception as exc:
        print(f"warning: image rendering failed: {exc}", file=sys.stderr)
        return images
    for i, pil_img in enumerate(pil_images, start=1):
        img_path = out_dir / f"page_{i}_img_0.png"
        pil_img.save(img_path, "PNG")
        images.append({"page_num": i, "idx": 0, "path": str(img_path)})
    return images
```

그리고 `main()` 안의 `output` 구성 부분을 교체:

```python
    pages = extract_pages(reader)
    images = extract_page_images(args.pdf_path, args.out_dir, pages)
    output = {
        "pages": pages,
        "images": images,
        "meta": {"total_pages": len(pages), "encrypted": False},
    }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_parse_pdf.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/parse_pdf.py skills/pdf-spec-organizer/scripts/tests/test_parse_pdf.py && git commit -m "feat: extract page images via pdf2image in parse_pdf"
```

---

### Task 8: `ocr_fallback.py` TDD

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_ocr_fallback.py`
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/ocr_fallback.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_ocr_fallback.py
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent
IMAGE_ONLY = SCRIPTS_DIR / "tests" / "samples" / "image_only.pdf"


pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None,
    reason="tesseract not installed; OCR fallback tests skipped",
)


def test_ocr_fallback_produces_text(tmp_path):
    # parse_pdf 먼저 돌려서 이미지 생성
    parse_out = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "parse_pdf.py"), str(IMAGE_ONLY), "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert parse_out.returncode == 0
    parse_data = json.loads(parse_out.stdout)
    image_paths = [img["path"] for img in parse_data["images"]]

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ocr_fallback.py"), "--images", *image_paths],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "pages" in data
    assert len(data["pages"]) == len(image_paths)
    page = data["pages"][0]
    assert set(page.keys()) >= {"page_num", "ocr_text"}
    # 샘플 PDF 의 이미지 안에 "SCREEN" 또는 "Settings" 가 있음 → OCR 으로 최소 일부 추출되어야
    all_text = " ".join(p["ocr_text"] for p in data["pages"]).lower()
    assert "screen" in all_text or "settings" in all_text


def test_ocr_fallback_no_tesseract_gives_clear_error(tmp_path, monkeypatch):
    # PATH 에서 tesseract 제거해 에러 케이스 시뮬레이션
    monkeypatch.setenv("PATH", "/nonexistent")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ocr_fallback.py"), "--images", str(tmp_path / "dummy.png")],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "tesseract" in result.stderr.lower()
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_ocr_fallback.py -v`
Expected: 모두 FAIL (파일 없음) 또는 tesseract 미설치 시 skipped

- [ ] **Step 3: 구현**

```python
# ocr_fallback.py
"""Run Tesseract OCR on a list of images.

Usage: ocr_fallback.py --images <img1> <img2> ...

Output (stdout): JSON
{ "pages": [{"page_num": N, "ocr_text": "...", "source_image": "path"}] }

Exit codes:
  0: success
  1: tesseract not found or OCR failed
  2: usage error
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import pytesseract
from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", nargs="+", required=True, type=Path)
    parser.add_argument("--lang", default="eng+kor", help="Tesseract languages")
    args = parser.parse_args()

    if shutil.which("tesseract") is None:
        print(
            "tesseract not found. Install: 'brew install tesseract tesseract-lang' (macOS)",
            file=sys.stderr,
        )
        return 1

    pages = []
    for page_num, img_path in enumerate(args.images, start=1):
        if not img_path.is_file():
            print(f"warning: image not found: {img_path}", file=sys.stderr)
            pages.append({"page_num": page_num, "ocr_text": "", "source_image": str(img_path)})
            continue
        try:
            text = pytesseract.image_to_string(Image.open(img_path), lang=args.lang)
        except pytesseract.TesseractError as exc:
            print(f"ocr failed for {img_path}: {exc}", file=sys.stderr)
            return 1
        pages.append({"page_num": page_num, "ocr_text": text.strip(), "source_image": str(img_path)})

    json.dump({"pages": pages}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_ocr_fallback.py -v`
Expected: tesseract 설치 돼 있으면 2 passed, 아니면 skipped

참고: Tesseract 없으면 아래 명령으로 설치 후 재실행:
```bash
brew install tesseract tesseract-lang
```

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/ocr_fallback.py skills/pdf-spec-organizer/scripts/tests/test_ocr_fallback.py && git commit -m "feat: add ocr_fallback.py using pytesseract"
```

---

### Task 9: `pii_scan.py` TDD

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_pii_scan.py`
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/pii_scan.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_pii_scan.py
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_pii(text: str):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "pii_scan.py")],
        input=text,
        capture_output=True,
        text=True,
    )


def test_detects_email():
    r = run_pii("contact: user.name+tag@example.com for details")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    categories = {f["category"] for f in data["findings"]}
    assert "email" in categories


def test_detects_kr_phone():
    r = run_pii("전화: 010-1234-5678")
    data = json.loads(r.stdout)
    categories = {f["category"] for f in data["findings"]}
    assert "phone" in categories


def test_detects_kr_rrn():
    # 주민등록번호 예시 (형식만)
    r = run_pii("주민번호: 900101-1234567")
    data = json.loads(r.stdout)
    categories = {f["category"] for f in data["findings"]}
    assert "rrn" in categories


def test_clean_text_returns_empty_findings():
    r = run_pii("This is a normal feature spec with no personal info.")
    data = json.loads(r.stdout)
    assert data["findings"] == []


def test_masks_sample_in_output():
    """Reported samples should be partially masked to avoid logging PII verbatim."""
    r = run_pii("contact: verylongemail.address@example.com")
    data = json.loads(r.stdout)
    sample = data["findings"][0]["sample"]
    assert "*" in sample or "..." in sample
    # 원본이 그대로 들어가면 안 됨
    assert "verylongemail.address@example.com" != sample
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_pii_scan.py -v`
Expected: FAIL (pii_scan.py 없음)

- [ ] **Step 3: 구현**

```python
# pii_scan.py
"""Scan text for PII patterns (email, KR phone, KR resident registration number).

Input: text on stdin.
Output (stdout): JSON
{ "findings": [{"category": "email"|"phone"|"rrn", "sample": "...(masked)", "line": N}] }

This is a WARNING tool — never blocks the workflow. It helps developers catch
PII in PDFs before publishing to Notion.
"""
import json
import re
import sys

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
KR_PHONE_RE = re.compile(r"\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b")
KR_RRN_RE = re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b")

PATTERNS = [
    ("email", EMAIL_RE),
    ("phone", KR_PHONE_RE),
    ("rrn", KR_RRN_RE),
]


def mask(value: str, category: str) -> str:
    if category == "email":
        local, _, domain = value.partition("@")
        if len(local) <= 2:
            return f"*@{domain}"
        return f"{local[0]}***{local[-1]}@{domain}"
    if category == "phone":
        return f"{value[:3]}-****-{value[-4:]}"
    if category == "rrn":
        return f"{value[:6]}-*******"
    return "***"


def scan(text: str) -> list[dict]:
    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for category, pattern in PATTERNS:
            for match in pattern.finditer(line):
                findings.append({
                    "category": category,
                    "sample": mask(match.group(0), category),
                    "line": line_no,
                })
    return findings


def main() -> int:
    text = sys.stdin.read()
    findings = scan(text)
    json.dump({"findings": findings}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_pii_scan.py -v`
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/pii_scan.py skills/pdf-spec-organizer/scripts/tests/test_pii_scan.py && git commit -m "feat: add pii_scan.py for email/phone/rrn detection"
```

---

### Task 10: `draft_registry.py` TDD — TTL + 동시 실행 감지

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/test_draft_registry.py`
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/draft_registry.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_draft_registry.py
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_reg(*args, registry_path):
    env_args = ["--registry", str(registry_path)]
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "draft_registry.py"), *args, *env_args],
        capture_output=True,
        text=True,
    )


def test_record_and_query_recent(tmp_path):
    reg = tmp_path / "registry.json"
    r = run_reg("record", "--hash", "abc123", "--draft-path", str(tmp_path / "d.md"), "--status", "running", registry_path=reg)
    assert r.returncode == 0, r.stderr

    r2 = run_reg("query-recent", "--hash", "abc123", "--within-seconds", "300", registry_path=reg)
    assert r2.returncode == 0
    data = json.loads(r2.stdout)
    assert data["found"] is True
    assert data["entry"]["hash"] == "abc123"


def test_query_recent_expired(tmp_path):
    reg = tmp_path / "registry.json"
    # record 후 8초 기다리지 말고, within-seconds=1 으로 강제
    run_reg("record", "--hash", "xyz", "--draft-path", "/tmp/x.md", "--status", "running", registry_path=reg)
    time.sleep(2)
    r = run_reg("query-recent", "--hash", "xyz", "--within-seconds", "1", registry_path=reg)
    data = json.loads(r.stdout)
    assert data["found"] is False


def test_list_latest(tmp_path):
    reg = tmp_path / "registry.json"
    run_reg("record", "--hash", "h1", "--draft-path", "/tmp/1.md", "--status", "failed", registry_path=reg)
    time.sleep(0.1)
    run_reg("record", "--hash", "h2", "--draft-path", "/tmp/2.md", "--status", "running", registry_path=reg)
    r = run_reg("list-latest", "--count", "5", registry_path=reg)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert len(data["entries"]) == 2
    assert data["entries"][0]["hash"] == "h2"  # 최신 순


def test_gc_removes_expired(tmp_path):
    reg = tmp_path / "registry.json"
    # success 는 3일, failed 는 7일 TTL. ttl_override 로 빠르게 테스트
    run_reg("record", "--hash", "old", "--draft-path", "/tmp/old.md", "--status", "success", "--ttl-seconds", "1", registry_path=reg)
    time.sleep(2)
    r = run_reg("gc", registry_path=reg)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["removed"] >= 1

    r2 = run_reg("list-latest", "--count", "5", registry_path=reg)
    assert json.loads(r2.stdout)["entries"] == []
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_draft_registry.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# draft_registry.py
"""Manage /tmp draft registry for concurrent-run detection and TTL cleanup.

Registry file format (JSON):
{
  "entries": [
    {
      "hash": "abc123",
      "draft_path": "/tmp/spec-draft-abc123-1700000000.md",
      "status": "running" | "success" | "failed",
      "created_at": 1700000000.0,
      "ttl_seconds": 604800
    }
  ]
}

Subcommands:
  record      --hash H --draft-path P --status S [--ttl-seconds N]
  query-recent --hash H --within-seconds N
  list-latest --count N
  gc
  update-status --draft-path P --status S
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path


def default_registry() -> Path:
    plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if plugin_data:
        return Path(plugin_data) / "draft-registry.json"
    return Path.home() / ".claude-plugin-data" / "yeoboya-workflow" / "draft-registry.json"


def load(reg: Path) -> dict:
    if not reg.is_file():
        return {"entries": []}
    try:
        return json.loads(reg.read_text())
    except json.JSONDecodeError:
        return {"entries": []}


def save(reg: Path, data: dict) -> None:
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps(data, indent=2))


def ttl_for(status: str) -> int:
    return {"success": 3 * 86400, "failed": 7 * 86400, "running": 7 * 86400}.get(status, 7 * 86400)


def cmd_record(args) -> int:
    data = load(args.registry)
    ttl = args.ttl_seconds if args.ttl_seconds is not None else ttl_for(args.status)
    entry = {
        "hash": args.hash,
        "draft_path": args.draft_path,
        "status": args.status,
        "created_at": time.time(),
        "ttl_seconds": ttl,
    }
    data["entries"].append(entry)
    save(args.registry, data)
    json.dump({"recorded": True, "entry": entry}, sys.stdout)
    return 0


def cmd_query_recent(args) -> int:
    data = load(args.registry)
    now = time.time()
    matches = [
        e for e in data["entries"]
        if e["hash"] == args.hash and (now - e["created_at"]) <= args.within_seconds
    ]
    found = bool(matches)
    out = {"found": found}
    if found:
        out["entry"] = sorted(matches, key=lambda e: e["created_at"], reverse=True)[0]
    json.dump(out, sys.stdout)
    return 0


def cmd_list_latest(args) -> int:
    data = load(args.registry)
    entries = sorted(data["entries"], key=lambda e: e["created_at"], reverse=True)[: args.count]
    json.dump({"entries": entries}, sys.stdout)
    return 0


def cmd_gc(args) -> int:
    data = load(args.registry)
    now = time.time()
    fresh = [e for e in data["entries"] if (now - e["created_at"]) <= e["ttl_seconds"]]
    removed = len(data["entries"]) - len(fresh)
    for e in data["entries"]:
        if e not in fresh:
            p = Path(e["draft_path"])
            if p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass
    data["entries"] = fresh
    save(args.registry, data)
    json.dump({"removed": removed}, sys.stdout)
    return 0


def cmd_update_status(args) -> int:
    data = load(args.registry)
    updated = 0
    for e in data["entries"]:
        if e["draft_path"] == args.draft_path:
            e["status"] = args.status
            e["ttl_seconds"] = ttl_for(args.status)
            updated += 1
    save(args.registry, data)
    json.dump({"updated": updated}, sys.stdout)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=default_registry())
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--hash", required=True)
    p_rec.add_argument("--draft-path", required=True)
    p_rec.add_argument("--status", required=True, choices=["running", "success", "failed"])
    p_rec.add_argument("--ttl-seconds", type=int, default=None)
    p_rec.set_defaults(func=cmd_record)

    p_q = sub.add_parser("query-recent")
    p_q.add_argument("--hash", required=True)
    p_q.add_argument("--within-seconds", type=int, required=True)
    p_q.set_defaults(func=cmd_query_recent)

    p_l = sub.add_parser("list-latest")
    p_l.add_argument("--count", type=int, default=5)
    p_l.set_defaults(func=cmd_list_latest)

    p_g = sub.add_parser("gc")
    p_g.set_defaults(func=cmd_gc)

    p_u = sub.add_parser("update-status")
    p_u.add_argument("--draft-path", required=True)
    p_u.add_argument("--status", required=True, choices=["running", "success", "failed"])
    p_u.set_defaults(func=cmd_update_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_draft_registry.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/scripts/draft_registry.py skills/pdf-spec-organizer/scripts/tests/test_draft_registry.py && git commit -m "feat: add draft_registry.py with ttl and concurrent-run detection"
```

---

## Phase 2: 설정 파일

### Task 11: `checklist.yaml` + fallback

**Files:**
- Create: `/Users/chuchu/testPlugin/config/pdf-spec-organizer/checklist.yaml`
- Create: `/Users/chuchu/testPlugin/config/pdf-spec-organizer/default-checklist.json`

- [ ] **Step 1: `checklist.yaml` 작성**

```bash
mkdir -p /Users/chuchu/testPlugin/config/pdf-spec-organizer
```

```yaml
version: 1

items:
  - id: error_cases
    name: 에러 케이스
    description: 네트워크/서버 오류 발생 시 UX
    applies_to: [iOS, Android, 공통]

  - id: empty_state
    name: 빈 상태
    description: 데이터 없거나 초기 진입 시 화면
    applies_to: [iOS, Android, 공통]

  - id: offline
    name: 오프라인 처리
    description: 네트워크 끊김 시 동작 (캐시 / 재시도)
    applies_to: [iOS, Android, 공통]

  - id: permissions
    name: 권한
    description: 카메라/위치/알림/사진 권한 요청 및 거부 플로우
    applies_to: [iOS, Android]

  - id: loading
    name: 로딩 상태
    description: 비동기 작업 인디케이터 / 스켈레톤
    applies_to: [iOS, Android, 공통]

  - id: a11y
    name: 접근성
    description: 스크린리더, 컬러 대비, 터치 타겟 크기
    applies_to: [iOS, Android, 공통]
```

- [ ] **Step 2: `default-checklist.json` 작성 (YAML 파싱 실패 시 fallback)**

```json
{
  "version": 1,
  "items": [
    {"id": "error_cases", "name": "에러 케이스", "description": "네트워크/서버 오류 발생 시 UX", "applies_to": ["iOS", "Android", "공통"]},
    {"id": "empty_state", "name": "빈 상태", "description": "데이터 없거나 초기 진입 시 화면", "applies_to": ["iOS", "Android", "공통"]},
    {"id": "offline", "name": "오프라인 처리", "description": "네트워크 끊김 시 동작 (캐시 / 재시도)", "applies_to": ["iOS", "Android", "공통"]},
    {"id": "permissions", "name": "권한", "description": "카메라/위치/알림/사진 권한 요청 및 거부 플로우", "applies_to": ["iOS", "Android"]},
    {"id": "loading", "name": "로딩 상태", "description": "비동기 작업 인디케이터 / 스켈레톤", "applies_to": ["iOS", "Android", "공통"]},
    {"id": "a11y", "name": "접근성", "description": "스크린리더, 컬러 대비, 터치 타겟 크기", "applies_to": ["iOS", "Android", "공통"]}
  ]
}
```

- [ ] **Step 3: JSON/YAML 유효성 검증**

Run:
```bash
cd /Users/chuchu/testPlugin && python3 -c "import yaml, json; yaml.safe_load(open('config/pdf-spec-organizer/checklist.yaml')); json.load(open('config/pdf-spec-organizer/default-checklist.json')); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add config/pdf-spec-organizer/checklist.yaml config/pdf-spec-organizer/default-checklist.json && git commit -m "feat: add checklist.yaml and fallback default-checklist.json"
```

---

### Task 12: `notion-schema.yaml`

**Files:**
- Create: `/Users/chuchu/testPlugin/config/pdf-spec-organizer/notion-schema.yaml`

- [ ] **Step 1: 작성**

```yaml
# Notion 피처 DB 자동 생성 시 사용하는 스키마 정의.
# Skill 의 최초 셋업 단계에서 이 정의를 참고해 Notion API 로 DB 를 만든다.

database:
  title: "여보야 피처 스펙"
  description: "PDF 스펙에서 정리된 피처 페이지. iOS/Android 개발자가 같은 페이지에서 노트를 공유한다."

properties:
  이름:
    type: title
  플랫폼:
    type: multi_select
    options: [iOS, Android, 공통]
  상태:
    type: select
    options: [Draft, In Review, Ready, In Dev, Done]
  원본_PDF:
    type: rich_text
    note: "파일명만 저장. 전체 경로는 저장하지 않음."
  PDF_해시:
    type: rich_text
    note: "SHA-256 앞 12자. 동시 실행 감지/버전 매칭용."
  소스_링크:
    type: url
    note: "PRD/Jira/Figma 등 외부 링크. 다건은 본문 링크 블록에 추가."
  이전_버전:
    type: relation
    target: self
  관련_피처:
    type: relation
    target: self
  생성자:
    type: people
  생성일:
    type: created_time
  누락_항목:
    type: multi_select
    options: [error_cases, empty_state, offline, permissions, loading, a11y]
    note: "checklist.yaml 의 id 값. 설정 변경 시 options 도 갱신 필요."

body_sections:
  - 개요
  - 화면 / 플로우
  - 요구사항
  - 누락 체크
  - 개발자 노트 (iOS / Android / 공통)
  - 메타
```

- [ ] **Step 2: YAML 유효성 검증**

Run: `cd /Users/chuchu/testPlugin && python3 -c "import yaml; yaml.safe_load(open('config/pdf-spec-organizer/notion-schema.yaml')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add config/pdf-spec-organizer/notion-schema.yaml && git commit -m "feat: add notion-schema.yaml for feature DB auto-creation"
```

---

## Phase 3: 레퍼런스 문서

### Task 13: `references/notion-schema.md`

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/notion-schema.md`

- [ ] **Step 1: 디렉토리 생성 및 작성**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/pdf-spec-organizer/references
```

```markdown
# Notion 피처 DB 스키마 상세

이 문서는 SKILL.md 에서 참조하는 Notion DB 스키마 상세 정의이다.
실제 DB 자동 생성 시 사용하는 프로그램적 스키마는 `config/pdf-spec-organizer/notion-schema.yaml` 이다.

## DB 속성

| 속성 | 타입 | Notion API 타입 | 설명 |
|---|---|---|---|
| 이름 | Title | `title` | 피처명 (예: "알림 설정 화면") |
| 플랫폼 | Multi-select | `multi_select` | `iOS`, `Android`, `공통` |
| 상태 | Select | `select` | `Draft`, `In Review`, `Ready`, `In Dev`, `Done` |
| 원본 PDF | Text | `rich_text` | **파일명만** (홈 경로 노출 방지) |
| PDF 해시 | Text | `rich_text` | SHA-256 앞 12자 |
| 소스 링크 | URL | `url` | 다건은 본문 링크 블록에 추가 |
| 이전 버전 | Relation (self) | `relation` | 새 버전 생성 시 연결 |
| 관련 피처 | Relation (self) | `relation` | v2 source-of-truth 기반 |
| 생성자 | Person | `people` | 플러그인 실행자 |
| 생성일 | Created time | `created_time` | 자동 |
| 누락 항목 | Multi-select | `multi_select` | `checklist.yaml` 의 id |

## 페이지 본문 블록 구조

```
# <피처명>

## 개요
<Claude 추출 1-2문단>

## 화면 / 플로우
<Notion 업로드된 이미지 + 캡션>

## 요구사항
- ...

## 누락 체크
- [ ] 에러 케이스
- [x] 빈 상태 (명시됨)
- [ ] 오프라인 처리
...

## 개발자 노트
### iOS
<Phase 4 입력, 없으면 빈 상태>

### Android
<Phase 4 입력>

### 공통 질문
<양 팀 논의 거리>

## 메타
- 원본 PDF: `<filename>`
- PDF 해시: `<short-hash>`
- 생성자: <user>
- 생성일: <date>
```

## 팀 DB 공유 전략

`yeoboya-workflow.config.json` 을 프로젝트 레포 루트에 커밋:

```json
{
  "pdf_spec_organizer": {
    "notion_database_id": "<feature-db-id>",
    "parent_page_id": "<parent-page-id>"
  }
}
```

- 파일이 없으면 skill 이 "팀 리드가 먼저 셋업하고 커밋하세요" 안내
- 최초 셋업: 부모 Notion 페이지 URL 입력 → DB 자동 생성 → 설정 파일 초안 출력 → 사용자가 커밋

## v2 확장

- 관련 피처 Relation 을 활용한 의존/충돌 추적
- Source-of-truth 인터페이스는 `references/source-of-truth.md` 참조
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/references/notion-schema.md && git commit -m "docs: add notion schema reference"
```

---

### Task 14: `references/review-format.md`

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md`

- [ ] **Step 1: 작성**

```markdown
# 터미널 / 미리보기 포맷 규약

Phase 4 의 미리보기 md 파일과 터미널 출력은 일관된 포맷을 따른다.

## `/tmp/spec-draft-<hash>-<ts>.md` 초안 파일 구조

```markdown
<!-- plugin-state
phase: 4
pdf_hash: <short-hash>
source_file: <filename>
created_at: <iso8601>
-->

# <피처명>

## 개요
<Claude 추출 요약>

## 화면 / 플로우
![page1](<이미지 경로>)
...

## 요구사항
- 요구사항 1
- 요구사항 2

## 누락 체크
- [ ] 에러 케이스 — 네트워크/서버 오류 UX 언급 없음
- [x] 빈 상태 — 명시됨
- [ ] 오프라인 처리 — 언급 없음

## 개발자 노트
### iOS
<!-- 플랫폼 담당자가 채움. 비어있으면 Notion 에도 빈 상태로 저장 -->

### Android
<!-- 플랫폼 담당자가 채움 -->

### 공통 질문
<!-- 양 팀이 함께 논의할 엣지케이스 / 질문 -->

## 메타
- 원본 PDF: <filename>
- PDF 해시: <short-hash>
- 생성자: <user>
- 생성일: <iso8601>
```

### 왜 HTML 주석?

`<!-- plugin-state ... -->` 블록은 Phase 진행 상태 직렬화용. `/spec-resume` 가 이 헤더를 읽어 어느 Phase 부터 이어갈지 결정한다. Notion 퍼블리시 시에는 제거된다.

## 터미널 출력 규약

각 Phase 시작/종료를 간결히 표시:

```
[Phase 1/5] PDF 파싱 중...
[Phase 1/5] 완료 (3 페이지, 2 이미지 추출)

[Phase 2/5] 구조화 중...
[Phase 2/5] 완료

피처 3개 추출됨:
  1. 알림 설정 화면 (iOS, Android)
  2. 푸시 권한 요청 플로우 (iOS, Android)
  3. 빈 상태 UI (공통)

이대로 진행할까요?
  y) 진행
  s) 피처 N번 쪼개기 (예: s 1)
  m) 피처 N,M 합치기 (예: m 1,2)
  r) 피처 N번 리네이밍 (예: r 1)
  e) 에디터에서 수정 (VS Code / $EDITOR)
  c) 취소
>
```

## Phase 별 터미널 프롬프트 예시

Phase 2 완료 후: 위 메뉴
Phase 3 완료 후: 누락 항목 요약 표시
Phase 4 시작: "다음 단계: 개발자 노트 작성 — 에디터를 열까요? (e/n/c)"
Phase 5 시작 (충돌 시):
```
Notion 에 같은 피처가 이미 존재합니다:
  제목: 알림 설정 화면
  최근 생성자: chuchu (2026-04-18 14:23)
  PDF 해시: 같음

어떻게 할까요?
  [1] 병합 (내 플랫폼 섹션만 append) ← 기본
  [2] 덮어쓰기 (기존 노트 손실 가능)
  [3] 새 버전 (이전_버전 Relation 으로 연결)
  [4] 취소
>
```
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/references/review-format.md && git commit -m "docs: add review format reference"
```

---

### Task 15: `references/conflict-policy.md`

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md`

- [ ] **Step 1: 작성**

```markdown
# 충돌 처리 정책

Phase 5 에서 Notion 에 **이미 같은 이름의 피처 페이지**가 존재할 때 적용한다.

## 기본값: 병합 (Merge)

- **현재 실행자의 플랫폼 섹션만 append / replace**
- 다른 플랫폼 섹션, 메타, 누락 체크, 공통 질문은 **보존**
- 충돌 검사 기준: "이름" Title 속성 완전 일치

예:
- 기존 페이지 "알림 설정 화면" 에 iOS 노트가 채워져 있음
- Android 개발자가 `/spec-from-pdf` 재실행 → 동일 이름 피처 감지
- 기본값 병합 선택 → "iOS" 섹션은 그대로, "Android" 섹션만 내 노트로 갱신

## 에스케이프 햇치

- **덮어쓰기**: 파괴적. Notion 페이지 본문을 새로 렌더한 것으로 완전히 교체. 기존 노트 소실.
  - 선택 시 "정말로 덮어쓰시겠습니까? 기존 노트가 삭제됩니다" 추가 확인.
- **새 버전**: 기존 페이지는 그대로 두고, 새 페이지를 생성해 `이전_버전(Relation)` 으로 기존을 가리킴.
  - 제목은 그대로 유지 (중복 허용). 검색 시 Relation 으로 계보 파악.

## 동시 실행 경고

5분 내 **같은 PDF 해시**로 다른 사용자가 실행한 기록이 있으면 "동시 실행 경고" 표시:

```
⚠️  5분 내 동일 PDF 를 다른 실행이 처리 중입니다:
  실행자: chuchu
  시작: 2분 전
  초안 경로: /tmp/spec-draft-<hash>-<ts>.md

덮어쓰기 전에 상대방과 조율하세요. 계속 진행할까요? (y/n)
```

기록 출처: `${CLAUDE_PLUGIN_DATA}/draft-registry.json` — `draft_registry.py query-recent`.

## `--fast` 플래그 동작

- 기본값(병합) 자동 적용. 프롬프트 없음.
- **덮어쓰기 / 새 버전**은 `--fast` 에서도 자동 선택 금지. 파괴적이거나 부작용이 큰 선택은 항상 사용자 확인.
- 따라서 `--fast` 에서 덮어쓰기가 필요한 경우 사용자가 플래그 없이 다시 실행해야 함.
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/references/conflict-policy.md && git commit -m "docs: add conflict policy reference"
```

---

### Task 16: `references/source-of-truth.md` (v2 스케치)

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/source-of-truth.md`

- [ ] **Step 1: 작성**

```markdown
# Source-of-truth 인터페이스 (v2 확장 포인트)

v1 에서는 구현되지 않는다. v2 "기존 스펙과의 충돌 체크" 를 위한 인터페이스 스케치.

## 목적

Phase 2 (구조화) 직후, 추출된 피처가 기존 앱/스펙과 **충돌/중복**되는지 사전 확인.

## 입력

- 추출된 피처 리스트: `[{name, platform, summary}]`
- 기존 source-of-truth 구성:
  ```json
  {
    "notion_feature_db": "<db-id>",
    "codebase_roots": ["/path/to/ios-repo", "/path/to/android-repo"]
  }
  ```
  프로젝트 레포의 `yeoboya-workflow.config.json` 에 선언.

## 출력 (각 피처마다)

```json
{
  "feature_name": "알림 설정 화면",
  "matches": [
    {"kind": "notion_page", "title": "알림 설정", "id": "<page-id>", "similarity": 0.85},
    {"kind": "code_symbol", "path": "ios-repo/NotificationSettings.swift", "line": 42}
  ],
  "recommendation": "관련 피처로 연결 제안 (Relation)"
}
```

## 구현 힌트 (v2 작업자용)

- Notion DB 쿼리: `mcp__claude_ai_Notion__notion-search` 으로 제목/본문 유사도 기반 후보 수집
- 코드베이스: `grep -rn "<피처명의 키워드>" <codebase>` 로 간단한 심볼/파일명 매칭
- 유사도 판정은 Claude 에게 후보 목록 + 피처 설명을 주고 맡긴다 (임베딩/벡터 DB 는 v3 이상)

## v1 에서 이 인터페이스를 어떻게 "열어두는가"

- Phase 2 직후에 "[Phase 2.5] source-of-truth 조회 — v1 비활성" 주석만 SKILL.md 에 남김
- 추출된 피처 리스트를 임시 JSON 으로 덤프하는 코드 경로를 유지 (나중에 v2 가 이 JSON 을 소비)
- Notion 페이지의 `관련_피처` Relation 속성은 v1 에서 비워두지만 **스키마에는 존재**
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/references/source-of-truth.md && git commit -m "docs: add source-of-truth reference (v2 extension sketch)"
```

---

## Phase 4: 메인 Skill 문서

### Task 17: `SKILL.md` — 프론트매터 + 사전 체크

**Files:**
- Create: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: SKILL.md 프론트매터 + "Precondition" 섹션**

```markdown
---
name: pdf-spec-organizer
description: 복합 PDF 스펙(PRD+디자인+플로우)을 파싱해 Notion 피처 DB 페이지로 정리한다. 명세 누락 체크 + iOS/Android 플랫폼별 개발자 노트 공유. /spec-from-pdf, /spec-update, /spec-resume 커맨드의 실제 로직.
allowed-tools: Bash Read Write Edit Grep Glob mcp__claude_ai_Notion__notion-search mcp__claude_ai_Notion__notion-fetch mcp__claude_ai_Notion__notion-create-pages mcp__claude_ai_Notion__notion-create-database mcp__claude_ai_Notion__notion-update-page mcp__claude_ai_Notion__notion-update-data-source
---

# pdf-spec-organizer

복합 PDF 스펙을 Notion 피처 DB 페이지로 정리하는 5단계 워크플로우.

## Precondition 체크 (Skill 시작 시 항상 먼저)

아래 항목을 순서대로 확인하고 실패 시 즉시 중단한다:

### 1. 인자 확인

- 필수: `PDF_PATH` 환경 변수 또는 커맨드 인자
- 경로가 파일이 아니면 중단 + 구체 메시지

### 2. 팀 공유 설정 확인

- **현재 워크스페이스 레포 루트**에서 `yeoboya-workflow.config.json` 을 찾는다.
- 없으면 다음 메시지로 중단:

  ```
  ❌ 팀 공유 설정 파일이 없습니다: yeoboya-workflow.config.json

  팀 리드가 먼저 최초 셋업을 실행하고 이 파일을 레포에 커밋해야 합니다.
  최초 셋업은 별도 문서 참고: README.md 의 "팀 리드 최초 셋업" 섹션.
  ```

- 있으면 `pdf_spec_organizer.notion_database_id` 값을 읽어 Notion DB ID 로 사용.

### 3. Python 의존성 확인

Run (Bash):
```bash
python3 -c "import PyPDF2, pdf2image, PIL, yaml, pytesseract" 2>&1
```

실패 시:
```
❌ Python 의존성이 설치되지 않았습니다.
  pip install -r ${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/requirements.txt
```

### 4. Tesseract 확인 (경고만, 차단 아님)

Run: `command -v tesseract`

없으면 경고만:
```
⚠️  Tesseract 가 설치되지 않아 OCR fallback 이 비활성됩니다.
  이미지 전용 페이지의 텍스트 추출이 안 될 수 있습니다.
  설치: brew install tesseract tesseract-lang (macOS)
```
```

- [ ] **Step 2: 커밋 (WIP SKILL.md)**

```bash
mkdir -p /Users/chuchu/testPlugin/skills/pdf-spec-organizer
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "feat: initialize pdf-spec-organizer SKILL.md with precondition checks"
```

---

### Task 18: `SKILL.md` — Phase 1 (파싱)

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Phase 1 섹션 추가**

SKILL.md 끝에 append:

```markdown
## Phase 1 — 파싱

### 1-1. 임시 작업 폴더 생성

```bash
PDF_PATH="$1"  # 절대경로로 정규화된 값
PDF_HASH=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/pdf_hash.py" "$PDF_PATH")
TS=$(date +%s)
WORK_DIR="/tmp/spec-draft-${PDF_HASH}-${TS}"
mkdir -p "$WORK_DIR"
DRAFT_PATH="${WORK_DIR}/draft.md"
```

### 1-2. 동시 실행 감지

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  query-recent --hash "$PDF_HASH" --within-seconds 300 > "${WORK_DIR}/recent.json"
```

`recent.json` 의 `found` 가 `true` 면 사용자에게 경고:
```
⚠️  5분 내 동일 PDF 를 다른 실행이 처리했습니다.
  실행자: <entry.who>  시작: <time>  경로: <entry.draft_path>

덮어쓰기 전에 조율하세요. 계속할까요? (y/n)
```

`n` 이면 중단.

### 1-3. 실행 기록

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  record --hash "$PDF_HASH" --draft-path "$DRAFT_PATH" --status running
```

### 1-4. parse_pdf 실행

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/parse_pdf.py" \
  "$PDF_PATH" --out-dir "${WORK_DIR}/images" > "${WORK_DIR}/parsed.json"
```

exit code:
- `0`: 계속
- `1`: 파일/포맷 오류 → 에러 출력 + 중단
- `3`: 암호화 PDF → "암호 해제된 PDF로 다시 시도해주세요" 안내 + 중단

### 1-5. OCR fallback 판단

`parsed.json` 의 `pages` 에서 `has_text: false` 페이지가 있고 이미지가 있으면 OCR 실행:

```bash
IMG_PATHS=$(python3 -c "
import json
data = json.load(open('${WORK_DIR}/parsed.json'))
need_ocr = any(not p['has_text'] for p in data['pages'])
if need_ocr:
    print(' '.join(img['path'] for img in data['images']))
" )

if [ -n "$IMG_PATHS" ] && command -v tesseract >/dev/null 2>&1; then
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/ocr_fallback.py" \
    --images $IMG_PATHS > "${WORK_DIR}/ocr.json"
  echo "  (OCR 결과 품질이 낮을 수 있습니다. 개발자 노트에서 보완하세요.)"
fi
```

### 1-6. PII 스캔

```bash
python3 -c "
import json
data = json.load(open('${WORK_DIR}/parsed.json'))
print('\n'.join(p['text'] for p in data['pages']))
" | python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/pii_scan.py" > "${WORK_DIR}/pii.json"
```

`pii.json` 의 `findings` 가 비어있지 않으면 경고만 표시 (차단 아님):
```
⚠️  PII 로 의심되는 패턴이 발견되었습니다 (N건):
  - email (line 12): u***r@example.com
  - phone (line 34): 010-****-5678

민감 정보가 Notion 에 퍼블리시될 수 있습니다. 진행할까요? (y/n)
```

### 1-7. 통합 데이터 구성

`parsed.json`, `ocr.json` (있으면), `pii.json` 을 Claude 가 읽어 후속 Phase 에서 사용한다.
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "feat: add Phase 1 (parsing) to SKILL.md"
```

---

### Task 19: `SKILL.md` — Phase 2 (구조화 + 개입 ①)

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Phase 2 섹션 추가**

```markdown
## Phase 2 — 구조화 + 개입 ①

### 2-1. Claude 에게 피처 추출 지시

Phase 1 산출물(`parsed.json` + `ocr.json` + 이미지 썸네일)을 읽어 **피처 리스트**를 생성한다.

추출 규칙:
- 한 피처 = 하나의 사용자 가치 단위 (화면/플로우 1~N개 포함 가능)
- 각 피처마다 필드:
  - `name`: 간결한 한글 이름 (10자 내외)
  - `platform`: iOS / Android / 공통 중 1개 이상
  - `summary`: 1-2문장
  - `screens`: 관련 이미지 페이지 번호 리스트
  - `requirements`: 불릿 포인트 리스트

결과를 `${WORK_DIR}/features.json` 으로 저장.

### 2-2. 사용자 확인 프롬프트

`references/review-format.md` 의 "터미널 출력 규약" 섹션을 따라 피처 목록 출력:

```
피처 3개 추출됨:
  1. 알림 설정 화면 (iOS, Android)
  2. 푸시 권한 요청 플로우 (iOS, Android)
  3. 빈 상태 UI (공통)

이대로 진행할까요?
  y) 진행
  s N) 피처 N번 쪼개기
  m N,M) 피처 N,M 합치기
  r N) 피처 N번 리네이밍
  t N) 피처 N번 플랫폼 변경
  e) 에디터에서 수정
  c) 취소
>
```

**`--fast` 플래그 처리:**
- 피처 경계 확인(s/m/r) 은 자동 통과
- **플랫폼 태깅(t) 확인은 여전히 강제**. 프롬프트:
  ```
  [--fast 모드] 플랫폼 태깅을 확인해주세요:
    1. 알림 설정 화면 → iOS, Android
    2. 푸시 권한 요청 플로우 → iOS, Android
    3. 빈 상태 UI → 공통

  모두 맞으면 y, 수정하려면 t N:
  >
  ```

### 2-3. 사용자 입력 처리 루프

각 명령별 동작:
- `y` → 다음 Phase
- `s N` → 피처 N번을 Claude 에게 "더 작게 쪼개세요" 지시, 결과 갱신 후 다시 2-2 로
- `m N,M` → Claude 에게 "N번과 M번을 병합, 이름/플랫폼 재정의" 지시 후 2-2
- `r N` → 사용자에게 새 이름 입력받아 N번 `name` 교체 후 2-2
- `t N` → 사용자에게 새 플랫폼 선택(체크박스) 받아 N번 `platform` 교체 후 2-2
- `e` → `${WORK_DIR}/features.md` 로 직렬화 → `$EDITOR` 로 열기 → 저장 후 다시 파싱해서 `features.json` 갱신 → 2-2
- `c` → Phase 정리(아래) 후 중단

### 2-4. 중단 정리

취소 시:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  update-status --draft-path "$DRAFT_PATH" --status failed
```
/tmp 폴더는 TTL 에 의해 7일 후 자동 삭제.
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "feat: add Phase 2 (structuring + intervention 1) to SKILL.md"
```

---

### Task 20: `SKILL.md` — Phase 3 (누락 체크)

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Phase 3 섹션 추가**

```markdown
## Phase 3 — 누락 체크

### 3-1. 체크리스트 로드

```bash
CHECKLIST_YAML="${CLAUDE_PLUGIN_ROOT}/config/pdf-spec-organizer/checklist.yaml"
CHECKLIST_FALLBACK="${CLAUDE_PLUGIN_ROOT}/config/pdf-spec-organizer/default-checklist.json"

python3 -c "
import sys, json, yaml
try:
    items = yaml.safe_load(open('${CHECKLIST_YAML}'))['items']
    source = 'yaml'
except Exception as e:
    print(f'⚠️  checklist.yaml 파싱 실패: {e}. fallback 사용.', file=sys.stderr)
    items = json.load(open('${CHECKLIST_FALLBACK}'))['items']
    source = 'fallback'
print(json.dumps({'items': items, 'source': source}))
" > "${WORK_DIR}/checklist.json"
```

`source == 'fallback'` 이면 경고 표시 (계속 진행).

### 3-2. 피처별 누락 항목 계산

각 피처에 대해:
1. `applies_to` 와 피처 `platform` 의 교집합이 비어있으면 해당 체크 항목은 스킵
2. 남은 항목에 대해 Claude 가 피처의 `summary` + `requirements` 를 읽고 "이 항목이 명시되어 있는가?" 판정
3. 명시 안 됨 → 누락으로 표시

결과를 `${WORK_DIR}/missing.json` 으로 저장:
```json
{
  "features": [
    {
      "name": "알림 설정 화면",
      "missing": ["error_cases", "offline"],
      "satisfied": ["empty_state", "loading", "a11y"]
    }
  ]
}
```

### 3-3. 요약 출력

```
누락 체크 완료:
  1. 알림 설정 화면
     누락: 에러 케이스, 오프라인 처리
     명시: 빈 상태, 로딩 상태, 접근성

  2. 푸시 권한 요청 플로우
     누락: 권한 거부 재요청 UX
     명시: 에러 케이스, 빈 상태

  의도된 제외는 다음 단계 "개발자 노트" 에 적어주세요.

계속하려면 Enter.
```
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "feat: add Phase 3 (missing check) to SKILL.md"
```

---

### Task 21: `SKILL.md` — Phase 4 (노트 + 개입 ②)

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Phase 4 섹션 추가**

```markdown
## Phase 4 — 개발자 노트 + 미리보기 + 개입 ②

### 4-1. 초안 md 파일 렌더

`features.json` + `missing.json` + `parsed.json` 을 통합해 `${DRAFT_PATH}` 로 저장.
포맷은 `references/review-format.md` 의 "초안 파일 구조" 를 엄격히 따른다.

**중요:**
- 헤더 `<!-- plugin-state ... -->` 에 `phase: 4`, `pdf_hash`, `source_file`, `created_at` 포함
- 각 피처마다 iOS/Android/공통 노트 섹션은 **빈 상태**로 렌더 (사용자가 채움)
- `--fast` 플래그여도 이 Phase 는 생략되지 않음

### 4-2. 사용자에게 노트 작성 프롬프트

```
다음 단계: 개발자 노트 작성

초안 파일: /tmp/spec-draft-<hash>-<ts>/draft.md

당신의 플랫폼 섹션(iOS / Android / 공통)만 채우세요.
타 플랫폼 섹션은 Phase 5 병합 시 보존됩니다.

어떻게 할까요?
  e) 에디터($EDITOR)로 열기  ← 권장
  s) 건너뛰기 (빈 노트로 퍼블리시)
  c) 취소
>
```

`e` 선택 시 `$EDITOR` 로 열기. macOS 기본값이 없으면 `code` / `vim` 순으로 시도.

### 4-3. 저장 후 검증

에디터 종료 후:
- 파일 존재 확인
- `plugin-state` 헤더 파싱해 `phase` 업데이트
- 노트 섹션이 완전히 비어도 경고만 표시 (계속 가능):
  ```
  ℹ️  노트가 비어있습니다. Phase 5 로 계속할까요? (y/n/e)
  ```
  `e` 는 다시 에디터 열기.

### 4-4. 최종 미리보기

터미널에 초안 요약 출력:
```
미리보기:

  피처 3개, 누락 항목 5개, 노트:
    - 알림 설정 화면: iOS ✓, Android ✗, 공통 ✓
    - 푸시 권한 요청 플로우: iOS ✓, Android ✗, 공통 ✗
    - 빈 상태 UI: iOS ✗, Android ✗, 공통 ✗

  Notion 에 퍼블리시할까요?
    y) 퍼블리시
    e) 에디터로 다시 열기
    c) 취소
>
```

### 4-5. 취소 / 에디터 재진입 처리

- `c` → Phase 5 로 가기 전 정리 (상태 failed 로 기록)
- `e` → 4-2 로 돌아감
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "feat: add Phase 4 (notes + preview) to SKILL.md"
```

---

### Task 22: `SKILL.md` — Phase 5 (충돌 + 퍼블리시)

**Files:**
- Modify: `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`

- [ ] **Step 1: Phase 5 섹션 추가**

```markdown
## Phase 5 — 충돌 처리 + 퍼블리시 + 개입 ③

### 5-1. DB ID 확보

Precondition 에서 읽은 `notion_database_id` 사용. 없으면 Phase 0에서 이미 중단됐을 것이므로 여기서는 존재 가정.

### 5-2. 피처별 루프

각 피처에 대해:

#### 5-2-a. 기존 페이지 조회

`mcp__claude_ai_Notion__notion-search` 로 **DB ID 필터 + 제목 완전 일치** 쿼리. 결과 있으면 충돌 처리로, 없으면 새로 생성.

#### 5-2-b. 충돌 시

`references/conflict-policy.md` 의 정책에 따라 프롬프트:

```
Notion 에 같은 피처가 이미 존재합니다:
  제목: <피처명>
  최근 생성자: <author>
  생성일: <date>
  기존 PDF 해시: <hash or "없음">  (현재: <my_hash>)

어떻게 할까요?
  [1] 병합 (내 플랫폼 섹션만 append) ← 기본
  [2] 덮어쓰기 (기존 노트 손실 가능)
  [3] 새 버전 (이전_버전 Relation 으로 연결)
  [4] 건너뛰기 (이 피처만 스킵)
>
```

**`--fast` 플래그:** `[1] 병합` 자동 선택. [2]/[3]/[4] 는 `--fast` 에서도 프롬프트 발생.

- **병합**: `mcp__claude_ai_Notion__notion-fetch` 로 기존 페이지 본문 읽기 → 내 플랫폼 섹션만 교체 → `mcp__claude_ai_Notion__notion-update-page` 로 업데이트
- **덮어쓰기**: "정말로 덮어쓰시겠습니까? (y/N)" 추가 확인 → yes 면 전체 본문 교체
- **새 버전**: 새 페이지 생성 + 새 페이지의 `이전_버전` Relation 에 기존 페이지 연결
- **건너뛰기**: 다음 피처로

#### 5-2-c. 충돌 없으면 새 페이지 생성

`mcp__claude_ai_Notion__notion-create-pages` 로 생성:
- 속성: 이름, 플랫폼, 상태=Draft, 원본_PDF=파일명만, PDF_해시, 생성자=현재 사용자, 누락_항목=`missing` 리스트
- 본문: `draft.md` 의 Notion 대응 블록으로 변환

#### 5-2-d. 이미지 업로드

각 피처의 `screens` 이미지 경로를 Notion 파일 업로드 API 로 올려 `image` 블록으로 삽입.

**Notion MCP 의 파일 업로드 지원 여부 점검:**
- `mcp__claude_ai_Notion__notion-create-pages` 가 로컬 파일 경로를 직접 지원하지 않는 경우 대비:
  - 1차: 이미지 블록에 placeholder URL 삽입 + 캡션에 로컬 경로 주석으로 표시
  - 2차 (v0.2 계획): S3/imgur 중계 업로더 추가. 지금은 placeholder + 경고.
- 이 대응은 `docs/manual-qa.md` 의 이슈로도 문서화.

### 5-3. 실행 기록 갱신

모든 피처 성공 시:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" \
  update-status --draft-path "$DRAFT_PATH" --status success
```

부분 실패 시 failed 기록 + 실패 피처 목록을 터미널에 표시 + `/spec-resume` 가이드:
```
⚠️  3개 중 2개 피처만 퍼블리시됐습니다:
  ✓ 알림 설정 화면
  ✓ 푸시 권한 요청 플로우
  ✗ 빈 상태 UI (Notion API timeout)

이어서 시도: /spec-resume --resume-latest
초안: <draft_path>
```

### 5-4. 결과 요약

성공 시:
```
✓ 퍼블리시 완료:
  - 알림 설정 화면: https://notion.so/...
  - 푸시 권한 요청 플로우: https://notion.so/...
  - 빈 상태 UI: https://notion.so/...

초안은 3일 후 자동 삭제됩니다: <draft_path>
```

### 5-5. GC 트리거

기회적 GC (성공 시만):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/pdf-spec-organizer/scripts/draft_registry.py" gc
```
```

- [ ] **Step 2: SKILL.md 에 "Resume 모드" 섹션 추가**

```markdown
## Resume 모드

`/spec-resume` 가 호출되면 이 Skill 이 다른 모드로 진입.

### R-1. 초안 선택

- `--resume-latest`: `draft_registry list-latest --count 5` 결과에서 **`status` 가 `running` 또는 `failed`** 인 최신 항목 자동 선택. 없으면 사용자에게 리스트 보여주고 선택받기.
- `--resume <path>`: 지정된 경로 사용. 없으면 중단.

### R-2. 상태 복구

초안 파일의 `<!-- plugin-state -->` 헤더에서 `phase` 를 읽어 다음 Phase 부터 시작:
- `phase: 1` → Phase 2 부터 재실행
- `phase: 2` → Phase 3 부터
- `phase: 3` → Phase 4 부터
- `phase: 4` → Phase 5 부터

### R-3. 실행

해당 Phase 부터 본 워크플로우와 동일하게 진행. 마지막에 `update-status` 갱신.

## Update 모드 (`/spec-update`)

기존 Notion 페이지 URL 을 받아 **Phase 4 만** 다시 실행.

### U-1. 페이지 조회

`mcp__claude_ai_Notion__notion-fetch` 로 기존 페이지 본문 가져옴.

### U-2. 임시 초안으로 변환

본문을 `references/review-format.md` 포맷의 md 로 변환해 `${WORK_DIR}/draft.md` 저장.

### U-3. 노트 작성 (Phase 4 재사용)

Phase 4 로직 그대로 실행.

### U-4. 병합 퍼블리시

Phase 5 의 **병합** 경로만 사용. 덮어쓰기/새 버전은 이 모드에서 허용 안 함.
```

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add skills/pdf-spec-organizer/SKILL.md && git commit -m "feat: add Phase 5 (publish), Resume, Update modes to SKILL.md"
```

---

## Phase 5: 슬래시 커맨드

### Task 23: `commands/spec-from-pdf.md`

**Files:**
- Create: `/Users/chuchu/testPlugin/commands/spec-from-pdf.md`

- [ ] **Step 1: 디렉토리 생성 및 커맨드 작성**

```bash
mkdir -p /Users/chuchu/testPlugin/commands
```

```markdown
---
name: spec-from-pdf
description: PDF 스펙(PRD+디자인+플로우)을 파싱해 Notion 피처 DB 페이지로 정리한다. 명세 누락 체크 + 플랫폼별 개발자 노트 공유.
argument-hint: <pdf-path> [--fast]
allowed-tools: Bash Read Write Edit Grep Glob mcp__claude_ai_Notion__*
---

# /spec-from-pdf

PDF 스펙을 Notion 피처 DB 페이지로 정리한다.

## 사용법

```
/spec-from-pdf ~/Downloads/feature-spec.pdf
/spec-from-pdf ~/Downloads/feature-spec.pdf --fast
```

## 동작

1. 인자를 절대 경로로 정규화
2. `pdf-spec-organizer` Skill 을 실행 (5 Phase 워크플로우)
3. 성공 시 생성된 Notion 페이지 URL 출력

## 인자 처리

아래 지시대로 인자를 검증하고 Skill 을 호출한다:

```bash
RAW_ARG="$1"
FAST_FLAG=""

# --fast 플래그 파싱
for a in "$@"; do
  if [ "$a" = "--fast" ]; then FAST_FLAG="--fast"; fi
done

# 경로 정규화
if [ -z "$RAW_ARG" ] || [ "$RAW_ARG" = "--fast" ]; then
  echo "❌ PDF 경로가 필요합니다. 사용법: /spec-from-pdf <pdf-path> [--fast]" >&2
  exit 2
fi

PDF_PATH=$(python3 -c "import sys, os; print(os.path.realpath(os.path.expanduser(sys.argv[1])))" "$RAW_ARG")

if [ ! -f "$PDF_PATH" ]; then
  echo "❌ 파일을 찾을 수 없습니다: $PDF_PATH" >&2
  exit 1
fi

if [ "${PDF_PATH##*.}" != "pdf" ] && [ "${PDF_PATH##*.}" != "PDF" ]; then
  echo "⚠️  .pdf 확장자가 아닙니다: $PDF_PATH. 계속 시도합니다."
fi

export PDF_PATH FAST_FLAG
```

이후 `pdf-spec-organizer` Skill 을 진입점으로 실행한다. Skill 은 위 환경변수를 읽어 워크플로우를 시작한다.

자세한 워크플로우는 `skills/pdf-spec-organizer/SKILL.md` 참조.
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add commands/spec-from-pdf.md && git commit -m "feat: add /spec-from-pdf slash command"
```

---

### Task 24: `commands/spec-update.md`

**Files:**
- Create: `/Users/chuchu/testPlugin/commands/spec-update.md`

- [ ] **Step 1: 작성**

```markdown
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
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add commands/spec-update.md && git commit -m "feat: add /spec-update slash command"
```

---

### Task 25: `commands/spec-resume.md`

**Files:**
- Create: `/Users/chuchu/testPlugin/commands/spec-resume.md`

- [ ] **Step 1: 작성**

```markdown
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
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add commands/spec-resume.md && git commit -m "feat: add /spec-resume slash command"
```

---

## Phase 6: 수동 QA 문서

### Task 26: `docs/manual-qa.md`

**Files:**
- Create: `/Users/chuchu/testPlugin/docs/manual-qa.md`

- [ ] **Step 1: 작성**

```markdown
# 수동 QA 체크리스트 — pdf-spec-organizer

각 릴리스 전 반드시 확인. 샘플 PDF 는 `skills/pdf-spec-organizer/scripts/tests/samples/` 사용.

## 사전 준비

- [ ] Python 의존성 설치 완료 (`pip install -r skills/pdf-spec-organizer/scripts/requirements.txt`)
- [ ] Tesseract 설치 완료 (`brew install tesseract tesseract-lang`)
- [ ] `yeoboya-workflow.config.json` 프로젝트 레포 루트에 존재
- [ ] Claude Code 에 Notion MCP 연결됨

## 정상 플로우

### 텍스트 위주 PDF
- [ ] `/spec-from-pdf tests/samples/minimal.pdf` 실행
- [ ] Phase 1~5 모두 통과
- [ ] Notion 페이지가 생성되고 URL 이 출력됨
- [ ] 페이지 열어보면 섹션 구조가 `references/review-format.md` 와 일치
- [ ] 속성(플랫폼/상태/PDF_해시/누락_항목) 모두 채워져 있음

### 이미지 위주 PDF
- [ ] `/spec-from-pdf tests/samples/image_only.pdf` 실행
- [ ] OCR fallback 이 트리거되고 "품질 낮을 수 있음" 경고 출력
- [ ] Notion 페이지에 이미지가 포함됨 (placeholder 라도)

### `--fast` 플래그
- [ ] `/spec-from-pdf tests/samples/minimal.pdf --fast` 실행
- [ ] 개입 ①(피처 경계)는 자동 통과, 플랫폼 태깅 확인은 여전히 발생
- [ ] 개입 ②(노트)는 강제 — 에디터 열림
- [ ] 개입 ③(충돌)은 기본값(병합) 자동 적용. 덮어쓰기/새버전은 발생 안 해야 정상

## 취소 경로

- [ ] Phase 2 에서 `c` → Notion 에 아무것도 안 만들어졌는지 확인
- [ ] Phase 4 에서 `c` → 동일
- [ ] Phase 5 충돌 시 `4) 건너뛰기` → 해당 피처만 스킵, 나머지 정상

## 동시 실행 감지

- [ ] 같은 PDF 로 두 세션 빠르게 실행 (5분 이내)
- [ ] 두 번째 실행에 "5분 내 동일 PDF" 경고 표시

## 병합 동작

- [ ] 사용자 A 가 피처 생성 (iOS 노트 작성)
- [ ] 사용자 B 가 같은 PDF 로 병합 실행 (Android 노트 작성)
- [ ] Notion 페이지에 iOS + Android 노트 **둘 다** 남아 있음

## 에러 케이스

- [ ] 존재하지 않는 경로 → 구체 에러 메시지
- [ ] 암호화 PDF → 중단 + 힌트
- [ ] PII 패턴 포함 PDF → 경고 후 사용자 확인
- [ ] `yeoboya-workflow.config.json` 없음 → 셋업 가이드 + 중단
- [ ] Notion MCP 실패 → 재시도 1회 후 초안 보존 + `/spec-resume` 가이드

## Resume

- [ ] Phase 3 에서 Ctrl+C → `/spec-resume --resume-latest` 로 Phase 4 부터 재개
- [ ] 초안 파일 직접 지정 `/spec-resume <path>` 동작 확인

## Update

- [ ] 기존 페이지 URL 에 `/spec-update <url>` → Phase 4 만 실행됨
- [ ] 내 플랫폼 노트만 갱신, 타 플랫폼 노트 보존

## TTL / 정리

- [ ] 성공 실행 후 3일 지난 초안이 gc 로 자동 삭제되는지 (시간 조작 필요 시 `draft_registry gc` + ttl-seconds 로 시뮬)
- [ ] 실패 실행 후 7일 TTL 확인

## 알려진 이슈

- Notion MCP 의 로컬 이미지 업로드 미지원 시 placeholder URL + 캡션으로 대체됨. v0.2 에서 S3/imgur 중계 계획.
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && git add docs/manual-qa.md && git commit -m "docs: add manual QA checklist"
```

---

## Phase 7: 통합 검증

### Task 27: 전체 유닛 테스트 통과 확인

- [ ] **Step 1: 모든 Python 테스트 실행**

Run:
```bash
cd /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts
source .venv/bin/activate
pytest tests/ -v
```
Expected: 모두 PASS (tesseract 없으면 OCR 테스트 skip 표시)

- [ ] **Step 2: 실패가 있으면 해당 Task 로 돌아가 수정**

---

### Task 28: 플러그인 수동 설치 및 dry-run

- [ ] **Step 1: Claude Code 에 플러그인 로드**

Claude Code 설정 파일에 플러그인 경로 추가:
- Run: Claude Code 실행 시 `--plugin-dir /Users/chuchu/testPlugin` 옵션, 또는
- `~/.claude/settings.json` 에 플러그인 디렉토리 등록

- [ ] **Step 2: 슬래시 커맨드 인식 확인**

Claude Code 에서 `/` 입력 후 `spec-from-pdf`, `spec-update`, `spec-resume` 노출되는지 확인.

- [ ] **Step 3: 샘플 PDF 로 정상 경로 1회 실행**

```
/spec-from-pdf /Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/tests/samples/minimal.pdf
```

(미리 `yeoboya-workflow.config.json` 을 테스트용 Notion DB 가리키게 준비)

- [ ] **Step 4: 결과를 `docs/manual-qa.md` 체크리스트와 대조**

최소 "정상 플로우 — 텍스트 위주 PDF" 전부 체크되어야 다음 단계로.

- [ ] **Step 5: 발견된 이슈를 CHANGELOG.md 의 "Known issues" 섹션에 기록**

```bash
cd /Users/chuchu/testPlugin && git add CHANGELOG.md && git commit -m "docs: record known issues from dry-run"
```

---

### Task 29: 최종 커밋 + 버전 태그

- [ ] **Step 1: CHANGELOG.md 의 `[Unreleased]` 를 `[0.1.0] - 2026-04-19` 로 변경**

- [ ] **Step 2: 태그**

```bash
cd /Users/chuchu/testPlugin && git add CHANGELOG.md && git commit -m "chore: release v0.1.0" && git tag v0.1.0
```

- [ ] **Step 3: 완료 메시지**

`pdf-spec-organizer` v0.1.0 구현 완료. 다음 기능 추가는 `skills/<new>/`, `commands/<new>/`, `config/<new>/` 로 독립 디렉토리에서 진행.

---

## 오픈 이슈 (스펙의 오픈 이슈에서 이어짐)

구현 중 결정 필요:

1. **Notion MCP 의 이미지 업로드 지원 여부** — Phase 5-2-d 참조. 미지원 시 placeholder URL 로 대체하고 v0.2 에서 S3/imgur 중계.
2. **Claude Code 의 `$EDITOR` 호출 방식** — SKILL.md 내 Bash 블록에서 `$EDITOR` 가 실제로 인터랙티브 에디터를 띄울 수 있는지 Task 28 에서 검증.
3. **`--fast` 플래그의 플랫폼 태깅 확인 UX** — 현재는 "모두 맞으면 y, 아니면 t N" 형식. Task 28 실사용 후 조정 가능.
4. **Tesseract 언어 팩** — `eng+kor` 기본. 한국어 팩 미설치 시 자동 감지 후 `eng` 로 폴백하는 로직 필요 여부 결정.
