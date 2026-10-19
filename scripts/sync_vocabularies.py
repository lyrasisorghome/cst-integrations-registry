#!/usr/bin/env python3
"""Copy controlled vocabularies from registry/vocabularies.yaml into registry/schema.json.

vocabularies.yaml is the single source of truth for controlled lists. Run this
after editing it. With --check, nothing is written and the script exits 1 if
schema.json is out of date (for CI).
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VOCAB_PATH = ROOT / "registry" / "vocabularies.yaml"
SCHEMA_PATH = ROOT / "registry" / "schema.json"

# schema.json $defs name -> vocabularies.yaml key
VOCAB_DEFS = {
    "system": "systems",
    "integration_type": "integration_types",
    "protocol": "protocols",
    "status": "statuses",
}


class VocabularyError(Exception):
    pass


def load_vocabularies(path=VOCAB_PATH):
    """Load vocabularies.yaml and check its structure.

    Returns the parsed file with each list in VOCAB_DEFS also available as
    plain values under "<key>_values". Raises VocabularyError listing every
    problem found.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise VocabularyError(f"{path.name}: expected a mapping at the top level")

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
        raise VocabularyError("\n".join(errors))
    return data


def synced_schema(schema, vocab):
    """Return schema with each vocabulary $def's enum replaced from vocab."""
    defs = schema.get("$defs", {})
    for def_name, key in VOCAB_DEFS.items():
        if def_name not in defs:
            raise VocabularyError(f"schema.json: missing $defs/{def_name}")
        defs[def_name]["enum"] = vocab[f"{key}_values"]
    return schema


def render(schema):
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if schema.json is out of date; don't write")
    args = parser.parse_args()

    try:
        vocab = load_vocabularies()
        current = SCHEMA_PATH.read_text(encoding="utf-8")
        updated = render(synced_schema(json.loads(current), vocab))
    except VocabularyError as e:
        print(f"Vocabulary error:\n{e}", file=sys.stderr)
        return 1

    if current == updated:
        print("schema.json is up to date with vocabularies.yaml")
        return 0
    if args.check:
        print("schema.json is out of date. Run: python scripts/sync_vocabularies.py", file=sys.stderr)
        return 1
    SCHEMA_PATH.write_text(updated, encoding="utf-8")
    print("Updated schema.json from vocabularies.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
