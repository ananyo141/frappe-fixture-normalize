import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from frappe_fixture_normalize.splitter import scrub_filename, split_records_by


def test_groups_records_by_field():
    records = [
        {"name": "a", "dt": "Issue"},
        {"name": "b", "dt": "Subscription"},
        {"name": "c", "dt": "Issue"},
    ]
    groups = split_records_by(records, field="dt")
    assert set(groups.keys()) == {"Issue", "Subscription"}
    assert [r["name"] for r in groups["Issue"]] == ["a", "c"]
    assert [r["name"] for r in groups["Subscription"]] == ["b"]


def test_missing_split_field_raises():
    records = [{"name": "a"}]
    with pytest.raises(KeyError, match="dt"):
        split_records_by(records, field="dt")


def test_null_split_field_raises():
    records = [{"name": "a", "dt": None}]
    with pytest.raises(ValueError, match="null"):
        split_records_by(records, field="dt")


def test_scrub_filename_matches_frappe_scrub():
    assert scrub_filename("Custom Field") == "custom_field"
    assert scrub_filename("Property Setter") == "property_setter"
    assert scrub_filename("Salary Slip-Detail") == "salary_slip_detail"


def test_empty_input_returns_empty_dict():
    assert split_records_by([], field="dt") == {}
