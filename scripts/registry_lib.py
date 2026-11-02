"""Shared helpers for the registry scripts: paths, YAML loading, vocabularies, and config."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "registry"
SCENARIOS_DIR = REGISTRY_DIR / "scenarios"
SCHEMA_PATH = REGISTRY_DIR / "schema.json"
VOCAB_PATH = REGISTRY_DIR / "vocabularies.yaml"
CONFIG_PATH = REGISTRY_DIR / "config.yaml"
INDEX_PATH = REGISTRY_DIR / "index.json"
ISSUE_TEMPLATE_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"

# schema.json $defs name -> vocabularies.yaml key
VOCAB_DEFS = {
    "system": "systems",
    "integration_type": "integration_types",
    "protocol": "protocols",
    "status": "statuses",
}

# Issue Form dropdown id -> vocabularies.yaml key
FORM_FIELDS = {
    "source_system": "systems",
    "target_system": "systems",
    "integration_type": "integration_types",
    "protocol": "protocols",
    "status": "statuses",
}


class RegistryError(Exception):
    """A problem with the registry's own configuration files."""


class _StringTimestampLoader(yaml.SafeLoader):
    """SafeLoader that leaves timestamps as strings.

    PyYAML turns unquoted values like 2026-05-15T14:30:00Z into datetime
    objects, which then fail the schema's string formats. With this loader a
    record validates the same whether or not its dates are quoted.
    """


_StringTimestampLoader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path):
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_StringTimestampLoader)


def load_vocabularies(path=VOCAB_PATH):
    """Load vocabularies.yaml and check its structure.

    Returns the parsed file with each list in VOCAB_DEFS also available as
    plain values under "<key>_values". Raises RegistryError listing every
    problem found.
    """
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise RegistryError(f"{Path(path).name}: expected a mapping at the top level")

    errors = []
    for key in VOCAB_DEFS.values():
        entries = data.get(key)
        if not isinstance(entries, list) or not entries:
            errors.append(f"{key}: must be a non-empty list")
            continue

        values = []
        for i, entry in enumerate(entries):
            if key == "systems":
                if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"].strip():
                    errors.append(f"systems[{i}]: needs a non-empty 'name'")
                    continue
                if "team" in entry and not (isinstance(entry["team"], str) and entry["team"].strip()):
                    errors.append(f"systems[{i}] ({entry['name']}): 'team' must be a non-empty string if present")
                values.append(entry["name"])
            elif isinstance(entry, str) and entry.strip():
                values.append(entry)
            else:
                errors.append(f"{key}[{i}]: must be a non-empty string")

        duplicates = sorted({v for v in values if values.count(v) > 1})
        if duplicates:
            errors.append(f"{key}: duplicate values {duplicates}")
        data[f"{key}_values"] = values

    if not (isinstance(data.get("default_team"), str) and data["default_team"].strip()):
        errors.append("default_team: must be a non-empty string")

    excluded = data.get("index_exclude_statuses", [])
    if not isinstance(excluded, list):
        errors.append("index_exclude_statuses: must be a list")
    else:
        unknown = [s for s in excluded if s not in data.get("statuses_values", [])]
        if unknown:
            errors.append(f"index_exclude_statuses: not in statuses: {unknown}")

    if errors:
        raise RegistryError("\n".join(errors))
    return data


def load_config(path=CONFIG_PATH):
    """Load config.yaml and check its values. Raises RegistryError on problems."""
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise RegistryError(f"{Path(path).name}: expected a mapping at the top level")

    errors = []
    base_url = data.get("base_url")
    if not (isinstance(base_url, str) and base_url.startswith(("http://", "https://")) and not base_url.endswith("/")):
        errors.append("base_url: must be an http(s) URL without a trailing slash")
    similarity = data.get("duplicate_title_similarity")
    if isinstance(similarity, bool) or not isinstance(similarity, (int, float)) or not 0 < similarity <= 1:
        errors.append("duplicate_title_similarity: must be a number between 0 and 1")
    if not isinstance(data.get("exclude_flagged_from_index"), bool):
        errors.append("exclude_flagged_from_index: must be true or false")

    if errors:
        raise RegistryError("\n".join(errors))
    return data
