# Feature → Test Traceability

This document is the source of truth for "100% feature coverage". Every public
behavior of `frappe_fixture_normalize` is listed below with the test that
asserts it. The combination of `pytest --cov` ≥ 99% and a green row for every
feature here is the contract.

Layers:
- **L1** — pure pytest under `tests/`. No frappe required.
- **L2** — frappe-bench integration under `frappe_fixture_normalize/tests/`.
  Discovered by `bench run-tests --app frappe_fixture_normalize`.
- **L3** — shell e2e under `tests/e2e/`. Manual / nightly local.

## Pure-module behaviors

| # | Feature | Layer | Test |
|---|---------|-------|------|
| 1 | Sort records by `name` | L1 | `test_normalizer.py::test_records_sorted_alphabetically_by_name` |
| 2 | Strip default keys (`modified`) | L1 | `test_normalizer.py::test_modified_field_stripped_by_default` |
| 3 | Strip extra keys | L1 | `test_normalizer.py::test_extra_strip_keys_honored` |
| 4 | Input immutability | L1 | `test_normalizer.py::test_input_records_not_mutated` |
| 5 | Missing `name` → KeyError | L1 | `test_normalizer.py::test_record_missing_name_raises` |
| 6 | Stable sort on duplicate names | L1 | `test_normalizer.py::test_normalize_records_stable_sort_for_duplicate_names` |
| 7 | Canonical JSON dump format | L1 | `test_normalizer.py::test_canonical_dump_indent_one_sort_keys_trailing_newline` |
| 8 | Non-ASCII preserved | L1 | `test_normalizer.py::test_canonical_dump_non_ascii_preserved` |
| 9 | Default stripped keys exposes `modified` | L1 | `test_normalizer.py::test_default_stripped_keys_includes_modified` |
| 10 | Group records by split field | L1 | `test_splitter.py::test_groups_records_by_field` |
| 11 | Missing split field → KeyError | L1 | `test_splitter.py::test_missing_split_field_raises` |
| 12 | Null/empty split field → ValueError | L1 | `test_splitter.py::test_null_split_field_raises` |
| 13 | Empty input → empty dict | L1 | `test_splitter.py::test_empty_input_returns_empty_dict` |
| 14 | `scrub_filename` parity with frappe.scrub | L1 | `test_splitter.py::test_scrub_filename_matches_frappe_scrub` |
| 15 | Default split-by config | L1 | `test_config.py::test_default_split_by_includes_custom_field_and_property_setter` |
| 16 | Default split-by is a mapping | L1 | `test_config.py::test_default_split_by_is_mapping` |

## Exporter (post-process)

| # | Feature | Layer | Test |
|---|---------|-------|------|
| 17 | Flat file normalize in place | L1 | `test_exporter.py::test_flat_file_gets_normalized_when_no_split_configured` |
| 18 | Split flat → per-target subdir | L1 | `test_exporter.py::test_split_doctype_creates_per_target_files_and_removes_flat` |
| 19 | Stale split file removed | L1 | `test_exporter.py::test_split_directory_cleared_of_stale_files` |
| 20 | Property Setter split by `doc_type` | L1 | `test_exporter.py::test_property_setter_split_by_doc_type` |
| 21 | Idempotent re-export | L1 | `test_exporter.py::test_idempotent_second_run_produces_identical_bytes` |
| 22 | Re-read split subdir when flat absent | L1 | `test_exporter.py::test_existing_split_files_reread_when_flat_missing` |
| 23 | Empty fixtures dir is no-op | L1 | `test_exporter.py::test_empty_fixtures_dir_noop` |
| 24 | Missing fixtures dir is no-op | L1 | `test_exporter.py::test_missing_fixtures_dir_noop` |
| 25 | Corrupted flat file skipped | L1 | `test_exporter.py::test_corrupted_flat_file_skipped` |
| 26 | Corrupted split member skipped on reread | L1 | `test_exporter.py::test_corrupted_split_file_skipped_on_reread` |
| 27 | Single-record array handled | L1 | `test_exporter.py::test_single_record_array_handled` |
| 28 | Subdir with no `.json` is no-op | L1 | `test_exporter.py::test_subdir_with_only_non_json_treated_as_empty` |
| 29 | Split config for absent doctype is no-op | L1 | `test_exporter.py::test_split_config_for_unseen_doctype_is_noop` |
| 30 | Top-level non-array `.json` left alone | L1 | `test_exporter.py::test_non_array_top_level_json_skipped` |
| 31 | Non-list member inside split subdir ignored | L1 | `test_exporter.py::test_split_subdir_non_list_json_member_ignored` |

