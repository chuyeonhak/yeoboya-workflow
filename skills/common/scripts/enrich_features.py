"""Feature metadata enrichment helper for pdf-spec-organizer.

Two subcommands:

  load-context --path <project-context.md>
    Loads a project-context.md, truncates at 500 lines, and emits JSON
    describing the content. Used by SKILL.md's Phase 3.5-a.

  merge-metadata --features-file <features.json> --metadata <meta.json>
    Merges a Claude-generated metadata map into features.json. Accepts
    malformed metadata JSON and falls back to an empty metadata shape
    per affected feature so Phase 4 can continue.

The Explore subagent orchestration and the Claude metadata-generation
prompt live in SKILL.md — this script handles filesystem I/O only.
"""
import argparse
import json
import sys
from pathlib import Path

EMPTY_METADATA = {
    "estimated_effort": "",
    "external_dependencies": [],
    "planning_gaps": [],
    "cross_team_requests": [],
}

MAX_CONTEXT_LINES = 500


def cmd_load_context(args) -> int:
    path = Path(args.path).expanduser()
    if not path.exists():
        print(json.dumps({"skip": True, "reason": "not_found", "path": str(path)}, ensure_ascii=False))
        return 0
    raw = path.read_text()
    if not raw.strip():
        print(json.dumps({"skip": True, "reason": "empty", "path": str(path)}, ensure_ascii=False))
        return 0
    lines = raw.splitlines()
    truncated = len(lines) > MAX_CONTEXT_LINES
    kept = lines[:MAX_CONTEXT_LINES]
    print(json.dumps({
        "skip": False,
        "truncated": truncated,
        "line_count": len(kept),
        "total_line_count": len(lines),
        "content": "\n".join(kept),
        "path": str(path),
    }, ensure_ascii=False))
    return 0


def _parse_metadata(meta_text: str) -> tuple[dict, bool]:
    """Return (metadata_map, parsed_ok). On failure returns ({}, False)."""
    try:
        data = json.loads(meta_text)
    except json.JSONDecodeError:
        return {}, False
    if not isinstance(data, dict):
        return {}, False
    return data, True


def _normalise_entry(raw) -> dict:
    if not isinstance(raw, dict):
        return dict(EMPTY_METADATA)
    out = dict(EMPTY_METADATA)
    if isinstance(raw.get("estimated_effort"), str):
        out["estimated_effort"] = raw["estimated_effort"]
    if isinstance(raw.get("external_dependencies"), list):
        out["external_dependencies"] = raw["external_dependencies"]
    if isinstance(raw.get("planning_gaps"), list):
        out["planning_gaps"] = raw["planning_gaps"]
    if isinstance(raw.get("cross_team_requests"), list):
        out["cross_team_requests"] = raw["cross_team_requests"]
    return out


def cmd_merge_metadata(args) -> int:
    features_path = Path(args.features_file).expanduser()
    meta_path = Path(args.metadata).expanduser()
    features = json.loads(features_path.read_text())
    meta_text = meta_path.read_text() if meta_path.exists() else ""
    meta_map, parsed_ok = _parse_metadata(meta_text)
    touched = 0
    fallback = 0
    for feat in features.get("features", []):
        if feat.get("excluded"):
            continue
        fid = feat.get("feature_id")
        if not fid:
            continue
        if parsed_ok and fid in meta_map:
            feat["metadata"] = _normalise_entry(meta_map[fid])
            touched += 1
        else:
            feat["metadata"] = dict(EMPTY_METADATA)
            fallback += 1
    features_path.write_text(json.dumps(features, ensure_ascii=False, indent=2))
    print(json.dumps({
        "parsed_ok": parsed_ok,
        "touched": touched,
        "fallback": fallback,
    }, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="enrich_features")
    sub = ap.add_subparsers(dest="cmd", required=True)

    lc = sub.add_parser("load-context")
    lc.add_argument("--path", required=True)
    lc.set_defaults(func=cmd_load_context)

    mm = sub.add_parser("merge-metadata")
    mm.add_argument("--features-file", required=True)
    mm.add_argument("--metadata", required=True)
    mm.set_defaults(func=cmd_merge_metadata)

    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
