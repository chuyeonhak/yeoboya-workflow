import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent


def run_merge(draft_path, notes_path):
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "note_merger.py"),
         "--draft", str(draft_path), "--notes", str(notes_path)],
        capture_output=True, text=True,
    )


def test_merge_injects_preserved_notes_into_matching_feature(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- notes_ios_start -->
<empty-block/>
<!-- notes_ios_end -->

<!-- notes_android_start -->
<empty-block/>
<!-- notes_android_end -->

<!-- notes_common_start -->
<empty-block/>
<!-- notes_common_end -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                "ios": "preserved iOS text", "ios_empty": False,
                "android": "", "android_empty": True,
                "common": "preserved common", "common_empty": False,
                "stray": "",
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "preserved iOS text" in merged
    assert "preserved common" in merged
    # empty sections stay as <empty-block/> placeholder
    assert merged.count("<empty-block/>") == 1  # only android remains empty


def test_merge_orphans_preserved_notes_for_removed_features(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "ccccccccc-cccc-4ccc-8ccc-cccccccccccc": {
                "ios": "orphan iOS note", "ios_empty": False,
                "android": "", "android_empty": True,
                "common": "", "common_empty": True,
                "stray": "",
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "이전 노트" in merged
    assert "orphan iOS note" in merged


def test_merge_preserves_stray_blocks_at_toggle_tail(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- notes_ios_start -->
<empty-block/>
<!-- notes_ios_end -->

<!-- notes_android_start -->
<empty-block/>
<!-- notes_android_end -->

<!-- notes_common_start -->
<empty-block/>
<!-- notes_common_end -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                "ios": "", "ios_empty": True,
                "android": "", "android_empty": True,
                "common": "", "common_empty": True,
                "stray": "manual user addition",
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "<!-- stray: preserved -->" in merged
    assert "manual user addition" in merged


def test_merge_injects_preserved_meta_section(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- meta_start -->
<empty-block/>
<!-- meta_end -->

<!-- notes_ios_start -->
<empty-block/>
<!-- notes_ios_end -->

<!-- notes_android_start -->
<empty-block/>
<!-- notes_android_end -->

<!-- notes_common_start -->
<empty-block/>
<!-- notes_common_end -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                "ios": "", "ios_empty": True,
                "android": "", "android_empty": True,
                "common": "", "common_empty": True,
                "stray": "",
                "meta": "**예상 기간:** iOS 2일", "meta_empty": False,
            }
        }
    }))
    r = run_merge(draft, notes)
    assert r.returncode == 0, r.stderr
    merged = draft.read_text()
    assert "**예상 기간:** iOS 2일" in merged


def test_merge_leaves_empty_meta_as_placeholder(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""
### 1. Foo
<!-- feature_id: aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa -->
body

<!-- meta_start -->
<empty-block/>
<!-- meta_end -->
""")
    notes = tmp_path / "notes.json"
    notes.write_text(json.dumps({
        "features": {
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa": {
                "ios": "", "ios_empty": True,
                "android": "", "android_empty": True,
                "common": "", "common_empty": True,
                "stray": "",
                "meta": "", "meta_empty": True,
            }
        }
    }))
    r = run_merge(draft, notes)
    merged = draft.read_text()
    # meta block remains as empty-block placeholder
    assert "<!-- meta_start -->" in merged
    assert "<!-- meta_end -->" in merged
    assert "<empty-block/>" in merged
