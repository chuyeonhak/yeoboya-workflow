# pdf-spec-organizer: Per-PDF Page Redesign — Design Spec

- **Date:** 2026-04-20
- **Author:** Swift_Chu (solution.yeoboya@gmail.com)
- **Status:** Draft — awaiting implementation plan
- **Scope:** `skills/pdf-spec-organizer/` + slash commands `/spec-from-pdf`, `/spec-update`, `/spec-resume`

## 1. Problem & Goal

Current behavior creates **one Notion page per feature** extracted from a PDF. A single PDF spec often yields 5–10 feature pages, cluttering the DB and making it hard to locate "the spec for this PDF." Teams asked for **one page per PDF**, with features organized as Toggle blocks inside.

**Goals:**
- `개방형_앱_전환_기획서 6.pdf` → single Notion page with all features as Toggle blocks.
- Preserve user-written notes (iOS/Android/공통) across `/spec-from-pdf` re-runs.
- Provide a one-time migration to consolidate already-created per-feature pages.

**Non-goals:**
- No mode flag to keep both behaviors. v2 fully replaces v1.
- No breaking change to Phase 1–3 logic (parsing / feature extraction / missing-check).

## 2. Architecture (Phase Flow)

The 5-Phase flow is preserved. Only Phase 4 (draft render) and Phase 5 (publish) change substantively.

| Phase | v1 | v2 |
|---|---|---|
| 1 Parse | unchanged | unchanged |
| 2 Structure | features extracted into list | **unchanged.** Each feature carries a stable `feature_id` (UUID) from this phase onward |
| 3 Missing | per-feature checklist | unchanged |
| 4 Draft + notes | renders per-feature section in `draft.md` | **renders single draft.md with Toggle-heading structure** and `feature_id` HTML markers |
| 5 Publish | creates N feature pages, matches by name | **creates 1 PDF page**; dedup by PDF-hash then filename; chunked block append with `sentinel` blocks |

## 3. Notion Page Body Structure

```
📄 [PDF 제목]                          (Title = 이름)
Properties:
  - 플랫폼      = union of all features
  - 상태        = single overall status
  - 원본 PDF    = filename only
  - PDF 해시    = sha256 prefix (12 chars)
  - 누락 항목   = union of all features' missing items
  - 생성자      = person

## 개요
(1–2 paragraphs, Claude-summarized)

## 피처별 상세
### 🔽 1. <피처명>                     (toggle heading 2)
  <!-- feature_id: <uuid> -->
  🟡 In Review                          (inline callout = per-feature status)
  **플랫폼:** 공통
  **개요:** ...
  **화면:** ![](...)
  **요구사항:** - ...
  **누락 체크:** - [ ] error_cases ...
  <!-- notes_ios_start -->
  ### iOS
  (user-editable)
  <!-- notes_ios_end -->
  <!-- notes_android_start -->
  ### Android
  (user-editable)
  <!-- notes_android_end -->
  <!-- notes_common_start -->
  ### 공통 질문
  (user-editable)
  <!-- notes_common_end -->
  <!-- publish_sentinel: feature_<id>_done -->

... (more toggles) ...

## 메타
- 원본 PDF: ...
- PDF 해시: ...
- 생성자/생성일
- (if migrated) 마이그레이션 소스: [구 피처 페이지 URL 목록]
```

**Why toggle headings:** Collapsed by default, so scanning a large PDF page is fast; each feature is still deep-linkable.

**Why `feature_id` markers:** Stable identity across re-runs. Rename/reorder does not orphan notes.

**Why `notes_*_start|end` markers:** Surgical note extraction during `/spec-update` merges, without fragile block-tree diffing.

**Why `publish_sentinel`:** `/spec-resume` can re-derive the append cursor from content, not from a fragile integer counter.

## 4. Phase 4 Draft Render Changes

- Single `draft.md` file instead of per-feature files.
- Each feature becomes a `### <name> {toggle="true"}` Notion-markdown block.
- `<!-- plugin-state -->` header gains fields reserved for Phase 5 (see Section 6).
- Existing `--fast` semantics preserved (Phase 4 never skipped).

## 5. Phase 5 Publish Changes

### 5.1 Conflict Detection (dedup)

```
1. Query Notion DB by PDF 해시 exact match.
   ├─ hit → "동일 PDF 재실행" prompt
   │         options: [덮어쓰기(노트 보존) / 새 버전 / 건너뛰기]
   └─ miss → query by filename.
             ├─ hit → "업데이트된 PDF" prompt (hash differs)
             │         options: [덮어쓰기(노트 보존) / 새 버전 / 건너뛰기]
             └─ miss → create new page.
```

