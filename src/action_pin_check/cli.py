from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import __version__
from .scanner import ScanResult, exit_code_for, scan_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="action-pin-check",
        description="Audit GitHub Actions workflows for mutable or missing action pins.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root, workflow directory, or workflow file to scan.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "github-annotations"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--fail-on",
        choices=("warning", "error", "never"),
        default="warning",
        help="Choose which finding severity should produce a non-zero exit code.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    result = scan_path(args.path)
    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif args.format == "github-annotations":
        annotations = _format_github_annotations(result)
        if annotations:
            print(annotations)
    else:
        print(_format_text(result))

    return exit_code_for(result, args.fail_on)


def _format_text(result: ScanResult) -> str:
    if result.ok:
        return (
            f"OK: scanned {result.workflow_count} workflow file(s), "
            f"{result.action_count} external action use(s), no pinning findings."
        )

    lines = [
        "Action Pin Check",
        f"Root: {result.root}",
        (
            f"Workflows: {result.workflow_count}  "
            f"External actions: {result.action_count}  "
            f"Findings: {len(result.findings)}"
        ),
        "",
    ]
    for finding in result.findings:
        location = finding.file
        if finding.line:
            location = f"{location}:{finding.line}"
        ref = f"@{finding.ref}" if finding.ref else ""
        lines.extend(
            [
                f"{finding.severity.upper()} {location} {finding.code}",
                f"  uses: {finding.action}{ref}".rstrip(),
                f"  {finding.message}",
                f"  Fix: {finding.suggestion}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _format_github_annotations(result: ScanResult) -> str:
    lines = []
    for finding in result.findings:
        command = "error" if finding.severity == "error" else "warning"
        props = [
            f"file={_escape_annotation_property(finding.file)}",
            f"title={_escape_annotation_property(finding.code)}",
        ]
        if finding.line > 0:
            props.insert(1, f"line={finding.line}")
        ref = f"@{finding.ref}" if finding.ref else ""
        message = (
            f"{finding.message} Fix: {finding.suggestion} "
            f"uses: {finding.action}{ref}".rstrip()
        )
        lines.append(
            f"::{command} {','.join(props)}::{_escape_annotation_data(message)}"
        )
    return "\n".join(lines)


def _escape_annotation_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_annotation_property(value: str) -> str:
    return (
        _escape_annotation_data(value)
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
