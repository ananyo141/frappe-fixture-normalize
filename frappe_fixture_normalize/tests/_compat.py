"""Cross-version compat for Frappe's test base class.

frappe v16 exposes `frappe.tests.IntegrationTestCase`; older releases (v14, v15)
expose `frappe.tests.utils.FrappeTestCase` instead. Tests should import
`IntegrationTestCase` from this module rather than directly from frappe.
"""

try:
    from frappe.tests import IntegrationTestCase  # noqa: F401  (v16+)
except ImportError:  # pragma: no cover - exercised on v14/v15 only
    from frappe.tests.utils import FrappeTestCase as IntegrationTestCase  # noqa: F401
