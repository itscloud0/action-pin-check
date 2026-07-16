import tempfile
import unittest
from pathlib import Path

from action_pin_check.scanner import exit_code_for, scan_path


PINNED_SHA = "0123456789abcdef0123456789abcdef01234567"


class ScannerTests(unittest.TestCase):
    def test_config_allows_exact_tag_refs_but_not_branches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = root / "ci.yml"
            workflow.write_text(
                "steps:\n"
                "  - uses: actions/checkout@v4\n"
                "  - uses: actions/setup-python@main\n"
                "  - uses: actions/setup-node@v4\n",
                encoding="utf-8",
            )
            config = root / ".action-pin-check.json"
            config.write_text(
                '{"allowed_tag_refs": ["actions/checkout@v4"]}\n',
                encoding="utf-8",
            )

            result = scan_path(root)

        self.assertEqual(
            [finding.code for finding in result.findings],
            ["floating-branch-ref", "mutable-version-ref"],
        )
        self.assertEqual(result.findings[1].action, "actions/setup-node")

    def test_explicit_config_path_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflows"
            root.mkdir()
            (root / "ci.yml").write_text(
                "steps:\n  - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            config = Path(tmp) / "policy.json"
            config.write_text(
                '{"allowed_tag_refs": ["actions/checkout@v4"]}\n',
                encoding="utf-8",
            )

            result = scan_path(root, config_path=config)

        self.assertTrue(result.ok)

    def test_detects_mutable_and_missing_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_dir = root / ".github" / "workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "ci.yml").write_text(
                "\n".join(
                    [
                        "name: ci",
                        "on: [push]",
                        "jobs:",
                        "  test:",
                        "    runs-on: ubuntu-latest",
                        "    steps:",
                        "      - uses: actions/checkout@v4",
                        "      - uses: actions/setup-python@main",
                        "      - uses: acme/no-ref",
                        "      - uses: ./local-action",
                        f"      - uses: owner/pinned@{PINNED_SHA}",
                    ]
                ),
                encoding="utf-8",
            )

            result = scan_path(root)

        codes = [finding.code for finding in result.findings]
        self.assertEqual(result.workflow_count, 1)
        self.assertEqual(result.action_count, 4)
        self.assertEqual(
            codes,
            ["mutable-version-ref", "floating-branch-ref", "missing-action-ref"],
        )

    def test_full_sha_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "safe.yml"
            workflow.write_text(
                "\n".join(
                    [
                        "jobs:",
                        "  test:",
                        "    steps:",
                        f"      - uses: actions/checkout@{PINNED_SHA}",
                    ]
                ),
                encoding="utf-8",
            )

            result = scan_path(workflow)

        self.assertTrue(result.ok)
        self.assertEqual(result.action_count, 1)

    def test_reusable_workflow_calls_count_remote_refs_and_skip_local_paths(self):
        fixture = Path(__file__).parent / "fixtures" / "reusable-workflow.yml"

        result = scan_path(fixture.parent)

        self.assertEqual(result.action_count, 1)
        self.assertEqual(len(result.findings), 1)
        finding = result.findings[0]
        self.assertEqual(finding.code, "floating-branch-ref")
        self.assertEqual(
            finding.action,
            "acme/platform/.github/workflows/reusable.yml",
        )
        self.assertEqual(finding.ref, "main")
        self.assertEqual(finding.file, "reusable-workflow.yml")

    def test_quoted_uses_values_and_inline_comments(self):
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "quoted"
            / "quoted-and-commented.yml"
        )

        result = scan_path(fixture)

        self.assertEqual(result.action_count, 3)
        self.assertEqual(
            [(finding.code, finding.action, finding.ref, finding.line)
             for finding in result.findings],
            [
                (
                    "mutable-version-ref",
                    "acme/platform/.github/workflows/reusable.yml",
                    "v3",
                    8,
                ),
                ("floating-branch-ref", "actions/checkout", "main", 16),
            ],
        )

    def test_exit_code_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "ci.yml"
            workflow.write_text(
                "steps:\n  - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            result = scan_path(workflow)

        self.assertEqual(exit_code_for(result, "warning"), 1)
        self.assertEqual(exit_code_for(result, "error"), 0)
        self.assertEqual(exit_code_for(result, "never"), 0)

    def test_no_workflows_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = scan_path(tmp)

        self.assertFalse(result.ok)
        self.assertEqual(result.findings[0].code, "no-workflows-found")


if __name__ == "__main__":
    unittest.main()
