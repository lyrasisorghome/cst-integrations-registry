#!/usr/bin/env python3
"""Build registry/index.json, the public index of scenario records.

The index lists every record except those whose status is in
index_exclude_statuses (vocabularies.yaml), and flagged records if
exclude_flagged_from_index is set (config.yaml). Each record gets its
system-controlled fields: record_url from base_url, flagged (default false),
and updated_date (defaults to submitted_date).

index.json is a build output, not committed. The publishing workflow builds it
and serves it on the registry website. The build stops if any record is
invalid; run validate_registry.py to see why.
"""

import argparse
import json
import sys

from registry_lib import INDEX_PATH, RegistryError, load_config, load_vocabularies
from validate_registry import load_records


def build_index(records, vocab, config):
    excluded = set(vocab.get("index_exclude_statuses", []))
    data = []
    for _, record in records.values():
        if record["status"] in excluded:
            continue
        if config["exclude_flagged_from_index"] and record.get("flagged"):
            continue
        entry = dict(record)
        entry["record_url"] = f"{config['base_url']}/scenarios/{record['id']}/"
        entry.setdefault("flagged", False)
        entry.setdefault("updated_date", record["submitted_date"])
        data.append(entry)

    # Newest first; id breaks ties so the output is stable.
    data.sort(key=lambda r: r["id"])
    data.sort(key=lambda r: r["submitted_date"], reverse=True)
    return {
        "meta": {"total": len(data)},
        "vocabularies": {key: vocab[f"{key}_values"]
                         for key in ("systems", "integration_types", "protocols", "statuses")},
        "data": data,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default=INDEX_PATH, help=f"where to write the index (default: {INDEX_PATH})")
    args = parser.parse_args()

    try:
        vocab, config = load_vocabularies(), load_config()
    except RegistryError as e:
        print(f"Registry error:\n{e}", file=sys.stderr)
        return 1

    records, problems = load_records()
    errors = [p for p in problems if p.level == "error"]
    if errors:
        print(f"Not building the index: {len(errors)} invalid record(s). Run scripts/validate_registry.py for details.",
              file=sys.stderr)
        return 1

    index = build_index(records, vocab, config)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {args.output}: {index['meta']['total']} of {len(records)} record(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
