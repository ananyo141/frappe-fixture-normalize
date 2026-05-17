import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frappe_fixture_normalize.exporter import process_app_fixtures_dir


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def test_flat_file_gets_normalized_when_no_split_configured(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    records = [
        {"name": "Z", "doctype": "Workflow", "modified": "2025-11-01"},
        {"name": "A", "doctype": "Workflow", "modified": "2025-11-02"},
    ]
    flat = fixtures / "workflow.json"
    write_json(flat, records)
    process_app_fixtures_dir(fixtures, split_by_config={})
    out = json.loads(flat.read_text())
    assert [r["name"] for r in out] == ["A", "Z"]
    assert all("modified" not in r for r in out)


def test_split_doctype_creates_per_target_files_and_removes_flat(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    records = [
        {"name": "Issue-foo", "doctype": "Custom Field", "dt": "Issue", "modified": "X"},
        {"name": "Subscription-bar", "doctype": "Custom Field", "dt": "Subscription", "modified": "Y"},
        {"name": "Issue-baz", "doctype": "Custom Field", "dt": "Issue", "modified": "Z"},
    ]
    flat = fixtures / "custom_field.json"
    write_json(flat, records)
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    assert not flat.exists()
    issue_file = fixtures / "custom_field" / "issue.json"
    subscription_file = fixtures / "custom_field" / "subscription.json"
    assert issue_file.exists()
    assert subscription_file.exists()
    issue_records = json.loads(issue_file.read_text())
    assert [r["name"] for r in issue_records] == ["Issue-baz", "Issue-foo"]
    assert all("modified" not in r for r in issue_records)


def test_split_directory_cleared_of_stale_files(tmp_path):
    fixtures = tmp_path / "fixtures"
    (fixtures / "custom_field").mkdir(parents=True)
    stale = fixtures / "custom_field" / "deprecated_doctype.json"
    stale.write_text(json.dumps([{"name": "old", "doctype": "Custom Field", "dt": "Deprecated"}]))
    records = [{"name": "Issue-foo", "doctype": "Custom Field", "dt": "Issue"}]
    flat = fixtures / "custom_field.json"
    write_json(flat, records)
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    assert not stale.exists()
    assert (fixtures / "custom_field" / "issue.json").exists()


def test_property_setter_split_by_doc_type(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    records = [
        {"name": "Issue-prop", "doctype": "Property Setter", "doc_type": "Issue"},
        {"name": "Subscription-prop", "doctype": "Property Setter", "doc_type": "Subscription"},
    ]
    flat = fixtures / "property_setter.json"
    write_json(flat, records)
    process_app_fixtures_dir(fixtures, split_by_config={"Property Setter": "doc_type"})
    assert not flat.exists()
    assert (fixtures / "property_setter" / "issue.json").exists()
    assert (fixtures / "property_setter" / "subscription.json").exists()


def test_idempotent_second_run_produces_identical_bytes(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    records = [
        {"name": "Issue-foo", "doctype": "Custom Field", "dt": "Issue"},
        {"name": "Subscription-bar", "doctype": "Custom Field", "dt": "Subscription"},
    ]
    write_json(fixtures / "custom_field.json", records)
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    issue_first = (fixtures / "custom_field" / "issue.json").read_bytes()
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    issue_second = (fixtures / "custom_field" / "issue.json").read_bytes()
    assert issue_first == issue_second


def test_existing_split_files_reread_when_flat_missing(tmp_path):
    """After first export, a re-run with no flat file (because we deleted it)
    should still produce a clean normalized output from the split files."""
    fixtures = tmp_path / "fixtures"
    sub = fixtures / "custom_field"
    sub.mkdir(parents=True)
    write_json(
        sub / "issue.json",
        [{"name": "Issue-zzz", "doctype": "Custom Field", "dt": "Issue", "modified": "X"}],
    )
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    out = json.loads((sub / "issue.json").read_text())
    assert "modified" not in out[0]


def test_empty_fixtures_dir_noop(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    assert list(fixtures.iterdir()) == []


def test_missing_fixtures_dir_noop(tmp_path):
    process_app_fixtures_dir(tmp_path / "does_not_exist", split_by_config={})


def test_corrupted_flat_file_skipped(tmp_path):
    """A flat file with malformed JSON must not crash the run; it is left
    untouched so a human can inspect."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    bad = fixtures / "workflow.json"
    bad.write_text("{not json")
    process_app_fixtures_dir(fixtures, split_by_config={})
    assert bad.read_text() == "{not json"


def test_corrupted_split_file_skipped_on_reread(tmp_path):
    """When re-collecting records from an existing split subdir, a malformed
    member file is skipped rather than aborting the export."""
    fixtures = tmp_path / "fixtures"
    sub = fixtures / "custom_field"
    sub.mkdir(parents=True)
    bad = sub / "broken.json"
    bad.write_text("{broken")
    good = sub / "issue.json"
    write_json(good, [{"name": "Issue-foo", "doctype": "Custom Field", "dt": "Issue"}])
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    # Good file is rewritten into the correct split location.
    assert (sub / "issue.json").exists()
    issue_records = json.loads((sub / "issue.json").read_text())
    assert [r["name"] for r in issue_records] == ["Issue-foo"]


def test_single_record_array_handled(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    records = [{"name": "Issue-foo", "doctype": "Custom Field", "dt": "Issue"}]
    write_json(fixtures / "custom_field.json", records)
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    assert (fixtures / "custom_field" / "issue.json").exists()
    out = json.loads((fixtures / "custom_field" / "issue.json").read_text())
    assert [r["name"] for r in out] == ["Issue-foo"]


def test_subdir_with_only_non_json_treated_as_empty(tmp_path):
    """If a split subdir exists but contains no `.json` files, behave as if
    the doctype has no records on disk."""
    fixtures = tmp_path / "fixtures"
    sub = fixtures / "custom_field"
    sub.mkdir(parents=True)
    (sub / "README.md").write_text("notes")
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    # README untouched, no spurious json files written.
    assert (sub / "README.md").exists()
    assert list(sub.glob("*.json")) == []


def test_split_config_for_unseen_doctype_is_noop(tmp_path):
    """A doctype configured for splitting but with no flat file and no subdir
    must not error and must not create empty artifacts."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    assert list(fixtures.iterdir()) == []


def test_non_array_top_level_json_skipped(tmp_path):
    """A `*.json` file at the top of fixtures/ whose root is an object (not a
    list of records) must be left untouched — it isn't a fixture file."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    meta = fixtures / "metadata.json"
    meta.write_text(json.dumps({"version": 1}))
    process_app_fixtures_dir(fixtures, split_by_config={})
    assert json.loads(meta.read_text()) == {"version": 1}


def test_split_subdir_non_list_json_member_ignored(tmp_path):
    """Inside a split subdir, a `.json` file that is an object (not array) is
    skipped during reread — does not raise."""
    fixtures = tmp_path / "fixtures"
    sub = fixtures / "custom_field"
    sub.mkdir(parents=True)
    (sub / "object.json").write_text(json.dumps({"not": "an array"}))
    (sub / "issue.json").write_text(json.dumps([{"name": "Issue-foo", "doctype": "Custom Field", "dt": "Issue"}]))
    process_app_fixtures_dir(fixtures, split_by_config={"Custom Field": "dt"})
    out = json.loads((sub / "issue.json").read_text())
    assert [r["name"] for r in out] == ["Issue-foo"]
