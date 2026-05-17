#!/usr/bin/env bash
# Scenario 02: Cross-machine determinism (simulated).
#
# Real cross-machine testing needs two hosts. We simulate by dumping the DB,
# restoring into a second site, exporting on both, and diffing the resulting
# files.
#
# This scenario is OPTIONAL — skipped unless E2E_CROSS_MACHINE=1 in env.
# When skipped, exits 0 with a SKIP message.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

if [ "${E2E_CROSS_MACHINE:-0}" != "1" ]; then
    echo "↷ SKIP 02_cross_machine: set E2E_CROSS_MACHINE=1 to enable (requires a second test site)"
    exit 0
fi

: "${ALT_SITE:?ALT_SITE required when E2E_CROSS_MACHINE=1}"

snap="$(snapshot_fixtures)"

# Export on primary site.
bench_exec export-clean-fixtures --app "$APP" > /dev/null
primary="$(mktemp -d)"; register_temp_dir "$primary"
cp -r "$FIXTURES_DIR/." "$primary/"

# Dump primary DB → restore on alt site → export there.
dump="$(mktemp -d)"; register_temp_dir "$dump"
bench_exec backup --backup-path-db "$dump/db.sql.gz" --backup-path-files "$dump/files.tar" \
    --backup-path-private-files "$dump/private.tar" > /dev/null
SITE="$ALT_SITE" bench_exec restore "$dump/db.sql.gz" > /dev/null
SITE="$ALT_SITE" bench_exec export-clean-fixtures --app "$APP" > /dev/null

alt="$(mktemp -d)"; register_temp_dir "$alt"
cp -r "$FIXTURES_DIR/." "$alt/"

restore_fixtures_snapshot "$snap"

if assert_trees_match "$primary" "$alt"; then
    log_pass "fixture trees identical across two sites with identical DB state"
else
    log_fail "02_cross_machine: trees diverged"
fi
