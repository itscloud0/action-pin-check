# Changelog

## v0.4.0 - 2026-07-13

- Added optional `.action-pin-check.json` configuration for exact, reviewed tag refs.
- Added `--config` for selecting an explicit JSON policy file.
- Kept branch refs and missing refs as findings even when configuration is present.

## v0.3.0 - 2026-07-10

- Added `--format sarif` for GitHub code scanning upload workflows.
- Documented SARIF output alongside text, JSON, and GitHub annotation output.

## v0.2.0 - 2026-07-10

- Added `--format github-annotations` for inline GitHub Actions workflow commands.
- Documented annotation output for CI users.

## v0.1.0 - 2026-06-16

- Initial release of `action-pin-check`.
- Added workflow scanning for external GitHub Actions `uses:` refs.
- Added findings for missing refs, branch refs, mutable version refs, and short SHAs.
- Added text and JSON output.
- Added configurable exit policy with `--fail-on`.
- Added tests, CI, examples, and launch materials.
