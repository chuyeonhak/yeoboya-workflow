"""Extract user-authored notes from a Notion PDF-page's markdown body.

Reads markdown from stdin. For every feature_id marker, locates its notes_ios,
notes_android, notes_common start/end blocks, and any stray (non-marker) content
between the feature start and the next feature/sentinel.

Output JSON:
{
  "features": {
    "<feature_id>": {
      "ios": "...", "ios_empty": bool,
      "android": "...", "android_empty": bool,
      "common": "...", "common_empty": bool,
      "stray": "..."
    }
  }
}
"""
import json
import re
import sys

FEATURE_ID_RE = re.compile(
    r"<!--\s*feature_id:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*-->"
)
SENTINEL_RE = re.compile(r"<!--\s*publish_sentinel:[^>]*-->")

SECTION_NAMES = ("ios", "android", "common")


def _section_re(name: str) -> re.Pattern:
    return re.compile(
        rf"<!--\s*notes_{name}_start\s*-->(.*?)<!--\s*notes_{name}_end\s*-->",
        re.DOTALL,
    )


def _is_empty(text: str) -> bool:
    # Consider empty only if it contains the explicit <empty-block/> marker
    # and nothing else meaningful
    if "<empty-block/>" in text:
        # Remove empty-block tag and check if anything remains
        stripped = re.sub(r"<empty-block/>", "", text).strip()
        return stripped == ""
    # If no empty-block tag, it's not considered empty (even if just a header)
    return False


def _strip_known_blocks(segment: str) -> str:
    out = segment
    for name in SECTION_NAMES:
        out = _section_re(name).sub("", out)
    out = SENTINEL_RE.sub("", out)
    out = FEATURE_ID_RE.sub("", out)
    return out.strip()


def extract(text: str) -> dict:
    result = {"features": {}}
    # Split body into chunks at each feature_id marker
    positions = [(m.start(), m.group(1)) for m in FEATURE_ID_RE.finditer(text)]
    positions.append((len(text), None))  # sentinel

    for i in range(len(positions) - 1):
        start, fid = positions[i]
        end = positions[i + 1][0]
        segment = text[start:end]
        feat = {}
        for name in SECTION_NAMES:
            m = _section_re(name).search(segment)
            content = m.group(1).strip() if m else ""
            is_empty = _is_empty(content)
            # If marked as empty, strip the empty-block tag and clear content
            if is_empty:
                content = re.sub(r"<empty-block/>", "", content).strip()
            feat[name] = content
            feat[f"{name}_empty"] = is_empty
        # stray = everything except feature_id marker, note sections, sentinels, and the first line after feature_id
        stray = _strip_known_blocks(segment)
        feat["stray"] = stray
        result["features"][fid] = feat
    return result


def main() -> int:
    text = sys.stdin.read()
    json.dump(extract(text), sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
