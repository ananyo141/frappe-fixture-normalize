"""Pre-commit hook: re-normalize fixture JSON files in place.

Usage:
    python -m frappe_fixture_normalize.pre_commit_hook path/to/file.json [more.json ...]

Exit codes:
    0 — all files already canonical (no changes written)
    1 — at least one file was rewritten or failed to parse
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from frappe_fixture_normalize.normalizer import canonical_dump, normalize_records


def process_file(path: Path) -> tuple[bool, str | None]:
    """Return (changed, error_message).

    `changed` is True if the file's bytes on disk differ after normalization.
    `error_message` is non-None when the file could not be processed.
    """
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"{path}: read failed: {e}"

    try:
        data = json.loads(original)
    except json.JSONDecodeError as e:
        return False, f"{path}: invalid JSON: {e}"

    if not isinstance(data, list):
        return False, None

    try:
        normalized = normalize_records(data)
    except (KeyError, ValueError) as e:
        return False, f"{path}: normalization failed: {e}"

    new_text = canonical_dump(normalized)
    if new_text == original:
        return False, None

    path.write_text(new_text, encoding="utf-8")
    return True, None


def main(argv: list[str]) -> int:
    exit_code = 0
    for arg in argv:
        path = Path(arg)
        changed, error = process_file(path)
        if error:
            print(error, file=sys.stderr)
            exit_code = 1
        elif changed:
            print(f"normalized {path}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
