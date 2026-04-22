# Error Handling Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 한계 분석에서 지적된 silent failure 3건을 해결하고, 기존 커맨드에 deprecation 경고를 주입한다. (1) Phase 3.5 JSON 파싱 실패 명시 경고 (2) Notion API exponential backoff (3) OCR 미설치 차단.

**Architecture:** Pydantic 스키마 검증 + retry 래퍼 + OCR pre-check. 기존 `enrich_features.py`, `page_publisher.py`, `parse_pdf.py` 수정. 기존 deprecated 커맨드 파일은 wrapper 재호출 shim 으로 교체.

**Tech Stack:** Pydantic, Python, Bash.

**Spec reference:** 설계 문서 섹션 9

**PR 번호:** 8/8 (마지막)

**Depends on:** PR 1, 4

---

## File Structure Overview

| 경로 | 유형 | 변경 |
|------|------|------|
| `skills/common/scripts/enrich_features.py` | 수정 | Pydantic 스키마 검증 + 경고 |
| `skills/common/scripts/notion_client.py` | 생성 | with_retry 래퍼 |
| `skills/common/scripts/page_publisher.py` | 수정 | with_retry 적용 + checkpoint |
| `skills/pdf-spec-organizer/scripts/parse_pdf.py` | 수정 | OCR 미설치 차단 |
| `skills/pdf-spec-organizer/scripts/ocr_fallback.py` | 수정 | raise SkillError |
| `commands/spec-from-pdf.md` | 수정 | deprecation shim |
| `commands/spec-update.md` | 수정 | deprecation shim |
| `commands/spec-resume.md` | 수정 | deprecation shim |
| `skills/common/scripts/tests/test_notion_client.py` | 생성 | |
| `skills/common/scripts/tests/test_enrich_features_validation.py` | 생성 | |

---

## Commit 1: `notion_client.py` — exponential backoff

### Task 1.1: Retry 래퍼

**Files:**
- Create: `skills/common/scripts/notion_client.py`
- Create: `skills/common/scripts/tests/test_notion_client.py`

- [ ] **Step 1: 테스트**

```python
import time
import pytest
from unittest.mock import MagicMock
from notion_client import with_retry, NotionRateLimitError, NotionServerError


def test_success_first_attempt():
    fn = MagicMock(return_value="ok")
    assert with_retry(fn, max_attempts=3, base_delay=0.01) == "ok"
    assert fn.call_count == 1


def test_retry_on_rate_limit():
    fn = MagicMock(side_effect=[NotionRateLimitError("429"), "ok"])
    result = with_retry(fn, max_attempts=3, base_delay=0.01)
    assert result == "ok"
    assert fn.call_count == 2


def test_exhausts_attempts():
    fn = MagicMock(side_effect=NotionRateLimitError("429"))
    with pytest.raises(NotionRateLimitError):
        with_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 3


def test_non_retry_error_propagates_immediately():
    fn = MagicMock(side_effect=ValueError("bad input"))
    with pytest.raises(ValueError):
        with_retry(fn, max_attempts=3, base_delay=0.01)
    assert fn.call_count == 1


def test_backoff_delays_increase(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    fn = MagicMock(side_effect=[
        NotionRateLimitError("1"),
        NotionRateLimitError("2"),
        "ok",
    ])
    with_retry(fn, max_attempts=3, base_delay=2.0)
    assert sleeps == [2.0, 4.0]  # 2 → 4 → 8 (ok 나오기 전까지)
```

- [ ] **Step 2: 구현**

```python
"""Notion API 재시도 래퍼 (exponential backoff)."""
import time
import logging
from typing import Callable, TypeVar


logger = logging.getLogger(__name__)
T = TypeVar("T")


class NotionRateLimitError(Exception):
    """429 Too Many Requests."""
    pass


class NotionServerError(Exception):
    """5xx 응답."""
    pass


RETRYABLE = (NotionRateLimitError, NotionServerError)


def with_retry(
    fn: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 2.0,
) -> T:
    """Exponential backoff: 2s → 4s → 8s.

    Args:
        fn: 호출할 함수 (no args).
        max_attempts: 최대 시도 횟수.
        base_delay: 첫 지연 (초).
    """
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except RETRYABLE as e:
            last_exc = e
            if attempt == max_attempts - 1:
                break
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"[Notion API] {e.__class__.__name__}: {e}. "
                f"{delay}초 후 재시도 ({attempt+1}/{max_attempts})"
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
```

