# action-pin-check v0.4.1

Patch release.

- Text output aligns finding codes when workflow paths have different lengths.
- Complete `file:line` locations remain visible and copy-paste friendly.

## v0.4.0

Feature release.

`action-pin-check` audits GitHub Actions workflows for external action refs that are missing, branch-based, tag-based, or short SHA pins. It is local-first, dependency-free at runtime, and now supports text, JSON, GitHub Actions annotation, and SARIF output.

Included:

- Optional `.action-pin-check.json` allowlist for exact reviewed tag refs.
- `--config` for an explicit JSON policy path.
- Branch refs and missing refs remain findings regardless of allowlist entries.
- `--format sarif` for GitHub code scanning upload workflows.
- `--format github-annotations` for inline CI findings on exact workflow lines.
- Existing text output for humans.
- Existing JSON output for automation.
- Existing `--fail-on` policy for CI gates.
