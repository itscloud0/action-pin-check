from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Iterable

USES_RE = re.compile(r"^\s*(?:-\s*)?uses\s*:\s*['\"]?([^'\"\s#]+)")
SHA_RE = re.compile(r"^[a-fA-F0-9]{40,64}$")
SHORT_SHA_RE = re.compile(r"^[a-fA-F0-9]{7,39}$")
FLOATING_REFS = {"main", "master", "trunk", "develop", "dev", "head"}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    file: str
    line: int
    action: str
    ref: str
    message: str
    suggestion: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScanResult:
    root: str
    workflow_count: int
    action_count: int
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "ok": self.ok,
            "workflow_count": self.workflow_count,
            "action_count": self.action_count,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def scan_path(path: str | Path) -> ScanResult:
    root = Path(path).resolve()
    workflows = tuple(_workflow_files(root))
    findings: list[Finding] = []
    action_count = 0

    for workflow in workflows:
        workflow_findings, workflow_action_count = _scan_workflow(workflow, root)
        findings.extend(workflow_findings)
        action_count += workflow_action_count

    if not workflows:
        findings.append(
            Finding(
                severity="error",
                code="no-workflows-found",
                file=str(root),
                line=0,
                action="",
                ref="",
                message="No GitHub Actions workflow files were found.",
                suggestion="Run this at a repository root or pass a workflow file/directory.",
            )
        )

    return ScanResult(
        root=str(root),
        workflow_count=len(workflows),
        action_count=action_count,
        findings=tuple(findings),
    )


def exit_code_for(result: ScanResult, fail_on: str) -> int:
    if fail_on == "never":
        return 0
    severities = {finding.severity for finding in result.findings}
    if fail_on == "error":
        return 1 if "error" in severities else 0
    return 1 if severities.intersection({"error", "warning"}) else 0


def _workflow_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() in {".yml", ".yaml"}:
            yield root
        return

    workflow_dir = root
    if (root / ".github" / "workflows").is_dir():
        workflow_dir = root / ".github" / "workflows"

    if not workflow_dir.is_dir():
        return

    for pattern in ("*.yml", "*.yaml"):
        yield from sorted(workflow_dir.glob(pattern))


def _scan_workflow(workflow: Path, root: Path) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    action_count = 0

    try:
        lines = workflow.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = workflow.read_text(errors="replace").splitlines()

    for line_number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("#"):
            continue
        match = USES_RE.match(line)
        if not match:
            continue

        spec = match.group(1).rstrip(",")
        if _is_local_or_docker_action(spec):
            continue

        action_count += 1
        action, ref = _split_action_ref(spec)
        if ref == "":
            findings.append(
                _finding(
                    "error",
                    "missing-action-ref",
                    workflow,
                    root,
                    line_number,
                    action,
                    ref,
                    "Action reference is missing an @ref.",
                    f"Pin {action} to a full commit SHA.",
                )
            )
            continue

        normalized = ref.lower()
        if SHA_RE.fullmatch(ref):
            continue
        if SHORT_SHA_RE.fullmatch(ref):
            findings.append(
                _finding(
                    "warning",
                    "short-sha-ref",
                    workflow,
                    root,
                    line_number,
                    action,
                    ref,
                    "Action is pinned to a short SHA.",
                    "Use the full commit SHA so the ref is unambiguous.",
                )
            )
        elif normalized in FLOATING_REFS or normalized.startswith("refs/heads/"):
            findings.append(
                _finding(
                    "error",
                    "floating-branch-ref",
                    workflow,
                    root,
                    line_number,
                    action,
                    ref,
                    "Action is pinned to a mutable branch ref.",
                    "Replace the branch with a reviewed full commit SHA.",
                )
            )
        else:
            findings.append(
                _finding(
                    "warning",
                    "mutable-version-ref",
                    workflow,
                    root,
                    line_number,
                    action,
                    ref,
                    "Action uses a tag or other mutable ref.",
                    "For stronger supply-chain control, pin to a full commit SHA.",
                )
            )

    return findings, action_count


def _is_local_or_docker_action(spec: str) -> bool:
    return spec.startswith(("./", "../", "docker://"))


def _split_action_ref(spec: str) -> tuple[str, str]:
    if "@" not in spec:
        return spec, ""
    action, ref = spec.rsplit("@", 1)
    return action, ref


def _finding(
    severity: str,
    code: str,
    workflow: Path,
    root: Path,
    line: int,
    action: str,
    ref: str,
    message: str,
    suggestion: str,
) -> Finding:
    try:
        file_name = str(workflow.relative_to(root))
    except ValueError:
        file_name = str(workflow)
    return Finding(
        severity=severity,
        code=code,
        file=file_name,
        line=line,
        action=action,
        ref=ref,
        message=message,
        suggestion=suggestion,
    )
