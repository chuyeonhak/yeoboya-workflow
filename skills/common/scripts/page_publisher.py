"""Prepare chunked block payloads for Notion publish + sentinel-based resume.

Subcommands:
  chunk --input MD_PATH --max-blocks N
    Split a markdown body into chunks no larger than N blocks. Output:
      {"chunks": [{"index": 0, "block_count": 42, "markdown": "..."}, ...]}
    Each chunk's markdown ends with a `<!-- publish_sentinel: chunk_<N>_done -->`
    line. Chunk boundaries never split inside a toggle (tab-indented children).

  find-sentinel --input MD_PATH
    Scan body content for `<!-- publish_sentinel: chunk_N_done -->` markers.
    Output: {"last_chunk_index": <int-or--1>, "complete": <bool>}
"""
import argparse
import json
import re
import sys
from pathlib import Path

SENTINEL_DONE_RE = re.compile(r"<!--\s*publish_sentinel:\s*chunk_(\d+)_done\s*-->")
SENTINEL_COMPLETE_RE = re.compile(r"<!--\s*publish_sentinel:\s*complete\s*-->")


def _count_blocks(markdown: str) -> int:
    """Rough estimate: one block per non-empty, non-indented line."""
    lines = [l for l in markdown.splitlines() if l.strip()]
    return len(lines)


def _split_lines(markdown: str):
    """Yield (line, is_toggle_child) pairs preserving original text."""
    for line in markdown.splitlines(keepends=True):
        yield line, line.startswith("\t")


def chunk_markdown(markdown: str, max_blocks: int) -> list[dict]:
    chunks = []
    current: list[str] = []
    current_count = 0
    in_toggle = False

    for line, is_child in _split_lines(markdown):
        if is_child:
            in_toggle = True
        else:
            # non-indented line — safe boundary if current is big enough
            # Account for sentinel (1 extra block) when deciding to split
            if current and current_count >= max_blocks - 1 and not in_toggle:
                chunks.append("".join(current))
                current = []
                current_count = 0
            in_toggle = False
        current.append(line)
        if line.strip():
            current_count += 1

    if current:
        chunks.append("".join(current))

    annotated = []
    for i, ch in enumerate(chunks):
        sentinel = f"\n\n<!-- publish_sentinel: chunk_{i}_done -->\n"
        full = ch.rstrip() + sentinel
        annotated.append({
            "index": i,
            "block_count": _count_blocks(full),
            "markdown": full,
        })
    return annotated


def cmd_chunk(args) -> int:
    text = Path(args.input).read_text()
    chunks = chunk_markdown(text, args.max_blocks)
    json.dump({"chunks": chunks}, sys.stdout, ensure_ascii=False)
    return 0


def cmd_find_sentinel(args) -> int:
    text = Path(args.input).read_text()
    complete = bool(SENTINEL_COMPLETE_RE.search(text))
    indices = [int(m.group(1)) for m in SENTINEL_DONE_RE.finditer(text)]
    last = max(indices) if indices else -1
    json.dump({"last_chunk_index": last, "complete": complete}, sys.stdout)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_c = sub.add_parser("chunk")
    p_c.add_argument("--input", required=True)
    p_c.add_argument("--max-blocks", type=int, default=80)
    p_c.set_defaults(func=cmd_chunk)

    p_s = sub.add_parser("find-sentinel")
    p_s.add_argument("--input", required=True)
    p_s.set_defaults(func=cmd_find_sentinel)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
