#!/usr/bin/env bash
# Scenario 05: Loader idempotence.
#
# Delete a single Custom Field from the DB, run `bench migrate`, verify the
# row is restored from the split fixture file. Re-run migrate: row count
# unchanged (no duplicates, no errors).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

# Re-export first so DB and split files are in sync; then pick a victim
# whose row actually exists in the DB.
bench_exec export-clean-fixtures --app "$APP" > /dev/null 2>&1 || true

victim=""
for cf_file in $(find "$FIXTURES_DIR/custom_field" -name '*.json' -type f 2>/dev/null | sort); do
    candidate="$(python3 -c "import json,sys; print(json.load(open('$cf_file'))[0]['name'])" 2>/dev/null || true)"
    [ -z "$candidate" ] && continue
    if [ "$(cf_count_by_name "$candidate")" = "1" ]; then
        victim="$candidate"
        break
    fi
done

if [ -z "$victim" ]; then
    echo "↷ SKIP 05_idempotence: no split fixture record matched a DB row"
    exit 0
fi

bench_exec execute frappe.client.delete --kwargs "{'doctype': 'Custom Field', 'name': '$victim'}" > /dev/null 2>&1 || true
after_delete="$(cf_count_by_name "$victim")"
[ "$after_delete" = "0" ] || log_fail "05_idempotence: delete did not remove the row (got '$after_delete')"

bench_exec execute frappe_fixture_normalize.loader.import_split_fixtures > /dev/null 2>&1
after_migrate="$(cf_count_by_name "$victim")"
[ "$after_migrate" = "1" ] || log_fail "05_idempotence: migrate did not restore the row (got '$after_migrate')"

bench_exec execute frappe_fixture_normalize.loader.import_split_fixtures > /dev/null 2>&1
after_second="$(cf_count_by_name "$victim")"
[ "$after_second" = "1" ] || log_fail "05_idempotence: second migrate created duplicates (got '$after_second')"

log_pass "deleted row restored by migrate; second migrate left count unchanged ($victim)"
