import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from action_pin_check.cli import main


class CliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
