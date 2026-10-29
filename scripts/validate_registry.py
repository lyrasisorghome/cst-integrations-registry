#!/usr/bin/env python3
"""Validate the scenario records in registry/scenarios/.

Each record is checked against registry/schema.json, its id must match its
filename, and its related_scenario_ids must point to existing records. Errors
fail the run (exit 1).

Possible duplicates are reported as warnings and never fail the run. By default
every record is checked for duplicates; with --changed, only the listed files
are (CI passes the files changed in a pull request, so long-standing look-alikes
aren't reported on every PR).

In GitHub Actions, problems are also printed as workflow annotations and a job
summary, so they show up on the pull request.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from registry_lib import (
    ROOT,
    SCENARIOS_DIR,
    SCHEMA_PATH,
    RegistryError,
    load_config,
    load_yaml,
)

# Only records with these statuses are compared by title for duplicates (per the spec).
TITLE_CHECK_STATUSES = {"Active", "Experimental"}


@dataclass
class Problem:
    level: str  # "error" or "warning"
    path: Path
    title: str
    message: str


def rel(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def field_path(parts):
    """Turn a jsonschema error path like ['source_system', 0] into 'source_system[0]'."""
    out = ""
    for part in parts:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


def load_records(scenarios_dir=SCENARIOS_DIR, schema_path=SCHEMA_PATH):
    """Load and validate every record.

    Returns (records, problems). records maps each file's stem to (path, record)
    for every file that parsed to a mapping, valid or not, so later checks can
    still use it.
    """
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    records, problems = {}, []

    for path in sorted(Path(scenarios_dir).iterdir()):
        if path.name.startswith(".") or path.is_dir():
            continue
        if path.suffix != ".yaml":
            problems.append(Problem("error", path, "Wrong file extension",
                                    "Scenario files must be named {id}.yaml"))
            continue

        try:
            record = load_yaml(path)
        except yaml.YAMLError as e:
            problems.append(Problem("error", path, "Invalid YAML", str(e)))
            continue
        if not isinstance(record, dict):
            problems.append(Problem("error", path, "Invalid record", "The file must contain a single YAML mapping of fields"))
            continue
        records[path.stem] = (path, record)

        for err in sorted(validator.iter_errors(record), key=lambda e: [str(p) for p in e.absolute_path]):
            where = field_path(err.absolute_path)
            problems.append(Problem("error", path, "Schema error", f"{where}: {err.message}" if where else err.message))

        record_id = record.get("id")
        if isinstance(record_id, str) and record_id != path.stem:
            problems.append(Problem("error", path, "id doesn't match filename",
                                    f"id is {record_id} but the file is {path.name}; they must match"))

    for stem, (path, record) in records.items():
        related = record.get("related_scenario_ids")
        if not isinstance(related, list):
            continue
        for rid in related:
            if rid == stem:
                problems.append(Problem("error", path, "Invalid related record", "related_scenario_ids lists the record itself"))
            elif isinstance(rid, str) and rid not in records:
                problems.append(Problem("error", path, "Unknown related record",
                                        f"related_scenario_ids: no record with id {rid}"))

    return records, problems


def levenshtein(a, b):
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def title_similarity(a, b):
    """Normalized Levenshtein similarity (0 to 1), ignoring case and extra whitespace."""
    a, b = " ".join(a.lower().split()), " ".join(b.lower().split())
    if not a and not b:
        return 1.0
    return 1 - levenshtein(a, b) / max(len(a), len(b))


def _match_key(record):
    """submitted_by + sorted systems + integration type, or None if any part is missing."""
    try:
        return (
            " ".join(record["submitted_by"].lower().split()),
            tuple(sorted(record["source_system"])),
            tuple(sorted(record["target_system"])),
            record["integration_type"],
        )
    except (KeyError, TypeError, AttributeError):
        return None


def duplicate_advisories(records, focus=None, threshold=0.85):
    """Warn about records that look like duplicates of each other.

    records maps id -> (path, record). Only pairs that include an id in focus
    are reported (every pair if focus is None).
    """
    problems, reported = [], set()
    focus_ids = records.keys() if focus is None else [i for i in focus if i in records]

    for fid in focus_ids:
        path, record = records[fid]
        key, title = _match_key(record), record.get("title")
        for oid, (_, other) in records.items():
            pair = frozenset((fid, oid))
            if oid == fid or pair in reported:
                continue
            other_title = other.get("title")
            label = f'{oid} ("{other_title}")' if isinstance(other_title, str) else oid

            if key is not None and key == _match_key(other):
                reported.add(pair)
                problems.append(Problem("warning", path, "Possible duplicate",
                                        f"Same submitter, systems, and integration type as {label}"))
            elif (isinstance(title, str) and isinstance(other_title, str)
                  and other.get("status") in TITLE_CHECK_STATUSES
                  and (score := title_similarity(title, other_title)) >= threshold):
                reported.add(pair)
                problems.append(Problem("warning", path, "Possible duplicate",
                                        f"Title is {score:.0%} similar to {label}"))
    return problems


def _escape_data(s):
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(s):
    return _escape_data(s).replace(":", "%3A").replace(",", "%2C")


def report(problems, record_count):
    errors = [p for p in problems if p.level == "error"]
    warnings = [p for p in problems if p.level == "warning"]
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    for p in problems:
        print(f"{p.level.upper()} {rel(p.path)}: {p.title}: {p.message}")
        if in_actions:
            print(f"::{p.level} file={_escape_property(rel(p.path))},title={_escape_property(p.title)}::{_escape_data(p.message)}")
    print(f"Checked {record_count} record(s): {len(errors)} error(s), {len(warnings)} warning(s)")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = ["## Registry validation", "",
                 f"Checked {record_count} record(s): **{len(errors)} error(s)**, {len(warnings)} warning(s).", ""]
        if problems:
            lines += ["| | File | Problem |", "|---|---|---|"]
            for p in problems:
                icon = "❌" if p.level == "error" else "⚠️"
                message = p.message.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {icon} | `{rel(p.path)}` | **{p.title}:** {message} |")
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--changed", nargs="*", metavar="FILE",
                        help="only check these files for possible duplicates")
    args = parser.parse_args()

    try:
        config = load_config()
    except RegistryError as e:
        print(f"Config error:\n{e}", file=sys.stderr)
        return 1

    records, problems = load_records()
    focus = None
    if args.changed is not None:
        focus = [Path(f).stem for f in args.changed
                 if Path(f).suffix == ".yaml" and Path(f).resolve().parent == SCENARIOS_DIR.resolve()]
    problems += duplicate_advisories(records, focus, config["duplicate_title_similarity"])
    return report(problems, len(records))


if __name__ == "__main__":
    sys.exit(main())
