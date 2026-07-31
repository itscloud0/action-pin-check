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


if __name__ == "__main__":
    unittest.main()
