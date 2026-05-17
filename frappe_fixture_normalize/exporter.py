"""Post-process fixture files written by `bench export-fixtures`.

Walks a single app's `fixtures/` directory, normalizes each JSON file, and for
any doctype configured in `split_by_config` rewrites the flat file as one file
per target value under `fixtures/<scrub(doctype)>/<scrub(target)>.json`.

`process_app_fixtures_dir` is pure (filesystem-only, no Frappe import) so it
can be unit-tested without a bench. The Frappe-coupled CLI wrapper lives in
`commands.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from frappe_fixture_normalize.normalizer import canonical_dump, normalize_records
from frappe_fixture_normalize.splitter import scrub_filename, split_records_by


def _read_records(path: Path) -> list[dict] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, list):
        return None
    return data


def _collect_records_for_doctype(
    fixtures_dir: Path,
    doctype: str,
    flat_name: str,
) -> list[dict] | None:
    """Read records for a doctype from either the flat file or its split subdir.

    Returns None if neither source exists. The flat file takes precedence —
    if it's present, the split subdir is treated as stale output to be replaced.
    """
    flat_path = fixtures_dir / f"{flat_name}.json"
    sub_dir = fixtures_dir / flat_name

    if flat_path.is_file():
        return _read_records(flat_path)

    if sub_dir.is_dir():
        collected: list[dict] = []
        for child in sorted(sub_dir.glob("*.json")):
            records = _read_records(child)
            if records:
                collected.extend(records)
        return collected if collected else None

    return None


def process_app_fixtures_dir(
    fixtures_dir: Path,
    split_by_config: dict[str, str],
) -> None:
    """Normalize every fixture file under `fixtures_dir`, splitting where configured."""

    if not fixtures_dir.is_dir():
        return

    seen_doctypes: set[str] = set()

    # First pass: handle each doctype that has a split rule. We look for either
    # a flat file or an existing split subdir.
    for doctype, split_field in split_by_config.items():
        flat_name = scrub_filename(doctype)
        records = _collect_records_for_doctype(fixtures_dir, doctype, flat_name)
        if records is None:
            continue
        seen_doctypes.add(flat_name)
        _write_split(fixtures_dir, flat_name, records, split_field)

    # Second pass: any remaining flat `*.json` files get normalized in place.
    for path in sorted(fixtures_dir.glob("*.json")):
        if path.stem in seen_doctypes:  # pragma: no cover - defensive; pass 1 unlinks the flat
            continue
        records = _read_records(path)
        if records is None:
            continue
        normalized = normalize_records(records)
        path.write_text(canonical_dump(normalized), encoding="utf-8")


def _write_split(
    fixtures_dir: Path,
    flat_name: str,
    records: list[dict],
    split_field: str,
) -> None:
    normalized = normalize_records(records)
    groups = split_records_by(normalized, field=split_field)

    target_dir = fixtures_dir / flat_name
    target_dir.mkdir(exist_ok=True)

    # Wipe old split files so records that moved targets or got deleted don't linger.
    for stale in target_dir.glob("*.json"):
        stale.unlink()

    for target, group in groups.items():
        out_path = target_dir / f"{scrub_filename(target)}.json"
        # Each group is already sorted (parent list was sorted); regroup is stable.
        out_path.write_text(canonical_dump(group), encoding="utf-8")

    # Remove the flat file if it existed.
    flat_path = fixtures_dir / f"{flat_name}.json"
    if flat_path.is_file():
        flat_path.unlink()
