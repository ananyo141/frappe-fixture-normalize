import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_MODULE = "frappe_fixture_normalize.pre_commit_hook"


def run_hook(*paths: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", HOOK_MODULE, *map(str, paths)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_already_canonical_file_returns_zero(tmp_path):
    records = [{"name": "A", "doctype": "Custom Field"}, {"name": "B", "doctype": "Custom Field"}]
    path = tmp_path / "custom_field.json"
    path.write_text(json.dumps(records, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    result = run_hook(path)
    assert result.returncode == 0, result.stderr
    rewritten = path.read_text()
    assert rewritten.endswith("\n")


def test_rewrites_unsorted_input_and_returns_nonzero(tmp_path):
    records = [
        {"name": "Z", "doctype": "Custom Field", "modified": "2025-01-01"},
        {"name": "A", "doctype": "Custom Field", "modified": "2025-01-02"},
    ]
    path = tmp_path / "custom_field.json"
    path.write_text(json.dumps(records))
    result = run_hook(path)
    assert result.returncode != 0
    after = json.loads(path.read_text())
    assert [r["name"] for r in after] == ["A", "Z"]
    assert all("modified" not in r for r in after)


def test_handles_multiple_files(tmp_path):
    clean_records = [{"name": "A"}]
    dirty_records = [{"name": "B", "modified": "2025-01-01"}, {"name": "A"}]
    clean = tmp_path / "clean.json"
    dirty = tmp_path / "dirty.json"
    clean.write_text(json.dumps(clean_records, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    dirty.write_text(json.dumps(dirty_records))
    result = run_hook(clean, dirty)
    assert result.returncode != 0
    assert clean.read_text().endswith("\n")
    after_dirty = json.loads(dirty.read_text())
    assert [r["name"] for r in after_dirty] == ["A", "B"]


def test_non_array_file_skipped_silently(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps({"key": "value"}, indent=1))
    result = run_hook(path)
    assert result.returncode == 0
    assert json.loads(path.read_text()) == {"key": "value"}


def test_invalid_json_returns_nonzero(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("not json")
    result = run_hook(path)
    assert result.returncode != 0
    assert "broken.json" in result.stderr
