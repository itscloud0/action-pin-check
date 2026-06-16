# Security Policy

## Supported versions

Version `0.1.x` receives security fixes.

## Reporting a vulnerability

Open a private vulnerability report on GitHub if available, or create a minimal public issue that avoids exposing exploit details.

Useful reports include:

- The workflow input that caused the problem.
- The expected finding.
- The actual finding.
- Whether the issue affects CI exit codes or JSON output.

## Scope

`action-pin-check` is a local static analyzer. It does not execute workflows, fetch remote actions, read secrets, or contact GitHub.
