"""Unit tests for `frappe_fixture_normalize.commands`.

`frappe` is not installed in the pure-pytest environment, so we stub the
modules and attributes the commands module touches at import time.
`click.testing.CliRunner` drives the commands without a real bench.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _install_frappe_stub(monkeypatch, hooks_value=None, installed_apps=None, app_paths=None):
    """Replace `frappe`, `frappe.commands`, `frappe.exceptions`,
    `frappe.utils.fixtures` in sys.modules with minimal fakes."""

    installed_apps = installed_apps if installed_apps is not None else []
    app_paths = app_paths or {}

    class SiteNotSpecifiedError(Exception):
        pass

    def pass_context(fn):
        # Click's pass_context normally injects the click context; for our
        # tests we pass it directly via CliRunner.invoke(obj=...).
        return fn

    fake_frappe = types.SimpleNamespace(
        init=lambda *a, **k: None,
        connect=lambda *a, **k: None,
        destroy=lambda *a, **k: None,
        get_hooks=lambda key, app_name=None: hooks_value if hooks_value is not None else [],
        get_installed_apps=lambda: list(installed_apps),
        get_app_path=lambda app: app_paths.get(app, f"/tmp/fake/{app}"),
    )
    fake_commands = types.SimpleNamespace(pass_context=pass_context)
    fake_exceptions = types.SimpleNamespace(SiteNotSpecifiedError=SiteNotSpecifiedError)
    fake_utils = types.SimpleNamespace()
    fake_utils_fixtures = types.SimpleNamespace(export_fixtures=lambda app=None: None)

    monkeypatch.setitem(sys.modules, "frappe", fake_frappe)
    monkeypatch.setitem(sys.modules, "frappe.commands", fake_commands)
    monkeypatch.setitem(sys.modules, "frappe.exceptions", fake_exceptions)
    monkeypatch.setitem(sys.modules, "frappe.utils", fake_utils)
    monkeypatch.setitem(sys.modules, "frappe.utils.fixtures", fake_utils_fixtures)

    # Force reload commands module under the stubbed environment.
    import importlib

    if "frappe_fixture_normalize.commands" in sys.modules:
        del sys.modules["frappe_fixture_normalize.commands"]
    return importlib.import_module("frappe_fixture_normalize.commands"), SiteNotSpecifiedError


# --- _resolve_split_config -----------------------------------------------


def test_resolve_split_config_returns_defaults_when_hook_missing(monkeypatch):
    commands, _ = _install_frappe_stub(monkeypatch, hooks_value=[])
    out = commands._resolve_split_config("apex")
    assert out == {"Custom Field": "dt", "Property Setter": "doc_type"}


def test_resolve_split_config_merges_list_of_dicts(monkeypatch):
    commands, _ = _install_frappe_stub(
        monkeypatch,
        hooks_value=[
            {"Custom Field": "dt"},
            {"Workflow": "document_type"},
        ],
    )
    out = commands._resolve_split_config("apex")
    assert out == {"Custom Field": "dt", "Workflow": "document_type"}


def test_resolve_split_config_accepts_plain_dict(monkeypatch):
    commands, _ = _install_frappe_stub(
        monkeypatch,
        hooks_value={"Custom Field": "dt", "Workflow": "document_type"},
    )
    out = commands._resolve_split_config("apex")
    assert out == {"Custom Field": "dt", "Workflow": "document_type"}


def test_resolve_split_config_falls_back_on_malformed_hook(monkeypatch):
    commands, _ = _install_frappe_stub(monkeypatch, hooks_value="not a mapping")
    out = commands._resolve_split_config("apex")
    assert out == {"Custom Field": "dt", "Property Setter": "doc_type"}


def test_resolve_split_config_skips_non_dict_list_entries(monkeypatch):
    commands, _ = _install_frappe_stub(
        monkeypatch,
        hooks_value=["string", 42, {"Workflow": "document_type"}, None],
    )
    out = commands._resolve_split_config("apex")
    assert out == {"Workflow": "document_type"}


def test_resolve_split_config_returns_defaults_when_merged_empty(monkeypatch):
    commands, _ = _install_frappe_stub(monkeypatch, hooks_value=[{}, {}])
    out = commands._resolve_split_config("apex")
    assert out == {"Custom Field": "dt", "Property Setter": "doc_type"}


# --- click commands: site-not-specified path -----------------------------


class _NoSiteContext:
    sites: list[str] = []


def test_export_command_raises_when_no_site(monkeypatch):
    commands, SiteNotSpecifiedError = _install_frappe_stub(monkeypatch)
    ctx = _NoSiteContext()
    with pytest.raises(SiteNotSpecifiedError):
        commands.export_clean_fixtures.callback(ctx, app=None)


def test_normalize_command_raises_when_no_site(monkeypatch):
    commands, SiteNotSpecifiedError = _install_frappe_stub(monkeypatch)
    ctx = _NoSiteContext()
    with pytest.raises(SiteNotSpecifiedError):
        commands.normalize_fixtures.callback(ctx, app=None)


# --- commands list registration ------------------------------------------


def test_commands_export_list_contains_all_entries(monkeypatch):
    commands, _ = _install_frappe_stub(monkeypatch)
    names = {c.name for c in commands.commands}
    assert names == {"export-clean-fixtures", "normalize-fixtures", "export-fixtures"}


def test_export_fixtures_override_raises_when_no_site(monkeypatch):
    commands, SiteNotSpecifiedError = _install_frappe_stub(monkeypatch)
    ctx = _NoSiteContext()
    with pytest.raises(SiteNotSpecifiedError):
        commands.export_fixtures_override.callback(ctx, app=None)


def test_export_fixtures_override_iterates_sites(monkeypatch, tmp_path):
    """Sanity: the override command threads --app through to `_run_for_site`
    exactly like `export-clean-fixtures`."""
    commands, _ = _install_frappe_stub(
        monkeypatch,
        installed_apps=["apex"],
        app_paths={"apex": str(tmp_path)},
    )
    (tmp_path / "fixtures").mkdir()
    invoked = []
    monkeypatch.setattr(commands, "_run_for_site", lambda site, app: invoked.append((site, app)))
    ctx = _MultiSiteContext(["a.localhost"])
    commands.export_fixtures_override.callback(ctx, app="apex")
    assert invoked == [("a.localhost", "apex")]


# --- happy path through `_run_for_site` (export pipeline) ----------------


def test_run_for_site_invokes_export_then_post_process(monkeypatch, tmp_path):
    """`_run_for_site` should call frappe's `export_fixtures` for the requested
    app, then normalize the resulting `fixtures/` directory."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    # Pre-seed a flat file so post-process has something to normalize.
    flat = fixtures / "custom_field.json"
    flat.write_text('[{"name": "X", "doctype": "Custom Field", "dt": "Issue", "modified": "Y"}]')

    commands, _ = _install_frappe_stub(
        monkeypatch,
        installed_apps=["apex"],
        app_paths={"apex": str(tmp_path)},
    )
    # Track that export_fixtures was called.
    call_log = []

    def tracked_export(app=None):
        call_log.append(app)

    monkeypatch.setattr(
        sys.modules["frappe.utils.fixtures"],
        "export_fixtures",
        tracked_export,
    )

    commands._run_for_site("apex.localhost", "apex")
    assert call_log == ["apex"]
    # Post-process should have split the flat file under split-by config (Custom Field/dt).
    assert (fixtures / "custom_field" / "issue.json").exists()
    assert not flat.exists()


