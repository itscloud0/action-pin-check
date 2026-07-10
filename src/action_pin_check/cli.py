from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence
from urllib.parse import quote

from . import __version__
from .scanner import Finding, ScanResult, exit_code_for, scan_path


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
        choices=("text", "json", "github-annotations", "sarif"),
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
    elif args.format == "sarif":
        print(json.dumps(_format_sarif(result), indent=2, sort_keys=True))
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
        lines.append(
            f"::{command} {','.join(props)}::"
            f"{_escape_annotation_data(_finding_message(finding))}"
        )
    return "\n".join(lines)


def _format_sarif(result: ScanResult) -> dict[str, object]:
    rule_codes = sorted({finding.code for finding in result.findings})
    rules = [_sarif_rule(code) for code in rule_codes]
    results = []

    for finding in result.findings:
        physical_location: dict[str, object] = {
            "artifactLocation": {"uri": _sarif_uri(finding.file)}
        }
        if finding.line > 0:
            physical_location["region"] = {"startLine": finding.line}
        results.append(
            {
                "ruleId": finding.code,
                "level": finding.severity,
                "message": {"text": _finding_message(finding)},
                "locations": [{"physicalLocation": physical_location}],
            }
        )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "action-pin-check",
                        "semanticVersion": __version__,
                        "informationUri": "https://github.com/itscloud0/action-pin-check",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def _sarif_rule(code: str) -> dict[str, object]:
    descriptions = {
        "floating-branch-ref": "Action ref is a mutable branch name.",
        "missing-action-ref": "Action reference is missing an @ref.",
        "mutable-version-ref": "Action ref is a tag or other mutable ref.",
        "no-workflows-found": "No GitHub Actions workflow files were found.",
        "short-sha-ref": "Action ref is a short SHA.",
    }
    return {
        "id": code,
        "shortDescription": {"text": descriptions.get(code, code)},
        "helpUri": "https://github.com/itscloud0/action-pin-check#usage",
        "properties": {"tags": ["github-actions", "supply-chain"]},
    }


def _sarif_uri(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return path.as_uri()
    return quote(value.replace("\\", "/"), safe="/:")


def _finding_message(finding: Finding) -> str:
    message = f"{finding.message} Fix: {finding.suggestion}"
    if finding.action:
        ref = f"@{finding.ref}" if finding.ref else ""
        message = f"{message} uses: {finding.action}{ref}"
    return message


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
