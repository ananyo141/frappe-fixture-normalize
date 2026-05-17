"""Layer-2 contract test: frappe's CLI assembly picks our `export-fixtures`.

Calls `frappe.utils.bench_helper.get_app_groups` directly — the very function
that `bench` uses to build its click root group at every invocation — and
asserts that the resulting `export-fixtures` command is OUR click command,
not frappe's.

This catches upstream frappe regressions in:
  * `get_app_groups`/`get_app_commands` (merge semantics — `|=`, `setdefault`, etc.)
  * `apps.txt` iteration order
  * Stock `export-fixtures` rename / removal
  * Our `commands` list registration

Without this test, an upstream change that switches the merge to first-wins
would silently revert our override.
"""

from __future__ import annotations

from frappe.utils import bench_helper

from frappe_fixture_normalize.tests._compat import IntegrationTestCase


class TestExportFixturesOverrideContract(IntegrationTestCase):
    def test_our_export_fixtures_wins_dict_merge(self):
        groups = bench_helper.get_app_groups()
        frappe_group = groups["frappe"]
        cmd = frappe_group.commands.get("export-fixtures")
        self.assertIsNotNone(cmd, "frappe assembled a CLI without an `export-fixtures` command")

        # The click `Command.callback` is the original function. Inspect its
        # module to confirm it is OUR implementation.
        callback = cmd.callback
        actual_module = getattr(callback, "__module__", "")
        self.assertEqual(
            actual_module,
            "frappe_fixture_normalize.commands",
            f"`export-fixtures` resolved to {actual_module!r}; expected our app. "
            "Upstream frappe may have changed `get_app_groups` merge semantics — "
            "stop and audit before shipping.",
        )

    def test_our_command_help_text_present(self):
        """Belt-and-braces fingerprint: a substring of our docstring must
        appear in the assembled click command's help text."""
        groups = bench_helper.get_app_groups()
        cmd = groups["frappe"].commands["export-fixtures"]
        self.assertIn("Drop-in replacement", cmd.help or "")

    def test_explicit_export_clean_fixtures_also_registered(self):
        """The override does not displace the explicit name — both must exist."""
        groups = bench_helper.get_app_groups()
        names = set(groups["frappe"].commands)
        self.assertIn("export-fixtures", names)
        self.assertIn("export-clean-fixtures", names)
        self.assertIn("normalize-fixtures", names)