- [ ] **Step 3: 테스트 + 커밋**

```bash
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_notion_client.py -v
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/notion_client.py \
        skills/common/scripts/tests/test_notion_client.py && \
git commit -m "feat(common): notion_client.with_retry — exponential backoff"
```

---

## Commit 2: Phase 3.5 Pydantic 검증

### Task 2.1: `enrich_features.py` 수정

**Files:**
- Modify: `skills/common/scripts/enrich_features.py`

- [ ] **Step 1: 현재 구조 확인**

```bash
grep -n "parse\|json.loads\|EMPTY_METADATA" \
  /Users/chuchu/testPlugin/skills/common/scripts/enrich_features.py | head -20
```

- [ ] **Step 2: Pydantic 스키마 도입**

파일 상단에 Pydantic 임포트 + 스키마 추가 (기존 구조 유지):

```python
import json
import sys
import logging
from pydantic import BaseModel, Field, ValidationError


logger = logging.getLogger(__name__)


class Phase35Response(BaseModel):
    """Claude 가 반환하는 메타 JSON 의 기대 스키마."""
    estimated_duration: str = Field(..., description="예: '2d', '4h'")
    dependencies: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)


def parse_claude_meta_response(raw: str) -> Phase35Response | None:
    """Claude 응답(JSON) → 검증된 Phase35Response. 실패 시 None + 명시 경고."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(
            f"⚠️  [Phase 3.5] JSON 파싱 실패: {e}\n"
            f"   → 예상시간/의존성 필드가 비어있는 상태로 진행합니다.\n"
            f"   → Notion 페이지에서 수동 입력하거나 `/spec-update`로 재생성 가능합니다.\n"
        )
        logger.error("[Phase 3.5] JSON parse error: %s", e, exc_info=True)
        return None

    try:
        return Phase35Response(**data)
    except ValidationError as e:
        sys.stderr.write(
            f"⚠️  [Phase 3.5] 메타 스키마 검증 실패\n"
            f"   원인: {e}\n"
            f"   → 예상시간/의존성 필드가 비어있는 상태로 진행합니다.\n"
        )
        logger.error("[Phase 3.5] schema validation error: %s", e, exc_info=True)
        return None
```

- [ ] **Step 3: 기존 호출 부위 리팩터**

`enrich_features.py` 내부에서 Claude 응답을 처리하는 기존 함수들을 `parse_claude_meta_response` 를 사용하도록 수정. 기존 `EMPTY_METADATA` 반환 지점은 이 함수의 `None` 반환으로 통합.

기존 파일 구조를 모르므로, 대략 다음 패턴:

```python
# 기존
try:
    result = json.loads(raw_response)
    return result, True
except Exception:
    return EMPTY_METADATA, False

# 신규
parsed = parse_claude_meta_response(raw_response)
if parsed is None:
    return EMPTY_METADATA, False
return parsed.model_dump(), True
```

실제 파일 구조에 맞춰 Edit.

- [ ] **Step 4: 테스트**

`/Users/chuchu/testPlugin/skills/common/scripts/tests/test_enrich_features_validation.py`:

```python
from enrich_features import parse_claude_meta_response, Phase35Response


def test_valid_response():
    raw = '{"estimated_duration": "2d", "dependencies": ["iOS팀"], "missing_items": []}'
    result = parse_claude_meta_response(raw)
    assert isinstance(result, Phase35Response)
    assert result.estimated_duration == "2d"
    assert result.dependencies == ["iOS팀"]


def test_invalid_json_returns_none(capsys):
    result = parse_claude_meta_response("not json")
    assert result is None
    captured = capsys.readouterr()
    assert "JSON 파싱 실패" in captured.err


def test_missing_required_field(capsys):
    raw = '{"dependencies": []}'  # estimated_duration 누락
    result = parse_claude_meta_response(raw)
    assert result is None
    captured = capsys.readouterr()
    assert "스키마 검증 실패" in captured.err


def test_wrong_type(capsys):
    raw = '{"estimated_duration": 123, "dependencies": "not a list"}'
    result = parse_claude_meta_response(raw)
    assert result is None
```

