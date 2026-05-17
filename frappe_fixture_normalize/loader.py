"""after_migrate hook: import split-fixture files written under
`<app>/fixtures/<scrub(doctype)>/*.json` by `bench export-clean-fixtures`.

Frappe's stock `sync_fixtures` only globs top-level `fixtures/*.json`, so split
subdirectories are invisible to it. This hook walks every installed app and
imports each record file via the same path-based importer used by sync_fixtures
itself, keeping behavior identical (idempotent insert/update, ignore on duplicate
errors).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path


def iter_split_fixture_files(app_path: Path) -> Iterator[Path]:
    """Yield every `<fixtures>/<subdir>/*.json` under an installed app, deterministic order.

    Pure: no Frappe imports, takes a filesystem path.
    """
    fixtures_root = app_path / "fixtures"
    if not fixtures_root.is_dir():
        return
    for subdir in sorted(fixtures_root.iterdir()):
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.glob("*.json")):
            yield path


def import_split_fixtures() -> None:
    """Frappe `after_migrate` hook entry point."""
    import frappe
    from frappe.core.doctype.data_import.data_import import import_doc

    for app in frappe.get_installed_apps():
        try:
            app_path = Path(frappe.get_app_path(app))
        except Exception:
            continue
        for path in iter_split_fixture_files(app_path):
            try:
                import_doc(str(path))
            except Exception as e:
                frappe.logger().warning(
                    f"frappe_fixture_normalize: failed importing {path}: {e}"
                )
