# action-pin-check

Audit GitHub Actions workflows for mutable or missing action pins.

`action-pin-check` is a small local CLI for maintainers who want a quick supply-chain sanity check before publishing a repo or accepting workflow changes.

## Problem

GitHub Actions workflows often use refs like `actions/checkout@v4` or `some/action@main`. Those refs are convenient, but they can move. For stricter CI hygiene, maintainers need a fast way to find workflow steps that are not pinned to a full commit SHA.

## Why this exists

Security scanners can be broad and noisy. This tool does one narrow check: read workflow files, list external `uses:` actions, and flag missing refs, branch refs, version tags, and short SHAs. It has no runtime dependencies and works without network access.

## 30-second quickstart

```bash
python -m pip install git+https://github.com/itscloud0/action-pin-check.git
action-pin-check examples/workflows --fail-on never
```

Expected demo output:

```text
Action Pin Check
Root: /path/to/action-pin-check/examples/workflows
Workflows: 1  External actions: 3  Findings: 3

WARNING unsafe.yml:10 mutable-version-ref
  uses: actions/checkout@v4
  Action uses a tag or other mutable ref.
  Fix: For stronger supply-chain control, pin to a full commit SHA.

ERROR unsafe.yml:11 floating-branch-ref
  uses: actions/setup-python@main
  Action is pinned to a mutable branch ref.
  Fix: Replace the branch with a reviewed full commit SHA.

ERROR unsafe.yml:12 missing-action-ref
  uses: acme/internal-action
  Action reference is missing an @ref.
  Fix: Pin acme/internal-action to a full commit SHA.
```

## Installation

From GitHub:

```bash
python -m pip install git+https://github.com/itscloud0/action-pin-check.git
```

For local development:

```bash
git clone https://github.com/itscloud0/action-pin-check.git
cd action-pin-check
python -m pip install .
```

## Usage

Scan the current repository:

```bash
action-pin-check
```

Scan a workflow directory:

```bash
action-pin-check .github/workflows
```

Return JSON for automation:

```bash
action-pin-check --format json --fail-on never
```

Emit SARIF for GitHub code scanning:

```bash
action-pin-check --format sarif --fail-on never > action-pin-check.sarif
```

Emit GitHub Actions workflow annotations for inline CI findings:

```bash
action-pin-check --format github-annotations --fail-on error
```

Fail CI only on hard errors, not version-tag warnings:

```bash
action-pin-check --fail-on error
```

## Demo

The included fixture contains a version tag, a branch ref, a missing ref, and a local action:

```bash
action-pin-check examples/workflows --fail-on never
```

Local actions like `./local-action` and Docker actions like `docker://...` are ignored in v0.1 because this tool focuses on external GitHub action refs.

## Common use cases

- Audit a new open-source repo before launch.
- Add a lightweight CI gate for workflow changes.
- Upload SARIF findings to GitHub code scanning.
- Produce JSON findings for a repo-quality dashboard.
- Review incoming pull requests that edit `.github/workflows`.
- Teach contributors why mutable action refs matter.

## Comparison and alternatives

`action-pin-check` is smaller than general-purpose security scanners. It does not try to audit permissions, secrets, dependencies, or action provenance. Use it when you want one quick, scriptable check for action ref pinning. Use a broader tool when you need full CI security posture review.

## Limitations

- Parses common `uses:` lines with a lightweight scanner, not a full YAML parser.
- Does not verify whether a SHA exists upstream.
- Does not rewrite workflow files automatically.
- Does not inspect reusable workflow internals.
- Ignores local and Docker actions in v0.1.

## Roadmap

- Config file for allowed tag refs.
- Safer fix suggestions that include action repository links.
- Reusable workflow coverage.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Small fixtures for real workflow edge cases are especially useful.

## License

MIT. See [LICENSE](LICENSE).
