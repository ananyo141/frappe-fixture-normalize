# frappe_fixture_normalize

[![CI](https://github.com/ananyo141/frappe-fixture-normalize/actions/workflows/ci.yml/badge.svg)](https://github.com/ananyo141/frappe-fixture-normalize/actions/workflows/ci.yml)

Stable, merge-safe fixture export and import for Frappe apps.

## What it solves

`bench export-fixtures` rewrites fixture files wholesale on every export:

- Records are ordered by `creation` timestamp, which differs per machine, so order shuffles.
- The per-record `modified` timestamp leaks into the diff.
- All Custom Field / Property Setter records share one large file, so independent feature branches always conflict.

This app fixes all three.

## Install

```bash
bench get-app frappe_fixture_normalize <repo-url>
bench --site <site> install-app frappe_fixture_normalize
```

## Export

Once installed, stock `bench export-fixtures` is automatically overridden — every export goes through this app's pipeline. Frappe's CLI dict-merges each installed app's `commands.py:commands` list in `apps.txt` order
(`frappe/utils/bench_helper.py:get_app_groups`), so the entry from this app wins over frappe's own.

```bash
bench --site <site> export-fixtures --app <your_app>
# or, explicit name (same behavior; useful in scripts that want to bypass the override):
bench --site <site> export-clean-fixtures --app <your_app>
```

Output is deterministic across machines:

- Records sorted alphabetically by `name`.
- `modified` field stripped per record.
- JSON dumped with `indent=1, sort_keys=True, ensure_ascii=False` plus trailing newline.
- For `Custom Field` and `Property Setter`, one file per target doctype is written under `fixtures/custom_field/<target>.json` and `fixtures/property_setter/<target>.json`.

The flat `fixtures/custom_field.json` / `fixtures/property_setter.json` files are removed automatically.

## Import

`after_migrate` hook walks every installed app's `fixtures/<scrub(doctype)>/*.json` and loads each record idempotently. Runs automatically on `bench migrate`.

## Pre-commit hook

```yaml
- repo: local
  hooks:
    - id: normalize-fixtures
      name: Normalize Frappe fixture JSON
      entry: python -m frappe_fixture_normalize.pre_commit_hook
      language: system
      files: ^.*/fixtures/.*\.json$
```

Defends against hand-edits and rebases that re-introduce noise.

## Configure split targets

Defaults:

```python
# frappe_fixture_normalize/config.py
DEFAULT_SPLIT_BY = {
    "Custom Field": "dt",
    "Property Setter": "doc_type",
}
```

Override per consumer app via `hooks.py`:

```python
fixture_normalize_split_by = {
    "Custom Field": "dt",
    "Property Setter": "doc_type",
    "Workflow": "document_type",
}
```

## Supported Frappe versions

CI verifies the app on every push against:

| Frappe | Python | Node |
|---|---|---|
| `version-15` | 3.11 | 20 |
| `version-16` | 3.14 | 24 |

The test suite uses a `frappe_fixture_normalize/tests/_compat.py` shim so the
same L2 tests run on both branches — `IntegrationTestCase` resolves to
`frappe.tests.IntegrationTestCase` on v16 and `frappe.tests.utils.FrappeTestCase`
on v15.

## License

MIT
