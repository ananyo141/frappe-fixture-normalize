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


def test_oserror_on_unreadable_file_returns_nonzero(tmp_path):
    import os
    import stat

    path = tmp_path / "locked.json"
    path.write_text(json.dumps([{"name": "A"}]))
    # Strip all read bits. Root bypasses DAC so skip when running as uid 0.
    if os.geteuid() == 0:
        return
    path.chmod(0)
    try:
        result = run_hook(path)
        assert result.returncode != 0
        assert "locked.json" in result.stderr
    finally:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_normalization_error_reported(tmp_path):
    """A record missing the required `name` field should surface as a hook failure
    rather than crash the process."""
    path = tmp_path / "broken.json"
    path.write_text(json.dumps([{"doctype": "Custom Field"}]))
    result = run_hook(path)
    assert result.returncode != 0
    assert "broken.json" in result.stderr
    assert "name" in result.stderr


# --- In-process tests for coverage ---------------------------------------
#
# The subprocess-based tests above validate the CLI contract; the in-process
# tests below import the module directly so coverage is measured.

from frappe_fixture_normalize.pre_commit_hook import main, process_file  # noqa: E402


def test_process_file_returns_false_for_canonical_file(tmp_path):
    records = [{"name": "A"}]
    path = tmp_path / "ok.json"
    path.write_text(json.dumps(records, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    changed, error = process_file(path)
    assert changed is False
    assert error is None


def test_process_file_returns_true_for_rewrite(tmp_path):
    records = [{"name": "B", "modified": "X"}, {"name": "A"}]
    path = tmp_path / "dirty.json"
    path.write_text(json.dumps(records))
    changed, error = process_file(path)
    assert changed is True
    assert error is None
    after = json.loads(path.read_text())
    assert [r["name"] for r in after] == ["A", "B"]
    assert all("modified" not in r for r in after)


def test_process_file_returns_error_for_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json")
    changed, error = process_file(path)
    assert changed is False
    assert error is not None
    assert "bad.json" in error


def test_process_file_returns_none_error_for_dict(tmp_path):
    path = tmp_path / "meta.json"
    path.write_text(json.dumps({"k": "v"}))
    changed, error = process_file(path)
    assert changed is False
    assert error is None


def test_process_file_returns_error_for_normalization_failure(tmp_path):
    path = tmp_path / "noname.json"
    path.write_text(json.dumps([{"doctype": "Custom Field"}]))
    changed, error = process_file(path)
    assert changed is False
    assert error is not None
    assert "name" in error


def test_process_file_returns_oserror_message_when_unreadable(tmp_path):
    import os
    import stat

    if os.geteuid() == 0:
        return
    path = tmp_path / "locked.json"
    path.write_text(json.dumps([{"name": "A"}]))
    path.chmod(0)
    try:
        changed, error = process_file(path)
        assert changed is False
        assert error is not None
        assert "locked.json" in error
    finally:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_main_returns_zero_when_no_changes(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps([{"name": "A"}], indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    assert main([str(p)]) == 0


def test_main_returns_one_when_rewrites(tmp_path, capsys):
    p = tmp_path / "x.json"
    p.write_text(json.dumps([{"name": "B"}, {"name": "A"}]))
    rc = main([str(p)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "normalized" in captured.err


def test_main_returns_one_when_error(tmp_path, capsys):
    p = tmp_path / "broken.json"
    p.write_text("nope")
    rc = main([str(p)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "broken.json" in captured.err


def test_main_empty_args_returns_zero():
    assert main([]) == 0
