import re
from collections import defaultdict
from collections.abc import Iterable


def split_records_by(records: Iterable[dict], field: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if field not in record:
            raise KeyError(f"record missing required split field {field!r}: {record.get('name')!r}")
        value = record[field]
        if value is None or value == "":
            raise ValueError(
                f"record {record.get('name')!r} has null/empty split field {field!r}; cannot place in a file"
            )
        groups[value].append(record)
    return dict(groups)


def scrub_filename(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
