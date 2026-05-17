"""Bench CLI: `bench export-clean-fixtures --app <name>`.

Wraps the standard `bench export-fixtures` and post-processes the written
files into a deterministic, merge-safe layout.
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


def _run_for_site(site: str, app: str | None) -> None:
    from frappe.utils.fixtures import export_fixtures

    frappe.init(site)
    frappe.connect()
    try:
        export_fixtures(app=app)
        apps = [app] if app else frappe.get_installed_apps()
        for current_app in apps:
            app_path = Path(frappe.get_app_path(current_app))
            fixtures_dir = app_path / "fixtures"
            split_config = _resolve_split_config(current_app)
            process_app_fixtures_dir(fixtures_dir, split_config)
            click.echo(f"normalized fixtures for {current_app} at {fixtures_dir}")
    finally:
        frappe.destroy()


def _normalize_for_site(site: str, app: str | None) -> None:
    frappe.init(site)
    frappe.connect()
    try:
        apps = [app] if app else frappe.get_installed_apps()
        for current_app in apps:
            app_path = Path(frappe.get_app_path(current_app))
            fixtures_dir = app_path / "fixtures"
            split_config = _resolve_split_config(current_app)
            process_app_fixtures_dir(fixtures_dir, split_config)
            click.echo(f"normalized fixtures for {current_app} at {fixtures_dir}")
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


commands = [export_clean_fixtures, normalize_fixtures]
