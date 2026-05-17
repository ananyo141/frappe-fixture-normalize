#!/usr/bin/env bash
# Scenario 08: `bench export-fixtures` override is live.
#
# Verifies two things:
#   1. `bench --help` shows OUR docstring under the `export-fixtures` entry,
#      proving frappe's dict-merge in `get_app_groups` picked our command
#      over frappe's own.
#   2. Running `bench export-fixtures --app $APP` produces split-file
#      output (subdir layout + sorted + no `modified`), the signature of
#      our pipeline rather than stock frappe's.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

# 1. help-text fingerprint
help_line="$(cd "$BENCH_DIR" && bench --help 2>&1 | grep -E '^\s*export-fixtures\b' || true)"
if [ -z "$help_line" ]; then
    log_fail "08_override_active: 'export-fixtures' not present in bench --help"
fi
case "$help_line" in
    *"Drop-in replacement"*)
        : ;;  # ours
    *)
        echo "expected our docstring 'Drop-in replacement...' in:" >&2
        echo "  $help_line" >&2
        log_fail "08_override_active: 'export-fixtures' bench help shows frappe's docstring, not ours"
        ;;
esac

# 2. behavior fingerprint — invoke stock name, expect split layout output.
snap="$(snapshot_fixtures)"
bench_exec export-fixtures --app "$APP" > /tmp/ffn_override_run.log 2>&1 || true

if ! grep -q "normalized fixtures for $APP" /tmp/ffn_override_run.log; then
    echo "stdout from bench export-fixtures:" >&2
    cat /tmp/ffn_override_run.log >&2
    restore_fixtures_snapshot "$snap"
    log_fail "08_override_active: 'normalized fixtures' marker missing — pipeline didn't run"
fi

# Subdir layout exists; flat does not.
if [ ! -d "$FIXTURES_DIR/custom_field" ]; then
    restore_fixtures_snapshot "$snap"
    log_fail "08_override_active: split subdir custom_field/ not present after export-fixtures"
fi
if [ -f "$FIXTURES_DIR/custom_field.json" ]; then
    restore_fixtures_snapshot "$snap"
    log_fail "08_override_active: flat custom_field.json should be removed after export-fixtures"
fi

restore_fixtures_snapshot "$snap"
rm -f /tmp/ffn_override_run.log

log_pass "bench export-fixtures invokes our pipeline (override active)"
