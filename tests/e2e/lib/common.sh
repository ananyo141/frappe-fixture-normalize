#!/usr/bin/env bash
# Shared helpers for e2e scripts. Source from each scenario.
#
# Required env (set by run_all.sh or caller):
#   BENCH_DIR  — absolute path to the bench root (e.g. /workspace/frappe-bench)
#   SITE       — site name (e.g. myapp.localhost)
#   APP        — consumer app under test (e.g. myapp)
#
# Optional env for scripts that insert Custom Fields (03, 04):
#   MODULE     — Frappe module to tag the inserted Custom Field with so
#                the consumer app's `fixtures` hook picks it up. Defaults
#                to "Custom" — override to match your consumer's filter.
#
# Optional:
#   FIXTURES_DIR — absolute path to <bench>/apps/<APP>/<APP>/fixtures (auto-derived)

set -euo pipefail

: "${BENCH_DIR:?BENCH_DIR must be set}"
: "${SITE:?SITE must be set}"
: "${APP:?APP must be set}"

FIXTURES_DIR="${FIXTURES_DIR:-$BENCH_DIR/apps/$APP/$APP/fixtures}"
APP_REPO_DIR="$(dirname "$FIXTURES_DIR")"
APP_REPO_DIR="$(dirname "$APP_REPO_DIR")"

# Track temp resources for cleanup.
__E2E_TEMP_DIRS=()
__E2E_TEMP_FIELDS=()

cleanup_on_exit() {
    local exit_code=$?
    set +e  # don't let cleanup failures override the test result
    for tmp in "${__E2E_TEMP_DIRS[@]:-}"; do
        [ -n "$tmp" ] && [ -d "$tmp" ] && rm -rf "$tmp" 2>/dev/null
    done
    for cf in "${__E2E_TEMP_FIELDS[@]:-}"; do
        [ -n "$cf" ] && delete_custom_field "$cf" 2>/dev/null
    done
    exit "$exit_code"
}
trap cleanup_on_exit EXIT

register_temp_dir() { __E2E_TEMP_DIRS+=("$1"); }
register_temp_field() { __E2E_TEMP_FIELDS+=("$1"); }

# bench_exec ARGS... → run `bench --site $SITE ARGS...` inside the bench root.
bench_exec() {
    (cd "$BENCH_DIR" && bench --site "$SITE" "$@")
}

# bench_run ARGS... → run `bench ARGS...` (no site).
bench_run() {
    (cd "$BENCH_DIR" && bench "$@")
}

# Insert a Custom Field via frappe.client.insert. First arg = dt, second = fieldname.
# Returns the inserted name on stdout.
insert_custom_field() {
    local dt="$1"; local fieldname="$2"; local module="${3:-Custom}"
    bench_exec execute frappe.client.insert --kwargs "{
        'doc': {
            'doctype': 'Custom Field',
            'dt': '$dt',
            'fieldname': '$fieldname',
            'fieldtype': 'Data',
            'label': '$fieldname',
            'module': '$module'
        }
    }" > /dev/null
    echo "${dt}-${fieldname}"
}

delete_custom_field() {
    local name="$1"
    bench_exec execute frappe.client.delete --kwargs "{
        'doctype': 'Custom Field',
        'name': '$name'
    }" > /dev/null 2>&1 || true
}

# Snapshot the fixtures dir to a temp tarball; restore_fixtures_snapshot reverts.
snapshot_fixtures() {
    local snap; snap="$(mktemp -d)"
    register_temp_dir "$snap"
    (cd "$APP_REPO_DIR" && tar cf "$snap/fixtures.tar" fixtures 2>/dev/null) || true
    echo "$snap/fixtures.tar"
}

restore_fixtures_snapshot() {
    local tar_path="$1"
    [ -f "$tar_path" ] || return 0
    (cd "$APP_REPO_DIR" && rm -rf fixtures && tar xf "$tar_path")
}

# Compare two file trees; exits 1 with diff on stderr if they differ.
assert_trees_match() {
    local a="$1"; local b="$2"
    if ! diff -ru "$a" "$b" > /dev/null; then
        echo "tree mismatch between $a and $b:" >&2
        diff -ru "$a" "$b" >&2 || true
        return 1
    fi
}

# Hash every file under a directory; output is `<hash>  <relative-path>` lines.
hash_tree() {
    local root="$1"
    (cd "$root" && find . -type f | sort | xargs md5sum 2>/dev/null || \
        find "$root" -type f | sort | xargs -I {} md5 -r {} | awk '{print $1"  "$2}')
}

log_pass() { echo "✓ PASS: $1"; }
log_fail() { echo "✗ FAIL: $1" >&2; exit 1; }

# Query Custom Field count by name using bench's mariadb command. The SQL
# is fed via stdin so shell quoting through nested ssh layers doesn't mangle
# parens/backticks.
cf_count_by_name() {
    local cf_name="$1"
    (cd "$BENCH_DIR" && bench --site "$SITE" mariadb 2>/dev/null) <<SQL | awk 'NR==2 {print $1}'
SELECT COUNT(*) FROM \`tabCustom Field\` WHERE name='${cf_name}';
SQL
}
