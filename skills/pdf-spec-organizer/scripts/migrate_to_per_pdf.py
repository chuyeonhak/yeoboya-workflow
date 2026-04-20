"""Plan migration from per-feature pages to per-PDF pages.

Dry-run is the default and safest mode: it reads a JSON dump of the current
DB's feature pages (as produced by the SKILL orchestration layer via
notion-search + notion-fetch) and outputs a plan. Apply mode is NOT implemented
here — the SKILL.md is responsible for executing the plan via MCP tool calls,
so this script's job ends with a deterministic plan.

Input (--pages-file PATH):
{
  "pages": [
    {
      "id": "<notion page id>",
      "title": "<feature name>",
      "properties": {
        "PDF 해시": "<12-char hash or ''>",
        "원본 PDF": "<filename or ''>",
        "플랫폼": ["iOS", "Android", "공통"],
        "누락 항목": ["error_cases", ...],
        "archived": bool
      },
      "content": "<markdown body>",
      "last_edited_time": "<iso8601>"
    },
    ...
  ]
}

Output (stdout JSON):
{
  "groups": [
    {
      "pdf_hash": "<hash or null>",
      "pdf_filename": "<filename>",
      "match_mode": "hash" | "filename+date",
      "source_page_ids": ["p1", "p2"],
      "union_platform": [...],
      "union_missing": [...],
      "features": [{id, name, platform, content}, ...]
    }
  ],
  "orphans": [{"id", "title", "reason"}, ...],
  "skipped_archived": <int>
}

Also writes a human-readable report to --report PATH.
"""
import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path


def _iso_to_date(s: str) -> dt.date | None:
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _group_by_hash(pages: list[dict]):
    by_hash: dict[str, list[dict]] = defaultdict(list)
    remaining: list[dict] = []
    for p in pages:
        h = p["properties"].get("PDF 해시", "").strip()
        if h:
            by_hash[h].append(p)
        else:
            remaining.append(p)
    return by_hash, remaining


def _group_by_filename_date(pages: list[dict]):
    """Group pages lacking hash by (filename, ±1-day window)."""
    groups: list[list[dict]] = []
    orphans: list[dict] = []
    # bucket by filename first
    by_fn: dict[str, list[dict]] = defaultdict(list)
    for p in pages:
        fn = p["properties"].get("원본 PDF", "").strip()
        if not fn:
            orphans.append({"id": p["id"], "title": p["title"],
                            "reason": "no PDF 해시 and no 원본 PDF"})
            continue
        by_fn[fn].append(p)

    for fn, items in by_fn.items():
        # sort by last_edited_time; cluster into windows ±1 day
        items.sort(key=lambda x: x.get("last_edited_time", ""))
        current: list[dict] = []
        for p in items:
            d = _iso_to_date(p.get("last_edited_time", ""))
            if not current:
                current = [p]
                continue
            prev_d = _iso_to_date(current[-1].get("last_edited_time", ""))
            if d and prev_d and abs((d - prev_d).days) <= 1:
                current.append(p)
            else:
                groups.append(current)
                current = [p]
        if current:
            groups.append(current)

    return groups, orphans


def _build_group_record(pages: list[dict], match_mode: str, pdf_hash: str | None) -> dict:
    union_platform = sorted({pl for p in pages for pl in p["properties"].get("플랫폼", [])})
    union_missing = sorted({m for p in pages for m in p["properties"].get("누락 항목", [])})
    features = []
    for p in pages:
        features.append({
            "id": p["id"],
            "name": p["title"],
            "platform": p["properties"].get("플랫폼", []),
            "missing": p["properties"].get("누락 항목", []),
            "content": p.get("content", ""),
            "last_edited_time": p.get("last_edited_time", ""),
        })
    return {
        "pdf_hash": pdf_hash,
        "pdf_filename": pages[0]["properties"].get("원본 PDF", ""),
        "match_mode": match_mode,
        "source_page_ids": sorted(p["id"] for p in pages),
        "union_platform": union_platform,
        "union_missing": union_missing,
        "features": features,
    }


def plan(pages: list[dict]) -> dict:
    live = [p for p in pages if not p["properties"].get("archived")]
    skipped = len(pages) - len(live)

    by_hash, remaining = _group_by_hash(live)
    groups: list[dict] = []
    for h, items in by_hash.items():
        groups.append(_build_group_record(items, "hash", h))

    fn_groups, orphans = _group_by_filename_date(remaining)
    for items in fn_groups:
        groups.append(_build_group_record(items, "filename+date", None))

    return {"groups": groups, "orphans": orphans, "skipped_archived": skipped}


def render_report(planned: dict) -> str:
    lines = ["# Migration Plan", ""]
    lines.append(f"Groups: {len(planned['groups'])}")
    lines.append(f"Orphans: {len(planned['orphans'])}")
    lines.append(f"Skipped (archived): {planned['skipped_archived']}")
    lines.append("")
    lines.append("## Groups")
    for i, g in enumerate(planned["groups"], 1):
        lines.append(f"### Group {i}")
        lines.append(f"- match_mode: `{g['match_mode']}`")
        lines.append(f"- pdf_hash: `{g['pdf_hash'] or '(none)'}`")
        lines.append(f"- pdf_filename: {g['pdf_filename']}")
        lines.append(f"- source pages: {', '.join(g['source_page_ids'])}")
        lines.append(f"- union 플랫폼: {', '.join(g['union_platform'])}")
        lines.append(f"- union 누락: {', '.join(g['union_missing'])}")
        lines.append("- features:")
        for f in g["features"]:
            lines.append(f"  - {f['name']} ({', '.join(f['platform']) or '-'})")
        lines.append("")
    if planned["orphans"]:
        lines.append("## Orphans (manual action required)")
        for o in planned["orphans"]:
            lines.append(f"- `{o['id']}` {o['title']} — {o['reason']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-file", required=True)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.pages_file).read_text())
    planned = plan(data["pages"])

    # Always emit report + JSON
    Path(args.report).write_text(render_report(planned), encoding="utf-8")
    json.dump(planned, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
