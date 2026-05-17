# End-to-end test scenarios

Shell scripts that exercise the full `frappe_fixture_normalize` pipeline
against a real Frappe bench. Use these before tagging a release, or to
validate behavior against a specific consumer app.

## What each script verifies

| # | Script | Verifies |
|---|---|---|
| 01 | `01_determinism.sh` | Two consecutive `export-clean-fixtures` runs produce byte-identical files |
| 02 | `02_cross_machine.sh` | Same DB → same file tree across two sites (set `E2E_CROSS_MACHINE=1`) |
| 03 | `03_single_field_diff.sh` | Adding one Custom Field changes exactly one split file |
| 04 | `04_merge_safety.sh` | Two branches adding fields to different doctypes merge without conflict |
| 05 | `05_idempotence.sh` | Deleted record restored by the loader; re-run produces no duplicates |
| 06 | `06_pre_commit_framework.sh` | `pre-commit` framework integration: dirty fixture is rewritten |
| 07 | `07_legacy_split.sh` | Pre-app flat fixture file is split into per-target without record loss |
| 08 | `08_override_active.sh` | `bench export-fixtures` (stock name) invokes our pipeline |

## Running against your consumer bench

```bash
BENCH_DIR=/path/to/frappe-bench \
SITE=myapp.localhost \
APP=myapp \
MODULE=MyAppModule \
bash <BENCH_DIR>/apps/frappe_fixture_normalize/tests/e2e/run_all.sh
```

| Env | Required | Description |
|---|---|---|
| `BENCH_DIR` | yes | Absolute path to the bench root |
| `SITE` | yes | Frappe site name |
| `APP` | yes | Consumer app slug. Its `fixtures/` directory is the target |
| `MODULE` | only for 03, 04 | Frappe module the test Custom Fields will be tagged with. Must match what your consumer's `hooks.fixtures` filter expects. Defaults to `"Custom"` if unset |
| `E2E_CROSS_MACHINE` | only for 02 | Set to `1` and provide `ALT_SITE` to enable |

## Required state in the consumer bench

Most scripts (01, 02, 05, 07, 08) need the consumer app to have at least
one Custom Field or Property Setter already in the database that the
`hooks.fixtures` filter will export. Scripts that find no records skip
themselves with a `↷ SKIP` message — they don't fail.

Scripts 03 and 04 create their own throwaway Custom Fields, tagged with
`$MODULE`, then clean up via the per-script `trap`. Make sure `$MODULE`
matches your consumer's filter (e.g. if your hook has
`["module", "in", ["MyAppModule"]]`, set `MODULE=MyAppModule`).

## Running a single scenario

```bash
BENCH_DIR=... SITE=... APP=... MODULE=... \
bash <BENCH_DIR>/apps/frappe_fixture_normalize/tests/e2e/08_override_active.sh
```

Each script is independent — `run_all.sh` is just an orchestrator that
prints a green/red summary.

## CI

Script `08_override_active.sh` runs in GitHub Actions on every push
(integration job). It needs no consumer state — only verifies that
`bench export-fixtures` produces our pipeline output.

The other scripts depend on consumer-side Custom Field rows and so
remain gated (`if: false`) in `.github/workflows/ci.yml`. Run them
locally before tagging.
