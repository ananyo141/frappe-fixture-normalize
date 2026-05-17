"""Default split-by configuration for fixture export.

Override per consumer app by setting `fixture_normalize_split_by` in hooks.py:

    fixture_normalize_split_by = {
        "Custom Field": "dt",
        "Property Setter": "doc_type",
        "Workflow": "document_type",
    }
"""

DEFAULT_SPLIT_BY: dict[str, str] = {
    "Custom Field": "dt",
    "Property Setter": "doc_type",
}