## Loader

| # | Feature | Layer | Test |
|---|---------|-------|------|
| 32 | Iter yields subdir json only | L1 | `test_loader.py::test_iter_yields_paths_under_subdirs_only` |
| 33 | Iter empty when no fixtures dir | L1 | `test_loader.py::test_iter_returns_empty_when_no_fixtures_dir` |
| 34 | Iter skips non-json | L1 | `test_loader.py::test_iter_skips_non_json_files` |
| 35 | Iter deterministic order | L1 | `test_loader.py::test_iter_deterministic_order` |
| 36 | `import_split_fixtures` skips broken app | L1 | `test_loader.py::test_import_split_fixtures_skips_broken_app` |
| 37 | `import_split_fixtures` logs + continues on import error | L1 | `test_loader.py::test_import_split_fixtures_logs_and_continues_on_import_failure` |
| 38 | Loader: restore deleted record on real bench | L2 | `frappe_fixture_normalize/tests/test_loader_hook.py::test_migrate_restores_deleted_record` |
| 39 | Loader: idempotent re-run | L2 | `test_loader_hook.py::test_migrate_twice_no_duplicates_no_errors` |
| 40 | Loader: corrupted sibling does not halt run | L2 | `test_loader_hook.py::test_corrupted_split_file_logs_warning_and_continues` |
| 41 | Loader: get_app_path raise swallowed | L2 | `test_loader_hook.py::test_get_app_path_failure_swallowed` |

## Pre-commit hook

| # | Feature | Layer | Test |
|---|---------|-------|------|
| 42 | Canonical file → exit 0 (subprocess) | L1 | `test_pre_commit_hook.py::test_already_canonical_file_returns_zero` |
| 43 | Rewrite → exit 1 (subprocess) | L1 | `test_pre_commit_hook.py::test_rewrites_unsorted_input_and_returns_nonzero` |
| 44 | Multi-file mixed (subprocess) | L1 | `test_pre_commit_hook.py::test_handles_multiple_files` |
| 45 | Non-array file skipped (subprocess) | L1 | `test_pre_commit_hook.py::test_non_array_file_skipped_silently` |
| 46 | Invalid JSON → exit 1 + stderr (subprocess) | L1 | `test_pre_commit_hook.py::test_invalid_json_returns_nonzero` |
| 47 | OSError on unreadable file | L1 | `test_pre_commit_hook.py::test_oserror_on_unreadable_file_returns_nonzero` |
| 48 | Normalization error reported | L1 | `test_pre_commit_hook.py::test_normalization_error_reported` |
| 49 | `process_file` canonical returns False | L1 | `test_pre_commit_hook.py::test_process_file_returns_false_for_canonical_file` |
| 50 | `process_file` rewrite returns True | L1 | `test_pre_commit_hook.py::test_process_file_returns_true_for_rewrite` |
| 51 | `process_file` invalid JSON returns error | L1 | `test_pre_commit_hook.py::test_process_file_returns_error_for_invalid_json` |
| 52 | `process_file` dict skipped (no error) | L1 | `test_pre_commit_hook.py::test_process_file_returns_none_error_for_dict` |
| 53 | `process_file` normalization failure surfaces error | L1 | `test_pre_commit_hook.py::test_process_file_returns_error_for_normalization_failure` |
| 54 | `process_file` OSError reported | L1 | `test_pre_commit_hook.py::test_process_file_returns_oserror_message_when_unreadable` |
| 55 | `main` exits 0 on clean run | L1 | `test_pre_commit_hook.py::test_main_returns_zero_when_no_changes` |
| 56 | `main` exits 1 on rewrite | L1 | `test_pre_commit_hook.py::test_main_returns_one_when_rewrites` |
| 57 | `main` exits 1 on error | L1 | `test_pre_commit_hook.py::test_main_returns_one_when_error` |
| 58 | `main` empty args is no-op | L1 | `test_pre_commit_hook.py::test_main_empty_args_returns_zero` |
| 59 | Pre-commit framework integration | L3 | `tests/e2e/06_pre_commit_framework.sh` |

