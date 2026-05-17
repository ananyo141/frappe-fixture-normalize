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
