"""Layer-2 integration tests for `after_migrate` loader.

Stages JSON fixtures under a tempdir, points the loader at it via the
`app_paths` parameter, calls `import_split_fixtures`, asserts records appear
/ are restored / are idempotent in the real Frappe DB.

We pass `app_paths` explicitly rather than mocking `frappe.get_installed_apps`
because frappe's own machinery (controllers, modules) consults the installed
apps list during `import_doc`. Mocking it globally during a test causes
"App erpnext is not installed" failures.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import frappe

from frappe_fixture_normalize.loader import import_split_fixtures
from frappe_fixture_normalize.tests._compat import IntegrationTestCase


def _custom_field_record(name: str, fieldname: str) -> dict:
    return {
        "doctype": "Custom Field",
        "name": name,
        "dt": "DocType",
        "fieldname": fieldname,
        "fieldtype": "Data",
        "label": fieldname.replace("_", " ").title(),
        "module": "Frappe Fixture Normalize",
    }


def _delete_if_exists(name: str) -> None:
    if frappe.db.exists("Custom Field", name):
        try:
            frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            pass


class TestLoaderHook(IntegrationTestCase):
    def setUp(self) -> None:
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self) -> None:
        for name in self._created:
            _delete_if_exists(name)

    def _stage_app(self, td: Path, records: list[dict]) -> Path:
        sub = td / "fixtures" / "custom_field"
        sub.mkdir(parents=True)
        path = sub / "doctype.json"
        path.write_text(json.dumps(records, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        return path

    def test_migrate_restores_deleted_record(self):
        fieldname = f"ffn_loader_restore_{uuid.uuid4().hex[:8]}"
        cf_name = f"DocType-{fieldname}"
        self._created.append(cf_name)

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._stage_app(tdp, [_custom_field_record(cf_name, fieldname)])
            _delete_if_exists(cf_name)
            self.assertFalse(frappe.db.exists("Custom Field", cf_name))

            import_split_fixtures(app_paths=[tdp])

            self.assertTrue(frappe.db.exists("Custom Field", cf_name))

    def test_migrate_twice_no_duplicates_no_errors(self):
        fieldname = f"ffn_loader_idem_{uuid.uuid4().hex[:8]}"
        cf_name = f"DocType-{fieldname}"
        self._created.append(cf_name)

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._stage_app(tdp, [_custom_field_record(cf_name, fieldname)])
            _delete_if_exists(cf_name)

            import_split_fixtures(app_paths=[tdp])
            import_split_fixtures(app_paths=[tdp])

            count = frappe.db.count("Custom Field", {"name": cf_name})
            self.assertEqual(count, 1)

    def test_corrupted_split_file_logs_warning_and_continues(self):
        fieldname = f"ffn_loader_resilient_{uuid.uuid4().hex[:8]}"
        cf_name = f"DocType-{fieldname}"
        self._created.append(cf_name)

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            sub = tdp / "fixtures" / "custom_field"
            sub.mkdir(parents=True)
            (sub / "broken.json").write_text("{not json")
            good_path = sub / "doctype.json"
            good_path.write_text(json.dumps([_custom_field_record(cf_name, fieldname)]))

            _delete_if_exists(cf_name)

            import_split_fixtures(app_paths=[tdp])  # must not raise

            self.assertTrue(frappe.db.exists("Custom Field", cf_name))

    def test_empty_app_path_is_noop(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # no fixtures dir at all
            import_split_fixtures(app_paths=[tdp])  # must not raise

    def test_default_discovers_installed_apps(self):
        """When `app_paths` is None, the loader pulls from
        `frappe.get_installed_apps`. Running on a real bench should iterate
        without error (records may or may not be imported depending on app
        state, but the call must succeed)."""
        import_split_fixtures()  # uses frappe.get_installed_apps under the hood
