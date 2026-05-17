#!/usr/bin/env bash
# End-to-end runner. Executes every `NN_*.sh` in this directory in order,
# reports per-scenario PASS/FAIL/SKIP, exits non-zero if any FAIL.
#
# Required env: BENCH_DIR, SITE, APP
#
# Example (Lando):
#   BENCH_DIR=/path/to/frappe-bench \
#       SITE=myapp.localhost APP=myapp MODULE=MyAppModule \
#       bash <BENCH_DIR>/apps/frappe_fixture_normalize/tests/e2e/run_all.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

: "${BENCH_DIR:?BENCH_DIR required}"
: "${SITE:?SITE required}"
: "${APP:?APP required}"

passed=0
failed=0
skipped=0
failures=()

for script in "$SCRIPT_DIR"/[0-9][0-9]_*.sh; do
    name="$(basename "$script")"
    echo "── $name ────────────────────────"
    if out="$(bash "$script" 2>&1)"; then
        if echo "$out" | grep -q '^↷ SKIP'; then
            skipped=$((skipped + 1))
            echo "$out"
        else
            passed=$((passed + 1))
            echo "$out"
        fi
    else
        failed=$((failed + 1))
        failures+=("$name")
        echo "$out"
    fi
done

echo
echo "════════════════════════════════"
echo "passed:  $passed"
echo "skipped: $skipped"
echo "failed:  $failed"
if [ "$failed" -gt 0 ]; then
    echo "failing scenarios: ${failures[*]}"
    exit 1
fi
