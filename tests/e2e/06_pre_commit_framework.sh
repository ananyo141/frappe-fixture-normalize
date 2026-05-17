#!/usr/bin/env bash
# Scenario 06: Pre-commit framework integration.
#
# Install the `pre-commit` package, wire up a `.pre-commit-config.yaml`
# pointing at our hook, hand-edit a fixture (re-add `modified`), run
# `pre-commit run --files <file>`. The hook must rewrite the file (exit 1
# first run, exit 0 second run).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

if ! command -v pre-commit > /dev/null 2>&1; then
    if ! python3 -m pip install --quiet pre-commit; then
        echo "↷ SKIP 06_pre_commit_framework: pre-commit not installable"
        exit 0
    fi
fi

work="$(mktemp -d)"; register_temp_dir "$work"

# Stand up a tiny git repo containing one canonical fixture file.
(cd "$work"
 git init -q
 git config user.email t@e && git config user.name T
 mkdir -p fixtures/custom_field
 cat > fixtures/custom_field/issue.json <<'JSON'
[
 {
  "doctype": "Custom Field",
  "dt": "Issue",
  "fieldname": "test_e2e_pc",
  "name": "Issue-test_e2e_pc"
 }
]
JSON
 # Resolve which python has our package importable: try bench env first, then
 # system python. Pre-commit's `language: system` runs the entry verbatim.
 PY="$BENCH_DIR/env/bin/python"
 if ! "$PY" -c "import frappe_fixture_normalize" 2>/dev/null; then
     PY="$(command -v python3)"
 fi

 cat > .pre-commit-config.yaml <<YAML
repos:
  - repo: local
    hooks:
      - id: normalize-fixtures
        name: Normalize Frappe fixture JSON
        entry: $PY -m frappe_fixture_normalize.pre_commit_hook
        language: system
        files: (^|/)fixtures/.*\.json\$
YAML
 git add -A && git commit -qm baseline
)

# Hand-edit: re-insert a `modified` timestamp and unsorted records.
cat > "$work/fixtures/custom_field/issue.json" <<'JSON'
[
 {"name": "Issue-zzz", "doctype": "Custom Field", "dt": "Issue", "modified": "2025-01-01"},
 {"name": "Issue-aaa", "doctype": "Custom Field", "dt": "Issue"}
]
JSON

rc=0
(cd "$work" && pre-commit run --files fixtures/custom_field/issue.json) > /dev/null 2>&1 || rc=$?

if [ "$rc" -eq 0 ]; then
    log_fail "06_pre_commit_framework: hook should have failed on dirty file (rc=$rc)"
fi

# Hook should have rewritten the file. Second run is clean.
if grep -q '"modified"' "$work/fixtures/custom_field/issue.json"; then
    log_fail "06_pre_commit_framework: modified field not stripped after hook run"
fi

(cd "$work" && pre-commit run --files fixtures/custom_field/issue.json) > /dev/null 2>&1
log_pass "pre-commit hook rewrote dirty fixture; second run was clean"
