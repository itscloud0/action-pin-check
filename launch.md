# Launch Plan: action-pin-check

## Suggested GitHub repository name

`action-pin-check`

## GitHub description

Audit GitHub Actions workflows for mutable or missing action pins.

## GitHub topics

- github-actions
- ci
- cli
- developer-tools
- devex
- security
- supply-chain
- open-source
- python
- workflow-audit

## X/Twitter launch post

I shipped `action-pin-check`: a tiny local CLI that scans GitHub Actions workflows for missing, branch-based, tag-based, or short SHA action refs.

Useful before publishing a repo or reviewing workflow changes.

```bash
action-pin-check .github/workflows
```

https://github.com/itscloud0/action-pin-check

## LinkedIn launch post

I released `action-pin-check`, a small open-source CLI for maintainers who want a quick GitHub Actions supply-chain sanity check.

It scans workflow `uses:` lines and flags external actions that are missing refs, pinned to branches, pinned to version tags, or using short SHAs. It is local-first, dependency-free at runtime, and can output JSON for automation.

This is intentionally narrow: one fast check that is easy to add to review workflows or CI.

Repository: https://github.com/itscloud0/action-pin-check

## Hacker News title

Show HN: action-pin-check - audit GitHub Actions refs from your terminal

## Reddit post for r/github

Title: I built a small CLI to audit GitHub Actions `uses:` refs

Body:

I made `action-pin-check`, a local Python CLI that scans workflow files and reports external actions that are missing refs, use branch refs like `main`, use mutable version tags like `v4`, or use short SHAs.

It does not call GitHub or execute workflows. It is meant as a quick pre-launch or pull request review check.

Repo: https://github.com/itscloud0/action-pin-check

## Demo captions

1. Scan `.github/workflows` before publishing a repo.
2. Catch `@main` action refs before they land in CI.
3. Return JSON findings for automation.
4. Fail CI on warnings or only on errors.
5. Keep local and Docker actions out of scope for a focused audit.

## Completed launch checklist

1. Added fixtures for reusable workflow `uses:` patterns.
2. Improved text output alignment for long workflow paths.
3. Added tests for quoted `uses:` values and inline comments.

## Shipped since v0.1.0

1. Added SARIF output for GitHub code scanning (`v0.3.0`).
2. Added optional config for allowed tag refs (`v0.4.0`).
3. Added GitHub Actions annotation output (`v0.2.0`).

## Current release title

`action-pin-check v0.4.1`

## Current release notes

Current releases include text, JSON, GitHub annotation, and SARIF output, exact reviewed-tag configuration, CI exit policies, tests, and workflow fixtures. Version `v0.4.1` also aligns long workflow paths in text findings without truncating their locations.

## What not to claim

- Do not claim it proves a workflow is secure.
- Do not claim it verifies upstream action integrity.
- Do not claim it replaces a full CI security audit.
- Do not claim automatic fixes.

## Known limitations

- Lightweight line scanner, not a full YAML parser.
- Does not verify whether SHAs exist upstream.
- Ignores local and Docker actions; this check targets external GitHub action refs.
- Does not inspect nested reusable workflows.

## Maintainer note

Keep this tool narrow and predictable. The best next features are output formats, fixtures, and CI integrations around the same action-ref pinning check.
