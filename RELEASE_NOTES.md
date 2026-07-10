# action-pin-check v0.2.0

Feature release.

`action-pin-check` audits GitHub Actions workflows for external action refs that are missing, branch-based, tag-based, or short SHA pins. It is local-first, dependency-free at runtime, and now supports text, JSON, and GitHub Actions annotation output.

Included:

- `--format github-annotations` for inline CI findings on exact workflow lines.
- Existing text output for humans.
- Existing JSON output for automation.
- Existing `--fail-on` policy for CI gates.
