"""Merge extracted notes into a draft.md so user-authored content is preserved.

Usage:
  note_merger.py --draft DRAFT_PATH --notes NOTES_JSON_PATH

Rewrites DRAFT_PATH in place:
  - For each feature_id present in both notes and draft:
    - Replace notes_ios / notes_android / notes_common sections with preserved
      text (if not empty). Empty sections stay as <empty-block/> placeholder.
  - Append stray content at end of matching toggle under a
    <!-- stray: preserved --> wrapper.
  - feature_ids present in notes but missing from draft → append an
    "이전 노트 (제거된 피처)" section at end of file with preserved text.
"""
import argparse
import json
import re
from pathlib import Path

SECTION_NAMES = ("ios", "android", "common")


def _replace_section(segment: str, name: str, new_inner: str) -> str:
    pat = re.compile(
        rf"(<!--\s*notes_{name}_start\s*-->)(.*?)(<!--\s*notes_{name}_end\s*-->)",
        re.DOTALL,
    )
    replacement = f"\\1\n{new_inner}\n\\3" if new_inner.strip() else "\\1\n<empty-block/>\n\\3"
    return pat.sub(replacement, segment, count=1)


def _find_feature_positions(text: str):
    fid_re = re.compile(
        r"<!--\s*feature_id:\s*([0-9a-fA-F-]{36})\s*-->"
    )
    return [(m.start(), m.end(), m.group(1)) for m in fid_re.finditer(text)]


def merge(draft: str, notes: dict) -> str:
    positions = _find_feature_positions(draft)
    positions_sorted = sorted(positions, key=lambda p: p[0])
    segments = []
    last = 0
    for i, (start, end, fid) in enumerate(positions_sorted):
        prev_text = draft[last:start]
        next_start = positions_sorted[i + 1][0] if i + 1 < len(positions_sorted) else len(draft)
        feat_segment = draft[start:next_start]
        n = notes.get("features", {}).get(fid)
        if n:
            for name in SECTION_NAMES:
                if not n.get(f"{name}_empty", True):
                    feat_segment = _replace_section(feat_segment, name, n[name])
            if n.get("stray", "").strip():
                # Append stray at the very end of the feature segment
                feat_segment = feat_segment.rstrip() + (
                    "\n\n<!-- stray: preserved -->\n" + n["stray"].strip() + "\n"
                )
        segments.append(prev_text + feat_segment)
        last = next_start
    merged = "".join(segments) + draft[last:]

    # Orphan notes: features in notes but not in draft
    in_draft = {fid for _, _, fid in positions_sorted}
    orphan_ids = [fid for fid in notes.get("features", {}) if fid not in in_draft]
    if orphan_ids:
        merged = merged.rstrip() + "\n\n## 이전 노트 (제거된 피처)\n"
        for fid in orphan_ids:
            feat = notes["features"][fid]
            merged += f"\n### feature_id: {fid}\n"
            for name in SECTION_NAMES:
                if not feat.get(f"{name}_empty", True):
                    merged += f"\n**{name}:**\n{feat[name].strip()}\n"
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--notes", required=True)
    args = ap.parse_args()

    draft_path = Path(args.draft)
    notes = json.loads(Path(args.notes).read_text())
    merged = merge(draft_path.read_text(), notes)
    draft_path.write_text(merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
