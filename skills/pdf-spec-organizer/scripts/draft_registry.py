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
    return Path.home() / ".claude-plugin-data" / "yeoboya-work-flow" / "draft-registry.json"


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
    # 공통 부모 파서: 모든 서브파서에 --registry 공유
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--registry", type=Path, default=default_registry())

    parser = argparse.ArgumentParser(parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record", parents=[common])
    p_rec.add_argument("--hash", required=True)
    p_rec.add_argument("--draft-path", required=True)
    p_rec.add_argument("--status", required=True, choices=["running", "success", "failed"])
    p_rec.add_argument("--ttl-seconds", type=int, default=None)
    p_rec.set_defaults(func=cmd_record)

    p_q = sub.add_parser("query-recent", parents=[common])
    p_q.add_argument("--hash", required=True)
    p_q.add_argument("--within-seconds", type=int, required=True)
    p_q.set_defaults(func=cmd_query_recent)

    p_l = sub.add_parser("list-latest", parents=[common])
    p_l.add_argument("--count", type=int, default=5)
    p_l.set_defaults(func=cmd_list_latest)

    p_g = sub.add_parser("gc", parents=[common])
    p_g.set_defaults(func=cmd_gc)

    p_u = sub.add_parser("update-status", parents=[common])
    p_u.add_argument("--draft-path", required=True)
    p_u.add_argument("--status", required=True, choices=["running", "success", "failed"])
    p_u.set_defaults(func=cmd_update_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
