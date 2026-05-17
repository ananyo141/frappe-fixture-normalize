#!/usr/bin/env bash
# Scenario 04: Merge safety across two feature branches.
#
# Branch A adds a Custom Field to Issue; Branch B adds one to Subscription.
# Both export. Merging both into a third branch must produce no git conflict
# and result in a tree that is the union of changes.
#
# This scenario uses a sandbox git repo so it doesn't touch the app's real
# git state.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

snap="$(snapshot_fixtures)"

# Baseline.
bench_exec export-clean-fixtures --app "$APP" > /dev/null
sandbox="$(mktemp -d)"; register_temp_dir "$sandbox"
cp -r "$FIXTURES_DIR/." "$sandbox/"

(cd "$sandbox" && git init -q && git config user.email t@e && git config user.name T \
    && git add . && git commit -qm baseline)

# Branch A: field to Issue.
cf_a="$(insert_custom_field 'Issue' 'e2e_ffn_merge_a' "${MODULE:-Custom}")"; register_temp_field "$cf_a"
bench_exec export-clean-fixtures --app "$APP" > /dev/null
(cd "$sandbox" && git checkout -qb feat/a && cp -r "$FIXTURES_DIR/." . && git add . && git commit -qm "feat-a")
delete_custom_field "$cf_a"

# Branch B: field to Subscription.
cf_b="$(insert_custom_field 'Subscription' 'e2e_ffn_merge_b' "${MODULE:-Custom}")"; register_temp_field "$cf_b"
bench_exec export-clean-fixtures --app "$APP" > /dev/null
(cd "$sandbox" && git checkout -q main 2>/dev/null || git checkout -q master)
(cd "$sandbox" && git checkout -qb feat/b && cp -r "$FIXTURES_DIR/." . && git add . && git commit -qm "feat-b")
delete_custom_field "$cf_b"

# Reset disk to baseline, then merge in the sandbox.
restore_fixtures_snapshot "$snap"
bench_exec export-clean-fixtures --app "$APP" > /dev/null

merge_ok=true
(cd "$sandbox" && git checkout -qb merge feat/a && git merge --no-edit -q feat/b > /dev/null 2>&1) || merge_ok=false

if $merge_ok; then
    log_pass "merge of feat/a + feat/b succeeded without conflict"
else
    (cd "$sandbox" && git status >&2)
    log_fail "04_merge_safety: merge produced a conflict"
fi
