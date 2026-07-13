import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from action_pin_check.cli import main


class CliTests(unittest.TestCase):
    def test_config_option_allows_reviewed_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "ci.yml"
            workflow.write_text(
                "steps:\n  - uses: actions/checkout@v4\n",
                encoding="utf-8",
            )
            config = Path(tmp) / "policy.json"
            config.write_text(
                '{"allowed_tag_refs": ["actions/checkout@v4"]}\n',
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main([str(workflow), "--config", str(config)])

        self.assertEqual(code, 0)
        self.assertIn("OK:", stdout.getvalue())

    def test_json_output_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "ci.yml"
            workflow.write_text(
                "steps:\n  - uses: actions/checkout@main\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main([str(workflow), "--format", "json", "--fail-on", "never"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["findings"][0]["code"], "floating-branch-ref")

    def test_text_output_for_clean_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "safe.yml"
            workflow.write_text(
                "steps:\n"
                "  - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main([str(workflow)])

        self.assertEqual(code, 0)
        self.assertIn("OK:", stdout.getvalue())

    def test_github_annotations_output_points_to_workflow_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "ci.yml"
            workflow.write_text(
                "steps:\n  - uses: actions/checkout@main\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        tmp,
                        "--format",
                        "github-annotations",
                        "--fail-on",
                        "never",
                    ]
                )

        self.assertEqual(code, 0)
        self.assertEqual(
            stdout.getvalue().strip(),
            "::error file=ci.yml,line=2,title=floating-branch-ref::"
            "Action is pinned to a mutable branch ref. Fix: Replace the branch "
            "with a reviewed full commit SHA. uses: actions/checkout@main",
        )

    def test_github_annotations_output_is_empty_for_clean_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "safe.yml"
            workflow.write_text(
                "steps:\n"
                "  - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main([tmp, "--format", "github-annotations"])

        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_sarif_output_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "ci.yml"
            workflow.write_text(
                "steps:\n  - uses: actions/setup-python@main\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main([tmp, "--format", "sarif", "--fail-on", "never"])

        payload = json.loads(stdout.getvalue())
        run = payload["runs"][0]
        result = run["results"][0]
        self.assertEqual(code, 0)
        self.assertEqual(payload["version"], "2.1.0")
        self.assertEqual(run["tool"]["driver"]["name"], "action-pin-check")
        self.assertEqual(result["ruleId"], "floating-branch-ref")
        self.assertEqual(result["level"], "error")
        self.assertEqual(
            result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            "ci.yml",
        )
        self.assertEqual(
            result["locations"][0]["physicalLocation"]["region"]["startLine"],
            2,
        )

    def test_sarif_output_has_empty_results_for_clean_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "safe.yml"
            workflow.write_text(
                "steps:\n"
                "  - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main([str(workflow), "--format", "sarif"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["runs"][0]["results"], [])


if __name__ == "__main__":
    unittest.main()
