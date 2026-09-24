import unittest
from pathlib import Path

from action_pin_check.scanner import scan_path


class ExampleWorkflowTests(unittest.TestCase):
    def test_github_actions_gate_example_is_clean(self):
        example = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "github-actions"
            / "action-pin-check.yml"
        )

        result = scan_path(example)

        self.assertTrue(result.ok)
        self.assertEqual(result.workflow_count, 1)
        self.assertEqual(result.action_count, 2)

        content = example.read_text(encoding="utf-8")
        self.assertIn(
            "action-pin-check/releases/download/v0.7.0/"
            "action_pin_check-0.7.0-py3-none-any.whl",
            content,
        )
        self.assertNotIn("git+https://github.com/itscloud0/action-pin-check", content)
        self.assertIn("action-pin-check .github/workflows --follow-local-reusable", content)

    def test_public_install_paths_are_pinned_and_checkout_free(self):
        root = Path(__file__).resolve().parents[1]
        wheel_url = (
            "https://github.com/itscloud0/action-pin-check/releases/download/"
            "v0.7.0/action_pin_check-0.7.0-py3-none-any.whl"
        )
        sdist_url = (
            "https://github.com/itscloud0/action-pin-check/releases/download/"
            "v0.7.0/action_pin_check-0.7.0.tar.gz"
        )
        archive_url = (
            "https://github.com/itscloud0/action-pin-check/archive/"
            "e656bf11670c28d2b0d6c64b615a43f697cbd0e4.tar.gz"
        )
        readme = (root / "README.md").read_text(encoding="utf-8")
        launch = (root / "launch.md").read_text(encoding="utf-8")
        workflow = (root / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("If Git is unavailable", readme)
        self.assertIn(wheel_url, readme)
        self.assertIn(sdist_url, readme)
        self.assertIn(archive_url, readme)
        quickstart = readme.split("## 30-second quickstart", 1)[1].split(
            "Example finding:", 1
        )[0]
        self.assertIn(wheel_url, quickstart)
        self.assertIn("action-pin-check .github/workflows --fail-on never", quickstart)
        self.assertNotIn("action-pin-check examples/workflows", quickstart)
        self.assertNotIn("git+https://github.com/itscloud0/action-pin-check", quickstart)
        self.assertIn("Does not fetch or inspect remote reusable workflow internals by default", launch)
        self.assertIn("`--follow-remote-reusable`", launch)
        public_job = workflow.split("  public-install:", 1)[1].split(
            "  public-archive-install:", 1
        )[0]
        self.assertIn(wheel_url, public_job)
        self.assertNotIn("      - uses: actions/checkout@", public_job)
        archive_job = workflow.split("  public-archive-install:", 1)[1]
        self.assertIn(archive_url, archive_job)
        archive_setup = archive_job.split(
            "      - name: Install public release archive", 1
        )[0]
        self.assertNotIn("actions/checkout@", archive_setup)
        self.assertIn("action_pin_check --version", archive_job)


if __name__ == "__main__":
    unittest.main()
