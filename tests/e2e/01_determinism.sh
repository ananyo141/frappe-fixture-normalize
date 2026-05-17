#!/usr/bin/env bash
# Scenario 01: Determinism on the same machine.
#
# Two consecutive `export-clean-fixtures --app $APP` runs against an unchanged
# DB must produce byte-identical files on disk.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

snap="$(snapshot_fixtures)"
register_temp_dir "$(dirname "$snap")"

bench_exec export-clean-fixtures --app "$APP" > /dev/null
hash_a="$(hash_tree "$FIXTURES_DIR")"

bench_exec export-clean-fixtures --app "$APP" > /dev/null
hash_b="$(hash_tree "$FIXTURES_DIR")"

restore_fixtures_snapshot "$snap"

if [ "$hash_a" = "$hash_b" ]; then
    log_pass "two consecutive exports produced identical file trees"
else
    diff <(echo "$hash_a") <(echo "$hash_b") >&2 || true
    log_fail "01_determinism: file tree differed between runs"
fi
