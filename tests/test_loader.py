import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frappe_fixture_normalize.loader import iter_split_fixture_files


def test_iter_yields_paths_under_subdirs_only(tmp_path):
    fixtures = tmp_path / "fixtures"
    (fixtures / "custom_field").mkdir(parents=True)
    (fixtures / "property_setter").mkdir(parents=True)
    flat = fixtures / "workflow.json"
    flat.write_text("[]")
    a = fixtures / "custom_field" / "issue.json"
    b = fixtures / "custom_field" / "subscription.json"
    c = fixtures / "property_setter" / "issue.json"
    for p in (a, b, c):
        p.write_text("[]")

    paths = sorted(iter_split_fixture_files(tmp_path))
    assert paths == sorted([a, b, c])


def test_iter_returns_empty_when_no_fixtures_dir(tmp_path):
    assert list(iter_split_fixture_files(tmp_path)) == []


def test_iter_skips_non_json_files(tmp_path):
    sub = tmp_path / "fixtures" / "custom_field"
    sub.mkdir(parents=True)
    (sub / "issue.json").write_text("[]")
    (sub / "README.md").write_text("notes")
    paths = list(iter_split_fixture_files(tmp_path))
    assert all(p.suffix == ".json" for p in paths)
    assert len(paths) == 1


def test_iter_deterministic_order(tmp_path):
    sub = tmp_path / "fixtures" / "custom_field"
    sub.mkdir(parents=True)
    for n in ["zeta", "alpha", "mu"]:
        (sub / f"{n}.json").write_text("[]")
    paths = list(iter_split_fixture_files(tmp_path))
    assert [p.name for p in paths] == ["alpha.json", "mu.json", "zeta.json"]


# --- import_split_fixtures: frappe-stubbed coverage --------------------------
#
# The loader's `import frappe` and `import_doc` calls are deferred to function
# body, so we stub them via sys.modules just for the call. Each test sets up
# a fake frappe module, invokes the hook, and asserts behavior.


import importlib  # noqa: E402
import json as _json  # noqa: E402
import types  # noqa: E402
from unittest import mock  # noqa: E402


def _install_fake_frappe(monkeypatch, *, installed_apps, get_app_path_side, import_doc_side):
    """Stub `frappe` + `frappe.modules.import_file.import_doc` in sys.modules."""
    fake_frappe = types.SimpleNamespace(
        get_installed_apps=lambda: installed_apps,
        get_app_path=get_app_path_side,
        logger=lambda: types.SimpleNamespace(warning=lambda *a, **k: None),
    )
    fake_modules = types.SimpleNamespace()
    fake_import_file = types.SimpleNamespace(import_doc=import_doc_side)

    monkeypatch.setitem(sys.modules, "frappe", fake_frappe)
    monkeypatch.setitem(sys.modules, "frappe.modules", fake_modules)
    monkeypatch.setitem(sys.modules, "frappe.core", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "frappe.core.doctype", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "frappe.core.doctype.data_import", types.SimpleNamespace())
    monkeypatch.setitem(
        sys.modules, "frappe.core.doctype.data_import.data_import", fake_import_file
    )
    # Reload the loader so its module-level imports (none currently, but be safe).
    import frappe_fixture_normalize.loader as loader_mod

    importlib.reload(loader_mod)
    return loader_mod


def test_import_split_fixtures_skips_broken_app(tmp_path, monkeypatch):
    """`frappe.get_app_path` raising must not abort the loader; the bad app is
    skipped and remaining apps still processed."""
    good_app = tmp_path / "good"
    (good_app / "fixtures" / "custom_field").mkdir(parents=True)
    fixture_path = good_app / "fixtures" / "custom_field" / "issue.json"
    fixture_path.write_text(_json.dumps([{"name": "Issue-foo", "doctype": "Custom Field"}]))

    imported: list[str] = []

    def fake_get_app_path(app):
        if app == "broken":
            raise RuntimeError("broken app")
        if app == "good":
            return str(good_app)
        raise AssertionError(f"unexpected app: {app}")

    def fake_import_doc(path):
        imported.append(str(path))

    loader_mod = _install_fake_frappe(
        monkeypatch,
        installed_apps=["broken", "good"],
        get_app_path_side=fake_get_app_path,
        import_doc_side=fake_import_doc,
    )
    loader_mod.import_split_fixtures()

    assert imported == [str(fixture_path)]


def test_import_split_fixtures_logs_and_continues_on_import_failure(tmp_path, monkeypatch):
    """A single record import failing must not stop the walk."""
    app_root = tmp_path / "good"
    sub = app_root / "fixtures" / "custom_field"
    sub.mkdir(parents=True)
    bad = sub / "bad.json"
    good = sub / "good.json"
    bad.write_text(_json.dumps([{"name": "Bad"}]))
    good.write_text(_json.dumps([{"name": "Good"}]))

    import_calls: list[str] = []
    warnings: list[str] = []

    def fake_import_doc(path):
        import_calls.append(path)
        if path.endswith("bad.json"):
            raise ValueError("simulated import error")

    fake_logger = types.SimpleNamespace(warning=lambda msg, *a, **k: warnings.append(msg))
    fake_frappe = types.SimpleNamespace(
        get_installed_apps=lambda: ["good"],
        get_app_path=lambda _: str(app_root),
        logger=lambda: fake_logger,
    )
    monkeypatch.setitem(sys.modules, "frappe", fake_frappe)
    monkeypatch.setitem(sys.modules, "frappe.core", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "frappe.core.doctype", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "frappe.core.doctype.data_import", types.SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "frappe.core.doctype.data_import.data_import",
        types.SimpleNamespace(import_doc=fake_import_doc),
    )

    import frappe_fixture_normalize.loader as loader_mod
    importlib.reload(loader_mod)
    loader_mod.import_split_fixtures()

    # Both files were attempted; warning was emitted for the bad one.
    assert sorted(import_calls) == sorted([str(bad), str(good)])
    assert any("bad.json" in w for w in warnings)
