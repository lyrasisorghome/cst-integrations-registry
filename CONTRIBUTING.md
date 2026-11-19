# Contributing to the CST Integrations Registry

Thanks for sharing your work. This guide covers what to include in a submission, how to submit, and what happens next. The Issue Form and the pull request template link here, so this page is the place to update submission guidance.

<!-- TODO(LYRASIS): Replace the placeholder text in "Terms" and "Questions" with final wording. -->

## What to include

A record describes one integration: what it does, which systems it connects, and how someone else could replicate it. Link to code and documentation rather than pasting them in.

Everything in the registry is **public**. Don't include:

- passwords, API keys, tokens, or other credentials
- internal or intranet URLs, server names, or IP addresses
- personal information about anyone who hasn't agreed to be listed

## How to submit

You'll need a free [GitHub account](https://github.com/signup).

### Issue Form (recommended)

1. Open the [Submit an integration scenario](https://github.com/lyrasisorghome/cst-integrations-registry/issues/new?template=submit-integration.yml) form.
2. Fill in the required fields (marked with a red asterisk) and any others you can.
3. Select **Create**.

Approvers for each system you named are notified and review your submission.

### Pull request

If you're comfortable with YAML and Git, you can add a record directly:

1. Create `registry/scenarios/{id}.yaml`, where `{id}` is a new lowercase UUID, such as one from `python3 -c "import uuid; print(uuid.uuid4())"`. The `id` field in the file must match.
2. Fill in the fields defined in [`registry/schema.json`](registry/schema.json). Values for systems, integration types, protocols, and statuses must come from [`registry/vocabularies.yaml`](registry/vocabularies.yaml).
3. Open a pull request and complete the checklist in its description.

Automated checks validate your record and point out any problems. They also warn if it looks like an existing record.

## What happens next

An approver from the relevant community reviews your submission. If they have questions, they'll comment on your issue or pull request, so watch for GitHub notifications. Once it's approved and merged, your record appears in the registry.

To update a record later, open a pull request that edits its file, or open an issue describing the change.

## Terms

<!-- TODO(LYRASIS): Terms of use for submissions. -->

By submitting, you confirm that you have the right to share this information and that it can be published publicly. Licensing for your notes and linked code is set by the record's `license` field.

## Questions

<!-- TODO(LYRASIS): Contact for questions about the registry. -->

Open an issue in this repository.
