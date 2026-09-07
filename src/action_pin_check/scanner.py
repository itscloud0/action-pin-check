from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

USES_RE = re.compile(r"^\s*(?:-\s*)?uses\s*:\s*['\"]?([^'\"\s#]+)")
SHA_RE = re.compile(r"^[a-fA-F0-9]{40,64}$")
SHORT_SHA_RE = re.compile(r"^[a-fA-F0-9]{7,39}$")
FLOATING_REFS = {"main", "master", "trunk", "develop", "dev", "head"}
DEFAULT_CONFIG_NAME = ".action-pin-check.json"
REMOTE_WORKFLOW_MAX_BYTES = 1_000_000
REMOTE_WORKFLOW_TIMEOUT_SECONDS = 10


class ConfigError(ValueError):
    """Raised when an action-pin-check config file is invalid."""


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
    repository_url: str | None = None

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


@dataclass(frozen=True)
class _RemoteWorkflow:
    owner: str
    repository: str
    path: str
    ref: str

    @property
    def identity(self) -> str:
        return f"{self.owner}/{self.repository}/{self.path}@{self.ref}"

    @property
    def file_label(self) -> str:
        return f"github://{self.identity}"

    @property
    def repository_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repository}"

    @property
    def raw_url(self) -> str:
        path = quote(self.path, safe="/._-")
        ref = quote(self.ref, safe="")
        return (
            f"https://raw.githubusercontent.com/{self.owner}/"
            f"{self.repository}/{ref}/{path}"
        )


class RemoteWorkflowFetchError(RuntimeError):
    """Raised when an opted-in remote reusable workflow cannot be fetched."""


def scan_path(
    path: str | Path,
    config_path: str | Path | None = None,
    follow_local_reusable: bool = False,
    follow_remote_reusable: bool = False,
) -> ScanResult:
    root = Path(path).resolve()
    allowed_tag_refs = _load_allowed_tag_refs(root, config_path)
    repository_root = _repository_root(root)
    workflows = list(_workflow_files(root))
    pending_workflows: list[Path | _RemoteWorkflow] = list(workflows)
    scanned_workflows: set[Path | _RemoteWorkflow] = set()
    findings: list[Finding] = []
    action_count = 0

    while pending_workflows:
        workflow = pending_workflows.pop(0)
        if workflow in scanned_workflows:
            continue
        scanned_workflows.add(workflow)
        if isinstance(workflow, _RemoteWorkflow):
            (
                workflow_findings,
                workflow_action_count,
                local_workflows,
                remote_workflows,
            ) = _scan_workflow(
                workflow,
                root,
                allowed_tag_refs,
                None,
                follow_remote_reusable,
            )
        else:
            (
                workflow_findings,
                workflow_action_count,
                local_workflows,
                remote_workflows,
            ) = _scan_workflow(
                workflow,
                root,
                allowed_tag_refs,
                repository_root if follow_local_reusable else None,
                follow_remote_reusable,
            )
        findings.extend(workflow_findings)
        action_count += workflow_action_count
        for local_workflow in local_workflows:
            if local_workflow not in scanned_workflows:
                pending_workflows.append(local_workflow)
        for remote_workflow in remote_workflows:
            if remote_workflow not in scanned_workflows:
                pending_workflows.append(remote_workflow)

    if not scanned_workflows:
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
        workflow_count=len(scanned_workflows),
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


def _repository_root(root: Path) -> Path:
    if root.is_file():
        if root.parent.name == "workflows" and root.parent.parent.name == ".github":
            return root.parent.parent.parent
        return root.parent
    if root.name == "workflows" and root.parent.name == ".github":
        return root.parent.parent
    return root


def _scan_workflow(
    workflow: Path | _RemoteWorkflow,
    root: Path,
    allowed_tag_refs: set[str],
    reusable_root: Path | None = None,
    follow_remote_reusable: bool = False,
) -> tuple[
    list[Finding],
    int,
    tuple[Path, ...],
    tuple[_RemoteWorkflow, ...],
]:
    findings: list[Finding] = []
    action_count = 0
    local_workflows: list[Path] = []
    remote_workflows: list[_RemoteWorkflow] = []

    try:
        if isinstance(workflow, _RemoteWorkflow):
            lines = _fetch_remote_workflow(workflow).splitlines()
        else:
            lines = workflow.read_text(encoding="utf-8").splitlines()
    except RemoteWorkflowFetchError as exc:
        return ([_remote_fetch_finding(workflow, str(exc))], 0, (), ())
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
            if reusable_root is not None:
                local_workflow = _resolve_local_reusable_workflow(spec, reusable_root)
                if local_workflow is not None:
                    local_workflows.append(local_workflow)
            elif isinstance(workflow, _RemoteWorkflow) and follow_remote_reusable:
                remote_workflow = _resolve_remote_relative_workflow(spec, workflow)
                if remote_workflow is not None:
                    remote_workflows.append(remote_workflow)
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

        if follow_remote_reusable:
            remote_workflow = _resolve_remote_reusable_workflow(spec)
            if remote_workflow is not None:
                remote_workflows.append(remote_workflow)

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
        elif f"{action}@{ref}" not in allowed_tag_refs:
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

    return findings, action_count, tuple(local_workflows), tuple(remote_workflows)


