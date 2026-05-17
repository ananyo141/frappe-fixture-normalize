#!/usr/bin/env bash
# Scenario 03: Bounded single-field diff.
#
# Adding one Custom Field to a single doctype must produce a diff touching
# exactly one file (that doctype's split file). No whole-tree rewrite.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

snap="$(snapshot_fixtures)"

# Baseline export ensures we start from the canonical state.
bench_exec export-clean-fixtures --app "$APP" > /dev/null
baseline="$(mktemp -d)"; register_temp_dir "$baseline"
cp -r "$FIXTURES_DIR/." "$baseline/"

# Add one Custom Field to Issue.
cf_name="$(insert_custom_field 'Issue' 'e2e_ffn_single_field' 'Apex')"
register_temp_field "$cf_name"

bench_exec export-clean-fixtures --app "$APP" > /dev/null

# Walk the trees: only `custom_field/issue.json` should have changed.
changed=()
while IFS= read -r path; do
    rel="${path#$FIXTURES_DIR/}"
    if [ ! -f "$baseline/$rel" ] || ! cmp -s "$path" "$baseline/$rel"; then
        changed+=("$rel")
    fi
done < <(find "$FIXTURES_DIR" -type f -name '*.json')

# Anything in baseline missing now?
while IFS= read -r path; do
    rel="${path#$baseline/}"
    if [ ! -f "$FIXTURES_DIR/$rel" ]; then
        changed+=("MISSING:$rel")
    fi
done < <(find "$baseline" -type f -name '*.json')

delete_custom_field "$cf_name"
bench_exec export-clean-fixtures --app "$APP" > /dev/null
restore_fixtures_snapshot "$snap"

if [ "${#changed[@]}" -eq 1 ] && [ "${changed[0]}" = "custom_field/issue.json" ]; then
    log_pass "single field add touched exactly custom_field/issue.json"
else
    echo "expected only custom_field/issue.json to change; got: ${changed[*]}" >&2
    log_fail "03_single_field_diff"
fi
