#!/usr/bin/env python3
"""Copy controlled vocabularies from registry/vocabularies.yaml into the files that repeat them.

vocabularies.yaml is the single source of truth for controlled lists. This
script copies its values into:

- registry/schema.json: the enum of each vocabulary $def
- .github/ISSUE_TEMPLATE/*.yml: the options of each Issue Form dropdown whose
  id is in FORM_FIELDS (registry_lib.py). Other fields, comments, and
  formatting are left alone.

Run it after editing vocabularies.yaml. On pull requests from branches in this
repository, the Sync vocabularies workflow runs it and commits the result. With
--check, nothing is written and the script exits 1 if any file is out of date
(for CI).
"""

import argparse
import io
import json
import sys

from ruamel.yaml import YAML

from registry_lib import (
    FORM_FIELDS,
    ISSUE_TEMPLATE_DIR,
    ROOT,
    SCHEMA_PATH,
    VOCAB_DEFS,
    RegistryError,
    load_vocabularies,
)


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


def _form_yaml():
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096  # don't re-wrap long lines
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def synced_form(text, vocab):
    """Return an Issue Form's text with its vocabulary dropdowns' options replaced from vocab.

    Text is returned unchanged if the form has no such dropdowns or they're
    already in sync, so files are only rewritten when a value changes.
    """
    yaml = _form_yaml()
    form = yaml.load(text)
    changed = False
    for item in (form or {}).get("body") or []:
        key = FORM_FIELDS.get(item.get("id"))
        if item.get("type") != "dropdown" or key is None:
            continue
        values = vocab[f"{key}_values"]
        attributes = item.setdefault("attributes", {})
        if list(attributes.get("options") or []) != values:
            attributes["options"] = list(values)
            changed = True
    if not changed:
        return text
    out = io.StringIO()
    yaml.dump(form, out)
    return out.getvalue()


def issue_forms(template_dir=ISSUE_TEMPLATE_DIR):
    """Issue Form files (config.yml configures the template chooser and isn't a form)."""
    if not template_dir.is_dir():
        return []
    return sorted(p for p in template_dir.iterdir()
                  if p.suffix in (".yml", ".yaml") and p.stem != "config")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if any file is out of date; don't write")
    args = parser.parse_args()

    try:
        vocab = load_vocabularies()
        current = SCHEMA_PATH.read_text(encoding="utf-8")
        updates = {SCHEMA_PATH: (current, render(synced_schema(json.loads(current), vocab)))}
        for path in issue_forms():
            current = path.read_text(encoding="utf-8")
            updates[path] = (current, synced_form(current, vocab))
    except RegistryError as e:
        print(f"Vocabulary error:\n{e}", file=sys.stderr)
        return 1

    stale = [path for path, (current, updated) in updates.items() if current != updated]
    if not stale:
        print("schema.json and Issue Forms are up to date with vocabularies.yaml")
        return 0
    names = ", ".join(p.relative_to(ROOT).as_posix() for p in stale)
    if args.check:
        print(f"Out of date with vocabularies.yaml: {names}\n"
              "Run: python scripts/sync_vocabularies.py (on branches in this repository, "
              "the Sync vocabularies workflow does this for you)", file=sys.stderr)
        return 1
    for path in stale:
        path.write_text(updates[path][1], encoding="utf-8")
    print(f"Updated from vocabularies.yaml: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
