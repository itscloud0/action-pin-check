# action-pin-check v0.1.0

Initial release.

`action-pin-check` audits GitHub Actions workflows for external action refs that are missing, branch-based, tag-based, or short SHA pins. It is local-first, dependency-free at runtime, and supports both text and JSON output.

Included:

- CLI scanner for repository roots, workflow directories, or workflow files.
- Text output for humans.
- JSON output for automation.
- `--fail-on` policy for CI gates.
- Example unsafe workflow fixture.
- Unit tests and GitHub Actions CI.
