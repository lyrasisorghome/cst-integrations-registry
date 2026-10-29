import json

import pytest

from build_index import build_index
from registry_lib import SCHEMA_PATH, RegistryError, load_config, load_vocabularies, load_yaml
from sync_vocabularies import render, synced_schema
from validate_registry import duplicate_advisories, load_records, title_similarity

GOOD = """\
id: {id}
title: {title}
source_system: [ArchivesSpace]
target_system: [DSpace]
integration_type: Linking
protocol: [REST API]
status: {status}
description: Bidirectional URI linking between AS digital objects and DSpace items.
submitted_by: {submitted_by}
submitted_date: {submitted_date}
"""

ID_A = "550e8400-e29b-41d4-a716-446655440000"
ID_B = "7c9e6679-7425-40de-944b-e07fc1f90ae7"


def write_record(directory, record_id=ID_A, **fields):
    values = {"id": record_id, "title": "ArchivesSpace to DSpace linking", "status": "Active",
              "submitted_by": "Example University", "submitted_date": "2026-05-15T14:30:00Z", **fields}
    path = directory / f"{record_id}.yaml"
    path.write_text(GOOD.format(**values), encoding="utf-8")
    return path


def messages(problems, level="error"):
    return [p.message for p in problems if p.level == level]


def test_schema_is_in_sync_with_vocabularies():
    current = SCHEMA_PATH.read_text(encoding="utf-8")
    assert render(synced_schema(json.loads(current), load_vocabularies())) == current


def test_repository_config_and_vocabularies_load():
    load_config()
    load_vocabularies()


def test_unquoted_timestamps_stay_strings(tmp_path):
    path = tmp_path / "r.yaml"
    path.write_text("submitted_date: 2026-05-15T14:30:00Z\nlast_verified_date: 2026-04-01\n")
    assert load_yaml(path) == {"submitted_date": "2026-05-15T14:30:00Z", "last_verified_date": "2026-04-01"}


def test_valid_record_with_unquoted_date_passes(tmp_path):
    write_record(tmp_path)
    records, problems = load_records(tmp_path)
    assert list(records) == [ID_A]
    assert problems == []


def test_schema_errors_name_the_field(tmp_path):
    write_record(tmp_path, status="Archived")
    _, problems = load_records(tmp_path)
    assert any(m.startswith("status: 'Archived' is not one of") for m in messages(problems))


def test_id_must_match_filename(tmp_path):
    write_record(tmp_path).rename(tmp_path / f"{ID_B}.yaml")
    _, problems = load_records(tmp_path)
    assert any("must match" in m for m in messages(problems))


def test_wrong_extension_and_bad_yaml(tmp_path):
    (tmp_path / f"{ID_A}.yml").write_text("id: x\n")
    (tmp_path / f"{ID_B}.yaml").write_text("title: [unclosed\n")
    _, problems = load_records(tmp_path)
    titles = sorted(p.title for p in problems)
    assert titles == ["Invalid YAML", "Wrong file extension"]


def test_related_ids_must_exist(tmp_path):
    path = write_record(tmp_path)
    path.write_text(path.read_text() + f"related_scenario_ids: [{ID_B}]\n")
    _, problems = load_records(tmp_path)
    assert messages(problems) == [f"related_scenario_ids: no record with id {ID_B}"]


def test_title_similarity():
    assert title_similarity("ArchivesSpace to DSpace", "archivesspace  to dspace") == 1.0
    assert title_similarity("abc", "xyz") == 0.0


def test_hard_duplicate_is_a_warning(tmp_path):
    write_record(tmp_path, ID_A, title="First integration")
    write_record(tmp_path, ID_B, title="Something else entirely")
    records, problems = load_records(tmp_path)
    warnings = duplicate_advisories(records)
    assert problems == []
    assert len(warnings) == 1 and warnings[0].level == "warning"
    assert "Same submitter" in warnings[0].message


def test_similar_title_is_a_warning_only_for_active_records(tmp_path):
    write_record(tmp_path, ID_A, submitted_by="Library A")
    write_record(tmp_path, ID_B, submitted_by="Library B", title="ArchivesSpace to DSpace linkin")
    records, _ = load_records(tmp_path)
    assert "similar" in duplicate_advisories(records)[0].message

    write_record(tmp_path, ID_A, submitted_by="Library A", status="Retired")
    records, _ = load_records(tmp_path)
    assert duplicate_advisories(records, focus=[ID_B]) == []


def test_focus_limits_duplicate_checks(tmp_path):
    write_record(tmp_path, ID_A)
    write_record(tmp_path, ID_B)
    records, _ = load_records(tmp_path)
    assert duplicate_advisories(records, focus=[]) == []
    assert len(duplicate_advisories(records, focus=[ID_B])) == 1


def test_index_excludes_retired_and_adds_system_fields(tmp_path):
    write_record(tmp_path, ID_A, submitted_date="2026-01-01T00:00:00Z")
    write_record(tmp_path, ID_B, status="Retired")
    records, _ = load_records(tmp_path)
    config = {"base_url": "https://registry.example.org", "exclude_flagged_from_index": False}
    index = build_index(records, load_vocabularies(), config)
    assert index["meta"]["total"] == 1
    entry = index["data"][0]
    assert entry["record_url"] == f"https://registry.example.org/scenarios/{ID_A}/"
    assert entry["flagged"] is False
    assert entry["updated_date"] == "2026-01-01T00:00:00Z"


def test_bad_config_is_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("base_url: https://example.org/\nduplicate_title_similarity: 2\nexclude_flagged_from_index: no\n")
    with pytest.raises(RegistryError) as e:
        load_config(path)
    assert str(e.value).count("\n") == 1  # base_url and similarity; "no" is a YAML boolean
