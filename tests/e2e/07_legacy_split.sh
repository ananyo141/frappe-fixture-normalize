#!/usr/bin/env bash
# Scenario 07: One-time legacy split.
#
# Take an existing flat `custom_field.json` (the pre-app world), run
# `bench normalize-fixtures --app $APP`, and confirm the flat file is split
# into per-target files with no record loss.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

snap="$(snapshot_fixtures)"

# Materialize a legacy flat file by concatenating the existing split records.
flat_records="$(mktemp)"; register_temp_dir "$(dirname "$flat_records")"
python3 - <<PY > "$flat_records"
import json, sys, os
root = "$FIXTURES_DIR/custom_field"
out = []
if os.path.isdir(root):
    for n in sorted(os.listdir(root)):
        if not n.endswith('.json'): continue
        with open(os.path.join(root, n)) as f:
            out.extend(json.load(f))
print(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False))
PY

if [ ! -s "$flat_records" ] || [ "$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$flat_records")" = "0" ]; then
    echo "↷ SKIP 07_legacy_split: no split fixtures to back-fill from"
    exit 0
fi

# Strip the existing split dir, write the flat file.
rm -rf "$FIXTURES_DIR/custom_field"
mv "$flat_records" "$FIXTURES_DIR/custom_field.json"

expected_total="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$FIXTURES_DIR/custom_field.json")"

bench_exec normalize-fixtures --app "$APP" > /dev/null

# Flat should be gone; split dir should hold the same total record count.
if [ -f "$FIXTURES_DIR/custom_field.json" ]; then
    log_fail "07_legacy_split: flat file not removed"
fi

total="$(python3 -c "
import json, sys, os
root = sys.argv[1]
total = 0
for n in sorted(os.listdir(root)):
    if n.endswith('.json'):
        with open(os.path.join(root, n)) as f:
            total += len(json.load(f))
print(total)
" "$FIXTURES_DIR/custom_field")"
restore_fixtures_snapshot "$snap"

if [ "$total" = "$expected_total" ]; then
    log_pass "legacy flat file ($expected_total records) split with no loss"
else
    log_fail "07_legacy_split: record count drifted (expected $expected_total, got $total)"
fi
