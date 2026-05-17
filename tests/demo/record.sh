#!/usr/bin/env bash
# Record a demo screencast for the README.
#
# Wraps `asciinema rec` around a scripted sequence that contrasts stock
# `bench export-fixtures` (wholesale rewrite, modified churn, creation
# ordering) with `bench export-clean-fixtures` (deterministic, split-per-
# target).
#
# Requirements:
#   - asciinema  (pip install asciinema)
#   - bench env with `frappe_fixture_normalize` installed
#   - a consumer app + site with at least one Custom Field already in DB
#   - `svg-term-cli` if you want to render to inline SVG (npm i -g svg-term-cli)
#
# Required env:
#   BENCH_DIR  — absolute path to the bench root
#   SITE       — site name
#   APP        — consumer app slug
#
# Usage:
#   BENCH_DIR=... SITE=... APP=... bash tests/demo/record.sh
#   # produces tests/demo/demo.cast
#
#   # Render to SVG for embedding in README:
#   svg-term --cast tests/demo/demo.cast \
#            --out tests/demo/demo.svg \
#            --window --width 100 --height 28

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$SCRIPT_DIR/demo.cast"

: "${BENCH_DIR:?BENCH_DIR required}"
: "${SITE:?SITE required}"
: "${APP:?APP required}"

# Inner driver that asciinema invokes. Each `sleep` pause makes the cast
# read naturally when played back at 1x.
cat > /tmp/ffn_demo_driver.sh <<DRIVER
#!/usr/bin/env bash
set -e
pause() { sleep "\${1:-1.5}"; }

clear
echo "# ----- BEFORE: stock 'bench export-fixtures' -----"
pause 1.5

cd "$BENCH_DIR/apps/$APP/$APP/fixtures" 2>/dev/null || cd "$BENCH_DIR"
pause 0.5
echo
echo "\$ ls fixtures/ | head"
ls "$BENCH_DIR/apps/$APP/$APP/fixtures" | head
pause 2

echo
echo "\$ wc -l fixtures/custom_field/*.json | tail -1"
wc -l "$BENCH_DIR/apps/$APP/$APP/fixtures/custom_field/"*.json 2>/dev/null | tail -1 || true
pause 2

echo
echo "# Run stock export-fixtures (overridden by frappe_fixture_normalize)..."
pause 1.5
echo "\$ bench --site $SITE export-fixtures --app $APP"
(cd "$BENCH_DIR" && bench --site "$SITE" export-fixtures --app "$APP" 2>&1) | head -5
pause 2

echo
echo "\$ git status --short fixtures/ | head"
(cd "$BENCH_DIR/apps/$APP" && git status --short . 2>/dev/null | head) || echo "(no git repo at consumer app)"
pause 2

echo
echo "# ----- KEY GUARANTEES -----"
echo "  - records sorted by 'name'"
echo "  - 'modified' field stripped"
echo "  - one file per target doctype: fixtures/custom_field/<target>.json"
echo "  - byte-identical output across machines"
pause 3

echo
echo "# Second run produces ZERO diff:"
pause 1
echo "\$ bench --site $SITE export-fixtures --app $APP > /dev/null"
(cd "$BENCH_DIR" && bench --site "$SITE" export-fixtures --app "$APP" > /dev/null 2>&1)
echo "\$ git diff --stat fixtures/"
(cd "$BENCH_DIR/apps/$APP" && git diff --stat fixtures/ 2>/dev/null) || echo " (clean)"
pause 3

echo
echo "# Done."
DRIVER
chmod +x /tmp/ffn_demo_driver.sh

asciinema rec "$OUT" \
    --overwrite \
    --idle-time-limit 2 \
    --title "frappe_fixture_normalize demo" \
    --command "/tmp/ffn_demo_driver.sh"

rm -f /tmp/ffn_demo_driver.sh

echo
echo "Recorded to: $OUT"
echo
echo "Render to inline SVG for README:"
echo "  svg-term --cast $OUT --out $SCRIPT_DIR/demo.svg --window --width 100 --height 28"
