#!/usr/bin/env python3
"""Synchronize project version files before semantic-release creates a tag."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    content = path.read_text()
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Could not update version in {path}")
    path.write_text(updated)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_release.py VERSION")

    version = sys.argv[1]
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise SystemExit(f"invalid version: {version}")

    replace_once(
        ROOT / "pyproject.toml",
        r'^version = "[^"]+"$',
        f'version = "{version}"',
    )
    replace_once(
        ROOT / "src" / "scrolllock_led_daemon.py",
        r'^VERSION = "[^"]+"$',
        f'VERSION = "{version}"',
    )

    changelog = ROOT / "debian" / "changelog"
    previous = changelog.read_text()
    timestamp = format_datetime(datetime.now().astimezone())
    entry = (
        f"scrolllock-led-daemon ({version}-1) noble; urgency=medium\n\n"
        f"  * Automated release {version}.\n\n"
        f" -- Alan Santos <alan.profissional.dev@gmail.com>  {timestamp}\n\n"
    )
    changelog.write_text(entry + previous)


if __name__ == "__main__":
    main()
