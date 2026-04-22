"""Common scripts 경로를 sys.path 에 주입한다.

이 모듈을 import 하는 것만으로 common/scripts/ 의 모듈을 import 할 수 있게 된다.
import 순서: `_path_setup` 을 반드시 `from X import Y` 보다 먼저 호출해야 한다.

사용 예:
    from _path_setup import COMMON_SCRIPTS_DIR  # noqa: F401
    from pii_scan import scan_text              # common/scripts/pii_scan.py
"""
import sys
from pathlib import Path

COMMON_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "common" / "scripts"
)

if str(COMMON_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_SCRIPTS_DIR))

if not COMMON_SCRIPTS_DIR.exists():
    raise ImportError(
        f"common/scripts/ not found at {COMMON_SCRIPTS_DIR}. "
        f"plugin installation may be broken."
    )
