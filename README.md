# frappe_fixture_normalize

[![CI](https://github.com/ananyo141/frappe-fixture-normalize/actions/workflows/ci.yml/badge.svg)](https://github.com/ananyo141/frappe-fixture-normalize/actions/workflows/ci.yml)

Stable, merge-safe fixture export and import for Frappe apps.

## Demo

![Demo](tests/demo/demo.svg)

> Cast source: [`tests/demo/demo.cast`](tests/demo/demo.cast). Rendered with
> `svg-term --cast tests/demo/demo.cast --out tests/demo/demo.svg --window --width 100 --height 28`.
> Re-record against your bench: see [`tests/demo/README.md`](tests/demo/README.md).

## The problem

Every Frappe project that uses fixtures hits the same three issues with stock `bench export-fixtures`:

1. **Per-machine ordering.** Records are exported `ORDER BY idx, creation` (`frappe/utils/fixtures.py:99`). The `creation` timestamp differs per dev environment, so the order of records shuffles between machines. Two devs running `export-fixtures` on the same DB get different files.

2. **`modified` timestamp leak.** Frappe's export strips `creation`, `owner`, `idx` etc., but not `modified` (`frappe/core/doctype/data_import/data_import.py:343-362`). Every record's ISO timestamp ends up in the JSON, so every export looks like a per-record rewrite — even when nothing changed.

3. **Single flat file per doctype.** All Custom Field records — across every target doctype — live in one `custom_field.json`. With a real project this is hundreds of records in a 250 KB+ file. Two devs adding fields to *different* doctypes on *different* branches still merge-conflict on the same file.

Result: every `export-fixtures` run produces a wholesale rewrite, every PR carries hundreds of "noise" lines, and any concurrent fixture work means manual conflict resolution.

## Frappe default vs. this app

| Behavior | Stock `bench export-fixtures` | `frappe_fixture_normalize` |
|---|---|---|
| Record order | `ORDER BY idx, creation` — varies per machine | Sorted alphabetically by `name` — deterministic |
| `modified` field | Kept in every record | Stripped |
| File layout for Custom Field | One flat `custom_field.json` | `custom_field/<target_doctype>.json` (one per target) |
| File layout for Property Setter | One flat `property_setter.json` | `property_setter/<target_doctype>.json` (one per target) |
| Trailing newline on output | No | Yes (POSIX) |
| Re-export with no DB changes | Wholesale rewrite (timestamps + reorder) | Zero diff |
| Two devs add fields to different doctypes | Merge conflict on `custom_field.json` | Auto-merge (different files) |
| `bench migrate` imports split files | No — only `fixtures/*.json` at top level | Yes — `after_migrate` hook walks `fixtures/<doctype>/*.json` |
| `bench export-fixtures` command | Stock | Auto-overridden via `commands.py` dict-merge |

### Before / after diff snippet

**Stock**, one record changes, diff touches every record:

```diff
- "modified": "2025-05-17 09:14:22.391823",
+ "modified": "2025-05-17 11:02:01.847551",
... (× 200 records, all unchanged but reordered or re-stamped) ...
```

**This app**, same change, diff is bounded to the actual edit:

```diff
   "label": "Reference ID",
+  "description": "External payment processor reference",
   "fieldtype": "Data",
```

One field added → exactly one hunk in exactly one file (`fixtures/custom_field/issue.json` if you touched Issue).

## Two adoption paths

| Mode | Setup | What you get |
|---|---|---|
| [**Minimal (pre-commit only)**](#minimal-mode-pre-commit-only-no-bench-install) | `pip install pre-commit` + `.pre-commit-config.yaml` | Clean diffs, no `modified` churn, records sorted by `name`. Single-file layout stays. |
| [**Full app install**](#full-install) | `bench get-app` + `bench install-app` (+ optional pre-commit) | All of the above plus per-target split files, auto-import on `bench migrate`, stock `bench export-fixtures` overridden |

Start minimal. Upgrade to the full app when same-doctype merge conflicts or auto-import become pain points.

## Minimal mode (pre-commit only, no bench install)

No Frappe app installation needed. The `pre-commit` framework runs the normalizer in its own isolated venv. Suitable when you want clean diffs without shipping another app to production.

### What it fixes vs. what it doesn't

| Problem | Minimal mode | Full app |
|---|---|---|
| `modified` field churn | ✅ stripped on commit | ✅ |
| Record order shuffles per machine | ✅ sorted by `name` on commit | ✅ |
| Wholesale flat-file rewrite | ✅ canonicalized → minimal diff | ✅ |
| Merge conflicts on single big `custom_field.json` | ❌ still conflicts | ✅ split per target |
| Auto-import of split files on `bench migrate` | ❌ stock `sync_fixtures` only | ✅ |
| Stock `bench export-fixtures` override | ❌ | ✅ |

### Setup

In your consumer repo (the one containing `<app>/<app>/fixtures/`):

```bash
pip install pre-commit
```

Add `.pre-commit-config.yaml` at the repo root:

```yaml
repos:
  - repo: local
    hooks:
      - id: normalize-fixtures
        name: Normalize Frappe fixture JSON
        entry: python -m frappe_fixture_normalize.pre_commit_hook
        language: python
        additional_dependencies:
          - git+https://github.com/ananyo141/frappe-fixture-normalize.git
        files: (^|/)fixtures/.*\.json$
```

`additional_dependencies` tells the pre-commit framework to spin up an isolated venv, pip-install our package there, and run the hook in that environment. **No `bench install-app` required.** Venv is cached after first run.

Activate the hook:

```bash
pre-commit install
```

### Workflow

```bash
# Dev runs the stock fixture export — produces ugly, machine-specific output.
bench --site <site> export-fixtures
git add backend/myapp/myapp/fixtures/custom_field.json
git commit -m "add field X"
# Pre-commit fires:
#   normalized backend/myapp/myapp/fixtures/custom_field.json
#   exit 1 → commit aborted, file rewritten in canonical form.

git add backend/myapp/myapp/fixtures/custom_field.json
git commit -m "add field X"
# Pre-commit passes; commit lands with minimal, sorted, modified-free diff.
```

Every subsequent commit touching `fixtures/**/*.json` runs the same pipeline.

### Smoke-test the setup

```bash
mkdir /tmp/test_repo && cd /tmp/test_repo
git init -q
mkdir -p fixtures

cat > fixtures/custom_field.json <<'JSON'
[
 {"name": "Issue-zzz", "doctype": "Custom Field", "modified": "2025-01-01"},
 {"name": "Issue-aaa", "doctype": "Custom Field", "modified": "2025-01-02"}
]
JSON

cat > .pre-commit-config.yaml <<'YAML'
repos:
  - repo: local
    hooks:
      - id: normalize-fixtures
        name: Normalize Frappe fixture JSON
        entry: python -m frappe_fixture_normalize.pre_commit_hook
        language: python
        additional_dependencies:
          - git+https://github.com/ananyo141/frappe-fixture-normalize.git
        files: (^|/)fixtures/.*\.json$
YAML

git add .
git commit -m "initial"   # first run builds venv (~10s), then rewrites + fails
git add .
git commit -m "initial"   # passes; inspect fixtures/custom_field.json
```

Expected: records sorted by `name`, `modified` stripped, file ends with a trailing newline.

## Full install

```bash
bench get-app https://github.com/ananyo141/frappe-fixture-normalize.git
bench --site <site> install-app frappe_fixture_normalize
```

After install, the sections below describe the behavior unlocked.

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
