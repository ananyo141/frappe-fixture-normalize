import json
from collections.abc import Iterable

DEFAULT_STRIPPED_KEYS: frozenset[str] = frozenset({"modified"})


def normalize_records(
    records: Iterable[dict],
    extra_strip_keys: Iterable[str] = (),
) -> list[dict]:
    strip = set(DEFAULT_STRIPPED_KEYS) | set(extra_strip_keys)
    cleaned: list[dict] = []
    for record in records:
        if "name" not in record:
            raise KeyError("record missing required 'name' field")
        cleaned.append({k: v for k, v in record.items() if k not in strip})
    cleaned.sort(key=lambda r: r["name"])
    return cleaned


def canonical_dump(records: list[dict]) -> str:
    return json.dumps(records, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
