import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frappe_fixture_normalize.loader import iter_split_fixture_files


def test_iter_yields_paths_under_subdirs_only(tmp_path):
    fixtures = tmp_path / "fixtures"
    (fixtures / "custom_field").mkdir(parents=True)
    (fixtures / "property_setter").mkdir(parents=True)
    flat = fixtures / "workflow.json"
    flat.write_text("[]")
    a = fixtures / "custom_field" / "issue.json"
    b = fixtures / "custom_field" / "subscription.json"
    c = fixtures / "property_setter" / "issue.json"
    for p in (a, b, c):
        p.write_text("[]")

    paths = sorted(iter_split_fixture_files(tmp_path))
    assert paths == sorted([a, b, c])


def test_iter_returns_empty_when_no_fixtures_dir(tmp_path):
    assert list(iter_split_fixture_files(tmp_path)) == []


def test_iter_skips_non_json_files(tmp_path):
    sub = tmp_path / "fixtures" / "custom_field"
    sub.mkdir(parents=True)
    (sub / "issue.json").write_text("[]")
    (sub / "README.md").write_text("notes")
    paths = list(iter_split_fixture_files(tmp_path))
    assert all(p.suffix == ".json" for p in paths)
    assert len(paths) == 1


def test_iter_deterministic_order(tmp_path):
    sub = tmp_path / "fixtures" / "custom_field"
    sub.mkdir(parents=True)
    for n in ["zeta", "alpha", "mu"]:
        (sub / f"{n}.json").write_text("[]")
    paths = list(iter_split_fixture_files(tmp_path))
    assert [p.name for p in paths] == ["alpha.json", "mu.json", "zeta.json"]
