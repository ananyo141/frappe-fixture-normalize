# Demo assets

Two artifacts here:

| File | Purpose |
|---|---|
| `record.sh` | Driver that wraps `asciinema rec` around a scripted export sequence on a real bench |
| `demo.cast` | Hand-crafted asciinema v2 cast that ships with the repo so the README has a demo without anyone running `asciinema rec` |

## Render the cast to inline SVG (for README)

```bash
npm i -g svg-term-cli
svg-term --cast demo.cast --out demo.svg --window --width 100 --height 28
```

The resulting `demo.svg` is self-contained (no JS, no external deps) and embeds inline in any GitHub-flavored markdown:

```markdown
![Demo](tests/demo/demo.svg)
```

## Re-record against a real bench

The shipped `demo.cast` is hand-crafted with realistic-looking output to keep the demo deterministic and offline. To capture an actual run against your bench:

```bash
pip install asciinema
BENCH_DIR=/path/to/frappe-bench \
SITE=myapp.localhost \
APP=myapp \
bash tests/demo/record.sh
# Overwrites tests/demo/demo.cast
```

Requirements for the live record:

- `asciinema` installed (`pip install asciinema`).
- The consumer app has at least one Custom Field with `module` matching your `hooks.fixtures` filter.
- The consumer app's `fixtures/` directory is inside a git repo (so the `git diff --stat` line in the demo has something to display).

## Why not record once with a real run?

- Live recordings drift with the bench's actual record counts and timing — harder to keep stable across releases.
- The hand-crafted cast is reproducible by `git checkout` alone; readers don't need bench access.
- Live recordings can still replace it at any time — same filename, same playback contract.
