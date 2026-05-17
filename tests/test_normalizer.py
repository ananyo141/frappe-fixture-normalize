import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frappe_fixture_normalize.normalizer import (
    DEFAULT_STRIPPED_KEYS,
    canonical_dump,
    normalize_records,
)


def test_records_sorted_alphabetically_by_name():
    records = [
        {"name": "Z-thing", "doctype": "Custom Field"},
        {"name": "A-thing", "doctype": "Custom Field"},
        {"name": "M-thing", "doctype": "Custom Field"},
    ]
    out = normalize_records(records)
    assert [r["name"] for r in out] == ["A-thing", "M-thing", "Z-thing"]


def test_modified_field_stripped_by_default():
    records = [
        {"name": "A", "doctype": "Custom Field", "modified": "2025-11-01 10:00:00"},
    ]
    out = normalize_records(records)
    assert "modified" not in out[0]


def test_default_stripped_keys_includes_modified():
    assert "modified" in DEFAULT_STRIPPED_KEYS


def test_extra_strip_keys_honored():
    records = [{"name": "A", "doctype": "Custom Field", "foo": 1, "bar": 2}]
    out = normalize_records(records, extra_strip_keys={"foo"})
    assert "foo" not in out[0]
    assert out[0]["bar"] == 2


def test_input_records_not_mutated():
    records = [{"name": "A", "doctype": "Custom Field", "modified": "X"}]
    normalize_records(records)
    assert records[0]["modified"] == "X"


def test_canonical_dump_indent_one_sort_keys_trailing_newline():
    records = [{"name": "A", "doctype": "Custom Field"}]
    out = canonical_dump(records)
    assert out.endswith("\n")
    parsed = json.loads(out)
    assert parsed == records
    lines = out.splitlines()
    assert lines[0] == "["
    keys_line = next(line for line in lines if "doctype" in line)
    name_line = next(line for line in lines if "name" in line)
    assert lines.index(keys_line) < lines.index(name_line)


def test_canonical_dump_non_ascii_preserved():
    records = [{"name": "A", "label": "café"}]
    out = canonical_dump(records)
    assert "café" in out


def test_normalize_records_stable_sort_for_duplicate_names():
    records = [
        {"name": "A", "doctype": "Custom Field", "fieldname": "second"},
        {"name": "A", "doctype": "Custom Field", "fieldname": "first"},
    ]
    out = normalize_records(records)
    assert [r["fieldname"] for r in out] == ["second", "first"]


def test_record_missing_name_raises():
    records = [{"doctype": "Custom Field"}]
    try:
        normalize_records(records)
    except KeyError as e:
        assert "name" in str(e)
    else:
        raise AssertionError("expected KeyError for missing 'name'")