`--fast` auto-selects nothing destructive. Overwrite / new-version paths always prompt.

### 5.2 Note-Preserving Overwrite

When user picks **덮어쓰기**, default behavior preserves notes:

1. Fetch existing page content.
2. Extract `<!-- notes_*_start -->…<!-- notes_*_end -->` blocks per `feature_id`.
3. Build new draft body; for each feature, inject preserved notes into the same-id toggle's note sections.
4. Features in the page but missing from the new draft → their notes move to a top-level **"이전 노트 (제거된 피처)"** section with the old feature name as subheading.
5. Property fields (`플랫폼`, `누락 항목`) are always replaced with fresh union (no accumulation of stale tags).

To bypass note preservation entirely, a hidden `--force-overwrite` flag exists. It is never auto-selected by `--fast`.

### 5.3 Chunked Publish (Notion API Limits)

Notion `create-pages` has a ~100-block ceiling per call. 7+ features × (image + requirements + missing + notes sections) can exceed this.

Algorithm:

```
1. Create shell page (properties + title + overview only) via notion-create-pages.
   Capture page_id.
2. Append blocks in chunks of ≤80 blocks. Preferred mechanism: notion-update-page
   with command=update_content, inserting before a trailing sentinel placeholder so
   each chunk's blocks appear at the intended position. (Implementation plan picks
   the exact API pattern; the invariant is "chunk N committed iff its sentinel is
   in the page body.")
3. After each successful chunk commit, ensure a sentinel comment block is in place:
     <!-- publish_sentinel: chunk_<N>_done -->
4. On rate-limit error → exponential backoff (1s, 2s, 4s, 8s, max 3 retries).
5. After final chunk, commit `<!-- publish_sentinel: complete -->`.
6. Update draft's plugin-state: publish_state=complete.
```

`last_block_sentinel_id` in plugin-state caches the most recent sentinel's block id if available; if the API does not expose stable block ids, resume falls back to scanning content for the latest `<!-- publish_sentinel: chunk_N_done -->` marker.

Partial failure halts the loop; `/spec-resume` picks up at the last sentinel.

### 5.4 Concurrent-Edit Safety

Even Phase 5's first publish path consults `draft_registry` for 5-minute-window warnings (existing behavior). No further locking at first-publish; conflict is caught at dedup (§5.1).

## 6. `plugin-state` Header (v2)

```html
<!-- plugin-state
phase: 5
pdf_hash: <short-hash>
source_file: <filename>
created_at: <iso8601>
publish_state: page_created | chunks_appending | complete | failed
page_id: <notion_page_id>                 (set after shell create)
last_block_sentinel_id: <id-or-null>       (latest sentinel block ID, for resume cursor)
-->
```

**`publish_state` transitions** (logged one-per-line to `${WORK_DIR}/publish.log` with ISO timestamps):

```
idle → page_created → chunks_appending → complete
                                        ↘ failed
```

v1-era drafts (missing these fields) are detected by absence of `publish_state`; resume falls back to a full re-publish path (see §7).

## 7. `/spec-resume` Changes

### 7.1 Arg Surface

Unchanged: `--resume-latest | <draft-path>`.

### 7.2 Resume Logic

```
1. Load draft. Read plugin-state.
2. If publish_state missing → legacy v1 draft:
     - Inform user: "v1 draft detected. Full re-publish will proceed."
     - Run Phase 4-5 as if brand new (no resume).
3. Else if publish_state == chunks_appending:
     - Fetch page_id from Notion. If 404 → prompt: 새로 퍼블리시할까요? (y/n)
     - Scan page content for latest <!-- publish_sentinel: chunk_N_done --> block.
     - Compute remaining chunks from draft's pending block list.
     - Resume append from there.
4. Else if publish_state == failed:
     - Show last error from publish.log.
     - Prompt: 재시도 / 취소.
5. Else (complete / idle): nothing to resume; show status.
```

### 7.3 Page-Drift Handling

