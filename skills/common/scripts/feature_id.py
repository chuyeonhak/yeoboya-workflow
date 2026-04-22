"""Feature ID generation and resolution.

Subcommands:
  assign            --features-file PATH
                    Assign UUID4 feature_id to every feature missing one.
  resolve           --features-file PATH --name NAME
                    Resolve a feature name (case-insensitive) to its feature_id.
                    Exits non-zero on no-match or ambiguous match.
  extract-from-stdin
                    Read markdown from stdin, extract all
                    <!-- feature_id: <uuid> --> values, print as JSON list.
"""
import argparse
import json
import re
import sys
import uuid
from pathlib import Path

FEATURE_ID_MARKER_RE = re.compile(
    r"<!--\s*feature_id:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*-->"
)


def cmd_assign(args) -> int:
    path = Path(args.features_file)
    data = json.loads(path.read_text())
    changed = False
    for f in data.get("features", []):
        if not f.get("feature_id"):
            f["feature_id"] = str(uuid.uuid4())
            changed = True
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    json.dump({"changed": changed}, sys.stdout)
    return 0


def cmd_resolve(args) -> int:
    path = Path(args.features_file)
    data = json.loads(path.read_text())
    target = args.name.strip().lower()
    matches = [
        f for f in data.get("features", [])
        if f.get("name", "").strip().lower() == target
    ]
    if not matches:
        print(f"ERROR: feature name not found: {args.name!r}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        lines = ["ERROR: ambiguous name; candidates:"]
        for m in matches:
            lines.append(f"  {m.get('feature_id', '<no-id>')}  {m.get('name')}")
        print("\n".join(lines), file=sys.stderr)
        return 1
    f = matches[0]
    json.dump({"feature_id": f["feature_id"], "name": f["name"]}, sys.stdout)
    return 0


def cmd_extract_from_stdin(args) -> int:
    text = sys.stdin.read()
    ids = FEATURE_ID_MARKER_RE.findall(text)
    json.dump({"feature_ids": ids}, sys.stdout)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_a = sub.add_parser("assign")
    p_a.add_argument("--features-file", required=True)
    p_a.set_defaults(func=cmd_assign)

    p_r = sub.add_parser("resolve")
    p_r.add_argument("--features-file", required=True)
    p_r.add_argument("--name", required=True)
    p_r.set_defaults(func=cmd_resolve)

    p_e = sub.add_parser("extract-from-stdin")
    p_e.set_defaults(func=cmd_extract_from_stdin)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