## CLI commands (`commands.py`)

| # | Feature | Layer | Test |
|---|---------|-------|------|
| 60 | `_resolve_split_config` defaults when hook missing | L1 | `test_commands.py::test_resolve_split_config_returns_defaults_when_hook_missing` |
| 61 | `_resolve_split_config` merges list of dicts | L1 | `test_commands.py::test_resolve_split_config_merges_list_of_dicts` |
| 62 | `_resolve_split_config` accepts plain dict | L1 | `test_commands.py::test_resolve_split_config_accepts_plain_dict` |
| 63 | `_resolve_split_config` falls back on malformed hook | L1 | `test_commands.py::test_resolve_split_config_falls_back_on_malformed_hook` |
| 64 | `_resolve_split_config` skips non-dict list entries | L1 | `test_commands.py::test_resolve_split_config_skips_non_dict_list_entries` |
| 65 | `_resolve_split_config` defaults when merged empty | L1 | `test_commands.py::test_resolve_split_config_returns_defaults_when_merged_empty` |
| 66 | `export-clean-fixtures`: SiteNotSpecifiedError | L1 | `test_commands.py::test_export_command_raises_when_no_site` |
| 67 | `normalize-fixtures`: SiteNotSpecifiedError | L1 | `test_commands.py::test_normalize_command_raises_when_no_site` |
| 68 | Commands list contains both entries | L1 | `test_commands.py::test_commands_export_list_contains_both_entries` |
| 69 | Export callback iterates context.sites | L1 | `test_commands.py::test_export_callback_iterates_sites` |
| 70 | Normalize callback iterates context.sites | L1 | `test_commands.py::test_normalize_callback_iterates_sites` |
| 71 | `_run_for_site` calls export then post-process | L1 | `test_commands.py::test_run_for_site_invokes_export_then_post_process` |
| 72 | `_normalize_for_site` does not call export | L1 | `test_commands.py::test_normalize_for_site_skips_export_call` |
| 73 | Export writes split files (real bench) | L3 | `tests/e2e/01_determinism.sh` + `tests/e2e/03_single_field_diff.sh` |
| 74 | Export with no `--app` iterates all installed | L3 | `tests/e2e/01_determinism.sh` |
| 75 | Normalize ignores DB state | L3 | `tests/e2e/07_legacy_split.sh` |
| 76 | Consumer `fixture_normalize_split_by` override | L1 | `test_commands.py::test_resolve_split_config_merges_list_of_dicts` (config resolution) + manual hook in consumer app's `hooks.py` |
| 77 | Loader: discovers installed apps via frappe API | L2 | `test_loader_hook.py::test_default_discovers_installed_apps` |
| 78 | Loader: empty app path noop | L2 | `test_loader_hook.py::test_empty_app_path_is_noop` |

## End-to-end scenarios

| # | Feature | Layer | Test |
|---|---------|-------|------|
| 79 | Determinism, same machine | L3 | `tests/e2e/01_determinism.sh` |
| 80 | Determinism, cross machine (optional) | L3 | `tests/e2e/02_cross_machine.sh` |
| 81 | Single-field diff bounded to one file | L3 | `tests/e2e/03_single_field_diff.sh` |
| 82 | Merge safety across feature branches | L3 | `tests/e2e/04_merge_safety.sh` |
| 83 | Loader idempotence (delete + migrate) | L3 | `tests/e2e/05_idempotence.sh` |
| 84 | Pre-commit framework integration | L3 | `tests/e2e/06_pre_commit_framework.sh` (cross-ref row 59) |
| 85 | Legacy flat-file split migration | L3 | `tests/e2e/07_legacy_split.sh` |

---

## Running the suite

```bash
# Layer 1 (fast, no bench)
pip install -e ".[test]"
pytest

# Layer 2 (inside a frappe bench with the app installed)
bench --site <site> run-tests --app frappe_fixture_normalize

# Layer 3 (against a real bench + apex.localhost or equivalent)
BENCH_DIR=/workspace/development/frappe-bench \
  SITE=apex.localhost APP=apex \
  bash tests/e2e/run_all.sh
```

When adding a feature, add its row here before merging. When deleting a
feature, remove its row. A row without a passing test in CI is a release
blocker.