If the `chunks_appending` page was manually edited (block count differs from what we'd expect):

- Sentinel-based resume is still safe because we append *after* the latest sentinel, not at a specific index.
- If sentinels were deleted by the user → prompt: "페이지가 수동 수정된 것 같습니다. 새 버전으로 퍼블리시할까요?"

### 7.4 Registry Schema

`draft_registry.json` entries gain:
- `page_id: string | null`
- `publish_state: string`
- Status enum adds `partial_success`.

`--resume-latest` prefers `partial_success` and `failed` over `running`.

GC policy: `partial_success` retained ≥ 3 days (not aggressively GC'd like `success`).

## 8. `/spec-update` Changes

### 8.1 Arg Surface

```
/spec-update <notion-page-url> [--feature="<name>"]
```

- URL only → re-open full PDF page's draft for editing (all toggles).
- URL + `--feature="<name>"` → edit only that feature's toggle.

Feature-name may contain spaces, parentheses, slashes (e.g. `로그인 유도 팝업(A/B)`). `--feature=<name>` form is required to avoid shell-split bugs.

### 8.2 Name → `feature_id` Resolution

1. Fetch page, extract all `<!-- feature_id: <uuid> -->` markers and their sibling titles.
2. Match name case-insensitively; on multiple matches → disambiguation prompt listing `id` + title + page.
3. If no match → error with list of available feature names.

### 8.3 Concurrent-Edit Safety

1. At session start: record page's `last_edited_time` (T0); optionally write a 5-minute soft lock comment block `<!-- editing_lock: <user@email> <iso8601> -->` at page tail.
2. User edits draft in `$EDITOR`.
3. Before publish: refetch page; compute new `last_edited_time` (T1).
   - T1 > T0 → someone else edited. Run 3-way merge:
     - Fresh page notes ← `notes_*_start/end` markers.
     - Draft notes ← user's edits.
     - If both changed the same section → prompt keep draft / keep fresh / open merge editor.
4. On publish, replace old lock comment or remove it.

The lock is **advisory** (no hard enforcement). Its presence warns other users running `/spec-update` concurrently.

### 8.4 Merge Algorithm

Per `feature_id`:

1. Extract each sub-section (`notes_ios`, `notes_android`, `notes_common`) by marker pair.
2. Draft wins on conflict; fresh-but-not-in-draft blocks are appended as "recovered" notes inside the same sub-section.
3. Blocks with no marker between toggle heading and next sentinel → treated as "stray", preserved verbatim at toggle tail with a `<!-- stray: preserved -->` wrapper.

## 9. `/spec-from-pdf` Changes (Summary)

- Produces single PDF-level page instead of N feature pages.
- Phase 2 assigns `feature_id` (UUID4) to each feature at first detection; IDs persist through Phase 2 edits (rename keeps id; merge adopts one of two, records the other in `merged_into`; split → new id for derivative).
- Phase 5 publishes to one page with chunked append.

## 9.1 `이전_버전` Relation Semantics in v2

- v2 uses the existing `이전_버전` Relation **only at the PDF-page level** (whole-page versioning).
- The `새 버전` dedup option (§5.1) creates a new PDF page with `이전_버전 = <old PDF page>`.
- Legacy Relation values on per-feature pages (from v1) are **not** carried forward by migration (those entries pointed to per-feature lineage, which is meaningless post-migration).

## 10. Migration Tool

`scripts/migrate_to_per_pdf.py`.

### 10.1 Usage

```
python3 migrate_to_per_pdf.py --dry-run   # preview; default
python3 migrate_to_per_pdf.py --apply     # write changes
```

### 10.2 Algorithm

```
1. Query DB → all pages (paginate if needed).
2. Group by PDF 해시 (primary) / filename + ±1d 생성일 (fallback for legacy pages).
3. Orphan group = pages with neither.
4. For each group:
   a. Build consolidated page content (toggle per feature).
   b. Preserve notes verbatim; insert `작성자: <user>, <date>` attribution where available.
   c. Assign fresh feature_id to each toggle (v2 id space).
   d. In dry-run: log planned output; in apply: create page.
5. On each source page, set properties:
   - migrated_to: <new_page_url>
   - archived: true
6. Emit migration-report.md in CWD with:
   - Group → new page URL mapping
   - Orphan list
   - Conflicts requiring manual action
```

### 10.3 Edge Cases

| Case | Handling |
|---|---|
| Legacy page no `PDF 해시` | Match by filename + ±1d 생성일. If ambiguous → orphan. |
| Notes on multiple per-feature pages | All notes preserved, each with author attribution. |
| Duplicate feature names across PDFs | Hash separates; fallback filename-only heuristic may conflate → flagged in report for manual split. |
| Pre-existing `이전_버전` Relation | Not carried forward. v2 chains are per-PDF. |
| Re-running migration | `archived=true` pages skipped. Idempotent. |

### 10.4 DB Schema Changes

Add via `notion-update-data-source`:
- `migrated_to` — URL property.
- `archived` — checkbox property.

Existing `이전_버전` Relation retained; v2 writes new values to it at the PDF-page level only (see §9.1).

## 11. Common Guards

### 11.1 `CLAUDE_PLUGIN_ROOT`

Both `/spec-update` and `/spec-resume` command files guard at top:

```bash
if [ -z "$CLAUDE_PLUGIN_ROOT" ]; then
  CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
```

### 11.2 `argument-hint` + `description` Updates

- `/spec-update` hint: `<notion-page-url> [--feature="<name>"]`
- `/spec-update` description: "기존 Notion 피처 페이지의 iOS/Android/공통 노트를 갱신한다. 전체 페이지 또는 특정 피처 Toggle 단위 편집 가능."
- `/spec-resume` description: "중단된 /spec-from-pdf 세션을 이어받는다. 퍼블리시 도중 중단된 부분 append 도 재개 가능."

### 11.3 feature_id Invariant

- Created during Phase 2 (first feature detection).
- Persists through: rename, reorder, Phase 2 merge (one id adopted), Phase 2 split (new id for derivative).
- Written to Notion as `<!-- feature_id: <uuid> -->` on publish; never re-generated once published.
- Migration script assigns fresh ids to legacy features (no pre-existing ids).

## 12. Test Matrix

### 12.1 Unit

- `draft_registry.py` — new fields (`page_id`, `publish_state`), status transitions including `partial_success`.
- URL → page_id extractor — fuzz with various Notion URL formats.
- feature-name → feature_id resolver — case-insensitivity, disambiguation, no-match.
- Toggle-marker extractor — parses `notes_*_start/end` correctly across nested markdown.
- Union-property computation — no stale tags after feature deletion.
- v1 draft detector — absent `publish_state` triggers legacy path.

### 12.2 Integration (MCP mocks or recorded)

- Chunked append with sentinel placement.
- Rate-limit retry with backoff.
- Fetch → edit → publish with `last_edited_time` check (happy + conflict).
- Page 404 during resume.

### 12.3 End-to-End

| Scenario | Coverage |
|---|---|
| Happy path /spec-from-pdf | full flow, 1 page with N toggles |
| Happy path /spec-update (full) | edit + publish preserves other fields |
| Happy path /spec-update (single feature) | `--feature=` edits only that toggle |
| /spec-resume — chunks_appending, valid page | resumes from sentinel |
| /spec-resume — page deleted | prompts new publish |
| /spec-resume — page manually edited (sentinels intact) | resumes |
| /spec-resume — sentinels removed | prompts new version |
| /spec-resume — v1 draft | falls back to full re-publish |
| Concurrent /spec-update — same page, full edit | 3-way merge triggers |
| Concurrent /spec-update — same feature | merge conflict prompts |
| Feature name with `(A/B)` | `--feature=` parses correctly |
| Feature renamed between /spec-from-pdf and /spec-update | resolved by feature_id |
| CLAUDE_PLUGIN_ROOT unset | guard fallback works |
| Migration dry-run | report correct, no writes |
| Migration apply | archival + idempotency |

## 13. Out of Scope

- External image hosting (S3/imgur) — stays on v0.2 roadmap. v2 continues placeholder fallback.
- DB property auto-creation — `migrated_to` / `archived` are manually added via `notion-update-data-source` during migration bootstrap.
- Rollback tooling beyond "archived=true keeps originals viewable".
- Multi-PDF aggregation into a single page — out of scope.

## 14. Open Questions

None at time of writing. All P0/P1 concerns from two independent audits were folded into this spec.

## 15. Migration Path

1. Ship v2 code (behavior flag: none — direct replacement).
2. In release notes: instruct users to run `migrate_to_per_pdf.py --dry-run` first, then `--apply`.
3. Existing per-feature pages marked `archived=true` + `migrated_to=<url>`; teams view via filter in Notion UI.
4. `/spec-update` on an archived page → error with link to `migrated_to` target.

## 16. Appendix: Critical Files

- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/SKILL.md`
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/conflict-policy.md`
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/review-format.md`
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/references/notion-schema.md`
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/draft_registry.py` — schema extension
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/migrate_to_per_pdf.py` — new
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/note_extractor.py` — new
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/note_merger.py` — new
- `/Users/chuchu/testPlugin/skills/pdf-spec-organizer/scripts/page_publisher.py` — new
- `/Users/chuchu/testPlugin/commands/spec-from-pdf.md`
- `/Users/chuchu/testPlugin/commands/spec-update.md` — arg surface, guard, description
- `/Users/chuchu/testPlugin/commands/spec-resume.md` — guard, description