- [ ] **Step 5: `requirements.txt` 에 Pydantic 추가**

```bash
grep -q "pydantic" /Users/chuchu/testPlugin/skills/common/scripts/requirements.txt || \
  echo "pydantic>=2.0" >> /Users/chuchu/testPlugin/skills/common/scripts/requirements.txt
```

- [ ] **Step 6: 테스트 + 커밋**

```bash
pip install pydantic
cd /Users/chuchu/testPlugin/skills/common/scripts/tests && \
python3 -m pytest test_enrich_features_validation.py -v
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/enrich_features.py \
        skills/common/scripts/tests/test_enrich_features_validation.py \
        skills/common/scripts/requirements.txt && \
git commit -m "feat(phase3.5): Pydantic 스키마 검증 + 명시 경고 (silent failure 제거)"
```

---

## Commit 3: `page_publisher.py` — retry + checkpoint

### Task 3.1: Notion publisher 에 재시도 적용

**Files:**
- Modify: `skills/common/scripts/page_publisher.py`

- [ ] **Step 1: 기존 chunk append 위치 파악**

```bash
grep -n "notion\|append\|chunk\|children" \
  /Users/chuchu/testPlugin/skills/common/scripts/page_publisher.py | head -20
```

- [ ] **Step 2: checkpoint 로직 추가**

파일 상단에 import + helper 추가:

```python
import json
from pathlib import Path

from notion_client import with_retry


CHECKPOINT_DIR = Path.home() / ".spec-organizer" / "checkpoints"


def _checkpoint_path(page_id: str) -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    # Notion page_id 는 UUID hyphen 제거 가능
    safe = page_id.replace("-", "")
    return CHECKPOINT_DIR / f"{safe}.json"


def _load_checkpoint(page_id: str) -> int:
    path = _checkpoint_path(page_id)
    if not path.exists():
        return 0
    try:
        return json.loads(path.read_text())["completed_idx"]
    except Exception:
        return 0


def _save_checkpoint(page_id: str, idx: int) -> None:
    _checkpoint_path(page_id).write_text(
        json.dumps({"completed_idx": idx})
    )


def _clear_checkpoint(page_id: str) -> None:
    path = _checkpoint_path(page_id)
    if path.exists():
        path.unlink()
```

- [ ] **Step 3: 기존 chunk append 함수 수정**

(실제 구현에 맞춰 조정)

```python
def publish_chunks(page_id: str, chunks: list[dict], notion_api_fn) -> None:
    """각 chunk 를 순차 append 하며, 실패 시 checkpoint 보존.

    Args:
        page_id: Notion 페이지 ID.
        chunks: 추가할 블록 리스트 (각 chunk 는 블록 배열).
        notion_api_fn: 호출 가능한 Notion API (children.append).
    """
    completed_idx = _load_checkpoint(page_id)
    for idx in range(completed_idx, len(chunks)):
        chunk = chunks[idx]
        def _call():
            return notion_api_fn(page_id=page_id, children=chunk)
        with_retry(_call, max_attempts=3, base_delay=2.0)
        _save_checkpoint(page_id, idx + 1)
    _clear_checkpoint(page_id)
```

- [ ] **Step 4: 기존 호출부 리팩터**

`page_publisher.py` 내부에서 chunk append 를 수행하던 기존 함수를 `publish_chunks` 로 치환 또는 내부에서 호출하도록 조정.

- [ ] **Step 5: 테스트**

```python
# test_page_publisher_retry.py (기존 파일에 병합 or 신규)
from unittest.mock import MagicMock
from page_publisher import publish_chunks, _clear_checkpoint


def test_publish_all_chunks_success(tmp_path, monkeypatch):
    monkeypatch.setattr("page_publisher.CHECKPOINT_DIR", tmp_path)
    api = MagicMock(return_value={"ok": True})
    chunks = [{"type": "paragraph"}] * 3
    publish_chunks("pid_123", chunks, api)
    assert api.call_count == 3


def test_publish_resumes_from_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr("page_publisher.CHECKPOINT_DIR", tmp_path)
    # 수동으로 checkpoint 설정 (2개 완료 상태)
    from page_publisher import _save_checkpoint
    _save_checkpoint("pid_456", 2)

    api = MagicMock()
    chunks = [{"x": i} for i in range(3)]
    publish_chunks("pid_456", chunks, api)
    assert api.call_count == 1  # idx 2 만 호출
```