def _load_allowed_tag_refs(
    root: Path,
    config_path: str | Path | None,
) -> set[str]:
    path = _resolve_config_path(root, config_path)
    if path is None:
        return set()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Unable to read config {path}: {exc}") from exc

    if not isinstance(payload, Mapping):
        raise ConfigError(f"Config {path} must contain a JSON object.")

    allowed = payload.get("allowed_tag_refs", [])
    if not isinstance(allowed, list) or not all(
        isinstance(value, str) for value in allowed
    ):
        raise ConfigError(
            f"Config {path} field 'allowed_tag_refs' must be a list of strings."
        )

    return {value for value in allowed if value}


def _resolve_config_path(
    root: Path,
    config_path: str | Path | None,
) -> Path | None:
    if config_path is not None:
        path = Path(config_path).expanduser().resolve()
        if not path.is_file():
            raise ConfigError(f"Config file does not exist: {path}")
        return path

    config_root = root
    if root.is_file():
        config_root = root.parent
    elif root.name == "workflows" and root.parent.name == ".github":
        config_root = root.parent.parent

    candidate = config_root / DEFAULT_CONFIG_NAME
    return candidate if candidate.is_file() else None


def _is_local_or_docker_action(spec: str) -> bool:
    return spec.startswith(("./", "../", "$/", "docker://"))


def _resolve_local_reusable_workflow(
    spec: str,
    repository_root: Path,
) -> Path | None:
    if spec.startswith("./"):
        relative = spec[2:]
    elif spec.startswith("$/"):
        relative = spec[2:]
    else:
        return None

    relative_path = Path(relative)
    if relative_path.suffix.lower() not in {".yml", ".yaml"}:
        return None

    candidate = (repository_root / relative_path).resolve()
    try:
        candidate.relative_to(repository_root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _resolve_remote_reusable_workflow(spec: str) -> _RemoteWorkflow | None:
    action, ref = _split_action_ref(spec)
    if not ref:
        return None
    parts = action.split("/")
    if len(parts) < 3:
        return None
    owner, repository = parts[:2]
    path = "/".join(parts[2:])
    if not _valid_remote_workflow_reference(owner, repository, path):
        return None
    return _RemoteWorkflow(owner, repository, path, ref)


def _resolve_remote_relative_workflow(
    spec: str,
    parent: _RemoteWorkflow,
) -> _RemoteWorkflow | None:
    if spec.startswith("./"):
        path = spec[2:]
    elif spec.startswith("$/"):
        path = spec[2:]
    else:
        return None
    if not _valid_remote_workflow_reference(parent.owner, parent.repository, path):
        return None
    return _RemoteWorkflow(parent.owner, parent.repository, path, parent.ref)


def _valid_remote_workflow_reference(
    owner: str,
    repository: str,
    path: str,
) -> bool:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", repository):
        return False
    parts = path.split("/")
    return (
        len(parts) >= 3
        and parts[:2] == [".github", "workflows"]
        and parts[-1].lower().endswith((".yml", ".yaml"))
        and all(part not in {"", ".", ".."} for part in parts)
    )


def _fetch_remote_workflow(workflow: _RemoteWorkflow) -> str:
    request = Request(
        workflow.raw_url,
        headers={
            "Accept": "text/plain",
            "User-Agent": "action-pin-check",
        },
    )
    try:
        with urlopen(request, timeout=REMOTE_WORKFLOW_TIMEOUT_SECONDS) as response:
            payload = response.read(REMOTE_WORKFLOW_MAX_BYTES + 1)
    except HTTPError as exc:
        raise RemoteWorkflowFetchError(f"HTTP {exc.code}") from exc
    except (OSError, TimeoutError, URLError) as exc:
        raise RemoteWorkflowFetchError(str(exc)) from exc

    if len(payload) > REMOTE_WORKFLOW_MAX_BYTES:
        raise RemoteWorkflowFetchError(
            f"response exceeds {REMOTE_WORKFLOW_MAX_BYTES} bytes"
        )
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RemoteWorkflowFetchError("response is not valid UTF-8") from exc


def _remote_fetch_finding(workflow: _RemoteWorkflow, reason: str) -> Finding:
    return Finding(
        severity="error",
        code="remote-workflow-fetch-failed",
        file=workflow.file_label,
        line=0,
        action=f"{workflow.owner}/{workflow.repository}/{workflow.path}",
        ref=workflow.ref,
        message=f"Unable to fetch remote reusable workflow: {reason}.",
        suggestion=(
            "Verify the public repository, workflow path, and ref, or rerun "
            "without --follow-remote-reusable."
        ),
        repository_url=workflow.repository_url,
    )


def _split_action_ref(spec: str) -> tuple[str, str]:
    if "@" not in spec:
        return spec, ""
    action, ref = spec.rsplit("@", 1)
    return action, ref


def _finding(
    severity: str,
    code: str,
    workflow: str | Path,
    root: Path,
    line: int,
    action: str,
    ref: str,
    message: str,
    suggestion: str,
) -> Finding:
    if isinstance(workflow, Path):
        try:
            file_name = str(workflow.relative_to(root))
        except ValueError:
            file_name = str(workflow)
    elif isinstance(workflow, _RemoteWorkflow):
        file_name = workflow.file_label
    else:
        file_name = workflow
    return Finding(
        severity=severity,
        code=code,
        file=file_name,
        line=line,
        action=action,
        ref=ref,
        message=message,
        suggestion=suggestion,
        repository_url=_action_repository_url(action),
    )


def _action_repository_url(action: str) -> str | None:
    parts = action.split("/")
    if len(parts) < 2 or any(
        not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts[:2]
    ):
        return None
    owner, repository = (quote(part, safe="._-~") for part in parts[:2])
    return f"https://github.com/{owner}/{repository}"
