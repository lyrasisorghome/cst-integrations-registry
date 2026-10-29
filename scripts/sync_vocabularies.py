#!/usr/bin/env python3
"""Copy controlled vocabularies from registry/vocabularies.yaml into registry/schema.json.

vocabularies.yaml is the single source of truth for controlled lists. Run this
after editing it. With --check, nothing is written and the script exits 1 if
schema.json is out of date (for CI).
"""

import argparse
import json
import sys

from registry_lib import SCHEMA_PATH, VOCAB_DEFS, RegistryError, load_vocabularies


def synced_schema(schema, vocab):
    """Return schema with each vocabulary $def's enum replaced from vocab."""
    defs = schema.get("$defs", {})
    for def_name, key in VOCAB_DEFS.items():
        if def_name not in defs:
            raise RegistryError(f"schema.json: missing $defs/{def_name}")
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
    except RegistryError as e:
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