- [ ] **Step 6: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/page_publisher.py \
        skills/common/scripts/tests/test_page_publisher*.py && \
git commit -m "feat(publisher): chunk append 에 retry + checkpoint 적용"
```

---

## Commit 4: OCR 미설치 차단

### Task 4.1: `parse_pdf.py` / `ocr_fallback.py` 수정

**Files:**
- Modify: `skills/pdf-spec-organizer/scripts/parse_pdf.py`
- Modify: `skills/pdf-spec-organizer/scripts/ocr_fallback.py`

- [ ] **Step 1: `SkillError` 정의 (공통)**

`skills/common/scripts/skill_errors.py`:

```python
"""스킬 런타임 에러 계층."""


class SkillError(RuntimeError):
    """사용자에게 보여지는 스킬 에러. 메시지에 해결 방법 포함 권장."""
    pass


class PrerequisiteError(SkillError):
    """전제 조건 미충족 (예: OCR 미설치)."""
    pass
```

- [ ] **Step 2: `ocr_fallback.py` 수정**

현재 구조 확인 후 silent skip 을 명시 raise 로 교체:

```python
import shutil
import sys
from pathlib import Path

# common 참조
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "common" / "scripts"))
from skill_errors import PrerequisiteError


def ensure_tesseract_available() -> None:
    if not shutil.which("tesseract"):
        raise PrerequisiteError(
            "이 PDF 는 이미지 전용이라 OCR 이 필요합니다.\n"
            "해결 방법:\n"
            "  1) macOS: brew install tesseract tesseract-lang\n"
            "  2) Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-kor\n"
            "  3) PDF 를 텍스트 선택 가능한 형태로 재생성\n"
            "  4) 자유 서술로 입력: '이 PDF 대신 설명으로 스펙 만들어줘'"
        )


def run_ocr_on_images(image_paths: list[Path]) -> str:
    ensure_tesseract_available()
    # ... (기존 OCR 로직)
```

- [ ] **Step 3: `parse_pdf.py` 에서 호출**

```python
from ocr_fallback import ensure_tesseract_available


def parse_pdf_with_ocr_fallback(pdf_path: Path) -> str:
    text = try_extract_text(pdf_path)
    if text.strip():
        return text
    # 이미지 전용 → OCR 필요
    ensure_tesseract_available()  # 없으면 PrerequisiteError raise
    return run_ocr_on_images(render_pdf_to_images(pdf_path))
```

- [ ] **Step 4: 테스트**

```python
# test_ocr_fallback.py 에 추가
from ocr_fallback import ensure_tesseract_available, PrerequisiteError


def test_raises_when_tesseract_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    import pytest
    with pytest.raises(PrerequisiteError) as exc_info:
        ensure_tesseract_available()
    assert "tesseract" in str(exc_info.value).lower()
    assert "해결 방법" in str(exc_info.value)
```

- [ ] **Step 5: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add skills/common/scripts/skill_errors.py \
        skills/pdf-spec-organizer/scripts/parse_pdf.py \
        skills/pdf-spec-organizer/scripts/ocr_fallback.py \
        skills/pdf-spec-organizer/scripts/tests/test_ocr_fallback.py && \
git commit -m "feat(ocr): tesseract 미설치 시 에러 차단 + 해결책 안내"
```

---

## Commit 5: Deprecated 커맨드 shim

### Task 5.1: `commands/spec-from-pdf.md` 갱신

**Files:**
- Modify: `commands/spec-from-pdf.md`
- Modify: `commands/spec-update.md`
- Modify: `commands/spec-resume.md`

- [ ] **Step 1: shim 템플릿 작성**

각 커맨드 파일을 아래 구조로 교체:

`commands/spec-from-pdf.md`:
```markdown
---
description: "[DEPRECATED v1.0] spec-organizer 로 위임됨. v1.5 에서 제거 예정."
---

**경고 메시지 (stderr)**:
```
[DEPRECATED] /spec-from-pdf 는 v1.5 에서 제거됩니다. 자연어로 호출해주세요:
  예) "이 PDF 로 스펙 만들어줘"
  또는 spec-organizer 스킬이 자동 감지합니다.
```

**즉시 위임**: spec-organizer 스킬을 Skill tool 로 호출.
- 인자 전달: 사용자 원본 인자 + `--work-type=새 기능` (default) + `--mode=create`
- 결과는 spec-organizer 가 반환.
```

`commands/spec-update.md`:
```markdown
---
description: "[DEPRECATED v1.0] spec-organizer 의 update 모드로 위임됨."
---

**경고**: `[DEPRECATED] /spec-update 는 v1.5 에서 제거됩니다.`

**위임**: spec-organizer 호출 시 `--mode=update` 와 원본 Notion URL 전달.
```

`commands/spec-resume.md`:
```markdown
---
description: "[DEPRECATED v1.0] spec-organizer 의 resume 모드로 위임됨."
---

**경고**: `[DEPRECATED] /spec-resume 는 v1.5 에서 제거됩니다.`

**위임**: spec-organizer 호출 시 `--mode=resume` 와 draft 경로 전달.
```

- [ ] **Step 2: 수동 검증**

각 커맨드 호출 시 경고가 실제로 로그에 남고 정상 위임되는지 확인 (수동 스모크 테스트).

- [ ] **Step 3: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add commands/spec-from-pdf.md commands/spec-update.md commands/spec-resume.md && \
git commit -m "refactor(commands): spec-* 를 deprecation shim 으로 전환"
```

---

## Commit 6: README + CHANGELOG 최종 업데이트

### Task 6.1: README.md 전면 갱신

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 기존 `/spec-from-pdf` 중심 섹션을 `spec-organizer` 중심으로 교체**

주요 변경:
- 사용법: 자연어 우선 (`"이 PDF 로 스펙 만들어줘"`)
- work_type 3종 지원 명시
- Deprecation 안내
- 설정 파일: `yeoboya-workflow.config.json` 은 동일 (변경 없음)

- [ ] **Step 2: 마이그레이션 가이드 섹션 추가**

```markdown
## v0.x → v1.0 마이그레이션

**변경 없는 것**:
- `yeoboya-workflow.config.json` (기존 `notion_database_id` 등 그대로)
- 기존 Notion 페이지 (touch-on-write 로 점진 마이그레이션)

**변경된 것**:
- `/spec-from-pdf` 등 구 커맨드는 경고 후 자동 위임 (v1.5 에서 제거)
- 신규 work_type 지원: 새 기능 + 버그 픽스 + 기능 강화
- PDF 없이도 스펙 작성 가능 (텍스트/링크 입력)

**권장 사용법**:
- 자연어 호출: `"이 PDF 스펙 만들어줘"`, `"로그인 버그 정리"`, `"다크모드 개선"`
- 작업 유형 명시하면 더 정확: `"이 PDF, 버그 픽스 쪽이야"`
```

### Task 6.2: CHANGELOG v1.0.0 엔트리

- [ ] **Step 1: `[Unreleased]` → `[1.0.0] - 2026-04-22` 로 승격**

Edit 로 CHANGELOG 상단 섹션 구조 정리:

```markdown
## [1.0.0] - 2026-04-22

### Added
- `spec-organizer` wrapper 스킬: 단일 진입점 + 자동 라우팅
- `bug-spec-organizer`, `enhancement-spec-organizer` 신규 스킬
- work_type 3종 지원 (새 기능 / 버그 픽스 / 기능 강화)
- PDF 없이 텍스트/URL 입력으로 스펙 작성 가능
- `common/scripts/`, `common/config/` 공유 레이어
- routing.yaml 2D 매트릭스 + 24셀 회귀 테스트
- work-type-schemas 스키마 주도 필드 수집
- checklist.yaml 의 `applies_to_work_type` 필터
- Notion API exponential backoff + chunk checkpoint
- Phase 3.5 Pydantic 검증 (silent failure 제거)
- OCR 미설치 차단 + 해결책 안내

