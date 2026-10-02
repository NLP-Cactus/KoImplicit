"""Check workspace availability and rejection of paths outside its root."""

import json
import tempfile
import unittest
from pathlib import Path

from koimplicit.cli import workspace_status


class WorkspaceCheck(unittest.TestCase):
    def test_workspace_and_path_boundary(self):
        root = Path(__file__).resolve().parents[1]
        report = workspace_status(root)
        self.assertTrue(all(item["exists"] for item in report["paths"].values()))
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            (workspace / "configs").mkdir()
            config = json.loads((root / "configs" / "study.json").read_text(encoding="utf-8"))
            config["paths"] = {"raw": "../outside"}
            (workspace / "configs" / "study.json").write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(ValueError):
                workspace_status(workspace)


if __name__ == "__main__":
    unittest.main()
