# CST Integrations Registry

A public, community-maintained registry of real-world integrations involving the LYRASIS Community Supported Technologies (CSTs): **ArchivesSpace, DSpace, CollectionSpace, VIVO, and Fedora**. It covers integrations between two CSTs and between a CST and an outside system.

Institutions often solve the same interoperability problems independently. This registry gives practitioners one place to share what they've built and to find what others have already done. Each record describes what an integration does, how it works, and how someone else could replicate it. Records link out to code, documentation, and specifications rather than hosting them.

> **Status:** Under active development (Phase I). Implements the [Integration Scenario Registry specification (F1)](https://github.com/lyrasisorghome/InteroperabilityProject/issues/58) from the LYRASIS Interoperability Project.

## How it works

The registry runs entirely on GitHub. There is no separate server or database.

- **Records** are YAML files, one per integration scenario, stored in `registry/scenarios/`.
- **A JSON Schema** (`registry/schema.json`) defines the required and optional fields. Controlled vocabularies (systems, integration types, protocols, statuses) live in `registry/vocabularies.yaml`, and administrators can edit them without changing code.
- **GitHub Actions** validate every submission against the schema, assign each record a stable UUID, flag likely duplicates (as warnings, never blocks), and rebuild `registry/index.json` when changes are merged.
- **A search site on GitHub Pages** reads `index.json`. Users can filter records by source system, target system, integration type, protocol, and status, search by keyword or UUID, and open a full detail page for any record.
- **Nothing is deleted.** Records marked Retired or Recalled drop out of the default search results but stay in the repository, and the git history serves as the record's audit trail.

## Finding an integration

Use the registry search site to filter and browse records. No account is needed. Developers who want the raw data can download `registry/index.json` directly.

## Contributing an integration

You'll need a GitHub account to submit a record. There are two ways to contribute:

1. **Issue Form (recommended).** Open a new issue using the *Submit an integration scenario* form. An Action converts your submission into a YAML record and opens a pull request for review. If anything doesn't pass validation, the Action comments on your issue so you can fix it.
2. **Pull request.** If you're comfortable with YAML, add a file to `registry/scenarios/` directly, following the PR template and contributor checklist.

A reviewer merges each pull request, and the record is published when it's merged.

## Review and notifications

Each CST community has its own GitHub team of approvers. When someone submits an integration through the Issue Form, the registry @mentions the team for every CST named as a source or target system, so the right reviewers are notified. Community managers can add or remove approvers by changing team membership, with no code changes.

GitHub delivers these mentions according to each team's settings and each member's personal notification settings. See the documentation for how to make sure you receive them.

## Documentation

User and administrator documentation will cover submitting and updating records, searching, the review process, notification settings, exporting data, governance, accessibility, and field definitions.

## Governance

The registry's administrative home is the LYRASIS Organizational Home for Community Supported Technologies. Product ownership is shared with the CST community product teams and community volunteers. Each community appoints its own registry approvers.

## Roadmap

Phase II may add a read-only HTTP API over the same data. This would not change the record schema.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
