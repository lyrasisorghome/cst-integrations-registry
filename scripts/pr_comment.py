#!/usr/bin/env python3
"""Render a validation report (validate_registry.py --report) as a pull request comment.

The Comment on pull request workflow posts the output, updating its earlier
comment if there is one (found by MARKER). Annotations and the job summary
already show the same problems, but a comment is easier for reviewers to find.

The report comes from a run on the pull request's code, so its text is
untrusted: it's escaped so record titles and filenames can't add formatting,
links, @mentions, or #references to the comment.

Uses only the standard library, so the workflow can run it without installing
anything.
"""

import argparse
import json
import re
import sys

MARKER = "<!-- registry-validation -->"
MAX_ITEMS = 50  # per section; the rest are counted, and the job summary has them all

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]<>()+!|~])")


def escape(text):
    """Make untrusted text safe to show as plain text in a comment."""
    text = " ".join(str(text).split())
    text = text.replace("&", "&amp;")
    text = _MARKDOWN_SPECIAL.sub(r"\\\1", text)
    # A zero-width space after @ and # stops mentions and issue references.
    return text.replace("@", "@​").replace("#", "#​")


def code(text):
    return "`" + " ".join(str(text).replace("`", "'").split()) + "`"


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def section(heading, intro, items):
    lines = [f"#### {heading}", ""]
    if intro:
        lines += [intro, ""]
    for p in items[:MAX_ITEMS]:
        lines.append(f"- {code(p['path'])}: **{escape(p['title'])}:** {escape(p['message'])}")
    if len(items) > MAX_ITEMS:
        lines.append(f"- …and {len(items) - MAX_ITEMS} more (see the run's summary)")
    return lines + [""]


def render(report, run_url=None):
    problems = report.get("problems", [])
    errors = [p for p in problems if p.get("level") == "error"]
    warnings = [p for p in problems if p.get("level") == "warning"]
    lines = [MARKER, "### Registry validation", ""]

    if not problems:
        lines += ["✅ All records are valid, and no possible duplicates were found.", ""]
    else:
        if errors:
            lines.append(f"❌ **{plural(len(errors), 'error')}** must be fixed before this pull request can be merged.")
        if warnings:
            lines.append(f"⚠️ **{plural(len(warnings), 'warning')}** for reviewers to check. Warnings don't block merging.")
        lines.append("")
        if errors:
            lines += section("Errors", None, errors)
        if warnings:
            lines += section("Warnings",
                             "Check whether this describes the same integration as the existing record. "
                             "If it does, consider updating that record instead of adding a new one.",
                             warnings)

    footer = f"Checked {plural(report.get('record_count', 0), 'record')}."
    if run_url:
        footer += f" [View the validation run]({run_url})"
    return "\n".join(lines + [footer]) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report", help="JSON report from validate_registry.py --report")
    parser.add_argument("--run-url", help="link to the validation run")
    parser.add_argument("--skip-if-clean", action="store_true",
                        help="print nothing if there are no problems (when there's no earlier comment to update)")
    args = parser.parse_args()

    with open(args.report, encoding="utf-8") as f:
        report = json.load(f)
    if args.skip_if_clean and not report.get("problems"):
        return 0
    sys.stdout.write(render(report, args.run_url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