### Changed
- `/spec-from-pdf`, `/spec-update`, `/spec-resume` 는 deprecation shim 으로 전환 (v1.5 제거 예정)
- 기존 SKILL.md 분리 (pdf-spec-organizer 축소 + 신규 스킬 2개)

### Deprecated
- `/spec-from-pdf`, `/spec-update`, `/spec-resume` (v1.5 에서 제거)
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/chuchu/testPlugin && \
git add README.md CHANGELOG.md && \
git commit -m "docs: v1.0.0 릴리스 노트 + 마이그레이션 가이드"
```

---

## Commit 7: 최종 smoke test + 회귀 확인

### Task 7.1: 전체 테스트 스위트 실행

- [ ] **Step 1: 전체 pytest**

```bash
cd /Users/chuchu/testPlugin && \
python3 -m pytest \
  skills/common/scripts/tests/ \
  skills/pdf-spec-organizer/scripts/tests/ \
  skills/spec-organizer/scripts/tests/ \
  skills/bug-spec-organizer/scripts/tests/ \
  skills/enhancement-spec-organizer/scripts/tests/ \
  evals/test_routing_matrix.py \
  -v 2>&1 | tail -40
```

Expected: **모든 테스트 PASS**, 회귀 0.

- [ ] **Step 2: 24셀 routing 확인**

```bash
cd /Users/chuchu/testPlugin && \
python3 -m pytest evals/test_routing_matrix.py -v 2>&1 | tail -30
```

Expected: **24/24 PASS**.

- [ ] **Step 3: 수동 스모크 (3 케이스)**

실제 Claude Code 에서:

1. **"이 PDF 로 스펙 만들어줘"** + PDF 첨부 → pdf-spec-organizer 트리거
2. **"로그인 버그 정리"** → bug-spec-organizer 트리거
3. **"다크모드 개선"** → enhancement-spec-organizer 트리거

각각 정상 Notion 페이지 생성되는지 확인.

### Task 7.2: 최종 태그

- [ ] **Step 1: 태그 생성 (선택)**

```bash
cd /Users/chuchu/testPlugin && \
git tag -a v1.0.0 -m "v1.0.0: spec-organizer wrapper + work_type 3종 지원"
```

---

## 완료 기준 (PR 8 & v1 전체)

- [ ] Phase 3.5 JSON 검증 실패 시 stderr 명시 경고
- [ ] Notion API 재시도 (2s/4s/8s) 적용
- [ ] OCR 미설치 시 PrerequisiteError 차단
- [ ] 3개 deprecated 커맨드 shim 전환
- [ ] README + CHANGELOG v1.0.0 정리
- [ ] 전체 테스트 스위트 PASS
- [ ] 수동 스모크 3 케이스 통과

## v1 릴리스 준비 체크리스트

- [ ] PR 1~8 모두 머지
- [ ] 기존 13개 단위 테스트 + 신규 15+ 통과
- [ ] routing-matrix 24/24
- [ ] 각 스킬 trigger-eval 95%+
- [ ] E2E 4 시나리오 (PDF 새기능 회귀 / bug 최소 / enhancement URL / resume)
- [ ] plugin.json 에 스킬 4개 등록 확인
- [ ] `yeoboya-workflow.config.json` 변경 없이 기존 사용자 동작 확인
- [ ] 태그 `v1.0.0` 푸시

---

## 전체 플랜 요약

| PR | 플랜 파일 | 예상 기간 |
|----|----------|----------|
| 1 | 01-common-core-extraction.md | 2일 |
| 2 | 02-routing-dispatcher.md | 3일 |
| 3 | 03-schemas-field-collector.md | 3일 |
| 4 | 04-spec-organizer-wrapper.md | 2일 |
| 5 | 05-bug-spec-organizer.md | 3일 |
| 6 | 06-enhancement-spec-organizer.md | 3일 |
| 7 | 07-checklist-migration.md | 1일 |
| 8 | 08-error-handling.md | 2일 |
| **합계** | | **19일 (≈ 4주)** |
