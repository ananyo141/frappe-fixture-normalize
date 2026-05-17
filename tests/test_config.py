import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frappe_fixture_normalize.config import DEFAULT_SPLIT_BY


def test_default_split_by_includes_custom_field_and_property_setter():
    assert DEFAULT_SPLIT_BY["Custom Field"] == "dt"
    assert DEFAULT_SPLIT_BY["Property Setter"] == "doc_type"


def test_default_split_by_is_mapping():
    assert isinstance(DEFAULT_SPLIT_BY, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in DEFAULT_SPLIT_BY.items())
