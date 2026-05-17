"""Bench CLI: `bench export-clean-fixtures --app <name>`.

Wraps the standard `bench export-fixtures` and post-processes the written
files into a deterministic, merge-safe layout.

The `*_for_site` wrappers manage Frappe lifecycle (init/connect/destroy) so
they can be invoked from a bare `bench` shell. Tests running inside an
already-connected Frappe context should call `do_export_and_normalize` /
`do_normalize_only` directly.
"""

from __future__ import annotations

from pathlib import Path

import click
import frappe
from frappe.commands import pass_context
from frappe.exceptions import SiteNotSpecifiedError

from frappe_fixture_normalize.config import DEFAULT_SPLIT_BY
from frappe_fixture_normalize.exporter import process_app_fixtures_dir


def _resolve_split_config(app: str) -> dict[str, str]:
    hooks_value = frappe.get_hooks("fixture_normalize_split_by", app_name=app)
    # frappe.get_hooks returns a list for unknown shapes; normalize.
    if not hooks_value:
        return dict(DEFAULT_SPLIT_BY)
    if isinstance(hooks_value, list):
        merged: dict[str, str] = {}
        for entry in hooks_value:
            if isinstance(entry, dict):
                merged.update(entry)
        return merged or dict(DEFAULT_SPLIT_BY)
    if isinstance(hooks_value, dict):
        return dict(hooks_value)
    return dict(DEFAULT_SPLIT_BY)


def _process_app(app: str) -> None:
    app_path = Path(frappe.get_app_path(app))
    fixtures_dir = app_path / "fixtures"
    split_config = _resolve_split_config(app)
    process_app_fixtures_dir(fixtures_dir, split_config)
    click.echo(f"normalized fixtures for {app} at {fixtures_dir}")


def do_export_and_normalize(app: str | None) -> None:
    """Frappe must already be init/connected. Calls standard export then
    post-processes."""
    from frappe.utils.fixtures import export_fixtures

    export_fixtures(app=app)
    apps = [app] if app else frappe.get_installed_apps()
    for current_app in apps:
        _process_app(current_app)


def do_normalize_only(app: str | None) -> None:
    """Frappe must already be init/connected. Re-normalizes on-disk files
    without re-querying the DB."""
    apps = [app] if app else frappe.get_installed_apps()
    for current_app in apps:
        _process_app(current_app)


def _run_for_site(site: str, app: str | None) -> None:
    frappe.init(site)
    frappe.connect()
    try:
        do_export_and_normalize(app)
    finally:
        frappe.destroy()


def _normalize_for_site(site: str, app: str | None) -> None:
    frappe.init(site)
    frappe.connect()
    try:
        do_normalize_only(app)
    finally:
        frappe.destroy()


@click.command("export-clean-fixtures")
@click.option("--app", default=None, help="Export fixtures of a specific app (default: all installed)")
@pass_context
def export_clean_fixtures(context, app=None):
    """Export fixtures with stable ordering, stripped `modified`, and per-target splits."""
    for site in context.sites:
        _run_for_site(site, app)
    if not context.sites:
        raise SiteNotSpecifiedError


@click.command("normalize-fixtures")
@click.option("--app", default=None, help="Normalize fixtures of a specific app (default: all installed)")
@pass_context
def normalize_fixtures(context, app=None):
    """Re-normalize existing fixture files without re-querying the DB.

    Useful for committing current on-disk state after a rebase, or for splitting
    legacy flat fixture files into the per-target layout one-time.
    """
    for site in context.sites:
        _normalize_for_site(site, app)
    if not context.sites:
        raise SiteNotSpecifiedError


@click.command("export-fixtures")
@click.option("--app", default=None, help="Export fixtures of a specific app (default: all installed)")
@pass_context
def export_fixtures_override(context, app=None):
    """Drop-in replacement for `bench export-fixtures` that produces stable,
    merge-safe output.

    Frappe assembles its CLI by dict-merging each installed app's `commands`
    list in `apps.txt` order (frappe/utils/bench_helper.py:get_app_groups).
    Apps installed after frappe — like this one — override earlier
    same-named entries, so running `bench export-fixtures` lands here.

    Behavior is identical to `bench export-clean-fixtures`; the explicit
    name is kept for documentation, scripts, and tests that want to bypass
    the override.
    """
    for site in context.sites:
        _run_for_site(site, app)
    if not context.sites:
        raise SiteNotSpecifiedError


commands = [export_clean_fixtures, normalize_fixtures, export_fixtures_override]