class _MultiSiteContext:
    def __init__(self, sites):
        self.sites = sites


def test_export_callback_iterates_sites(monkeypatch, tmp_path):
    commands, _ = _install_frappe_stub(
        monkeypatch,
        installed_apps=["apex"],
        app_paths={"apex": str(tmp_path)},
    )
    (tmp_path / "fixtures").mkdir()
    invoked = []
    monkeypatch.setattr(commands, "_run_for_site", lambda site, app: invoked.append((site, app)))
    ctx = _MultiSiteContext(["a.localhost", "b.localhost"])
    commands.export_clean_fixtures.callback(ctx, app="apex")
    assert invoked == [("a.localhost", "apex"), ("b.localhost", "apex")]


def test_normalize_callback_iterates_sites(monkeypatch, tmp_path):
    commands, _ = _install_frappe_stub(
        monkeypatch,
        installed_apps=["apex"],
        app_paths={"apex": str(tmp_path)},
    )
    (tmp_path / "fixtures").mkdir()
    invoked = []
    monkeypatch.setattr(commands, "_normalize_for_site", lambda site, app: invoked.append((site, app)))
    ctx = _MultiSiteContext(["a.localhost"])
    commands.normalize_fixtures.callback(ctx, app=None)
    assert invoked == [("a.localhost", None)]


def test_normalize_for_site_skips_export_call(monkeypatch, tmp_path):
    """`_normalize_for_site` must NOT call frappe.export_fixtures — it operates
    on existing files only."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    flat = fixtures / "custom_field.json"
    flat.write_text('[{"name": "X", "doctype": "Custom Field", "dt": "Issue"}]')

    commands, _ = _install_frappe_stub(
        monkeypatch,
        installed_apps=["apex"],
        app_paths={"apex": str(tmp_path)},
    )
    call_log = []
    monkeypatch.setattr(
        sys.modules["frappe.utils.fixtures"],
        "export_fixtures",
        lambda app=None: call_log.append(app),
    )

    commands._normalize_for_site("apex.localhost", "apex")
    assert call_log == []  # export_fixtures never invoked
    assert (fixtures / "custom_field" / "issue.json").exists()
