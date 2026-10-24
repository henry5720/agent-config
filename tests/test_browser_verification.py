"""逐條判定的公開切點：schema 與 render CLI。"""
import copy
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/verify-in-browser"
FIXTURES = ROOT / "tests/fixtures/browser-verification"


class BrowserVerificationTest(unittest.TestCase):
    def run_cli(self, path):
        return subprocess.run(
            [sys.executable, str(SKILL / "scripts/render-report.py"), str(path)],
            text=True, capture_output=True,
        )

    def test_fixtures_pass_shared_draft07_schema_and_match_operator_table(self):
        schema = json.loads((SKILL / "result.schema.json").read_text())
        Draft7Validator.check_schema(schema)
        validator = Draft7Validator(schema)
        for fixture in sorted(FIXTURES.glob("*.json")):
            with self.subTest(fixture=fixture.name):
                validator.validate(json.loads(fixture.read_text()))
                result = self.run_cli(fixture)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, fixture.with_suffix(".md").read_text())

    def test_invalid_reports_are_rejected_before_any_markdown_is_printed(self):
        original = json.loads((FIXTURES / "mixed.json").read_text())
        variants = []
        extra = copy.deepcopy(original)
        extra["verifier"]["unexpected"] = True
        variants.append(extra)
        no_evidence = copy.deepcopy(original)
        no_evidence["criteria"][0]["evidence"] = []
        variants.append(no_evidence)
        no_reason = copy.deepcopy(original)
        no_reason["criteria"][1]["reason"] = None
        variants.append(no_reason)
        impossible = copy.deepcopy(original)
        impossible["status"] = "unverifiable"
        impossible["unverifiableReason"] = "登入失敗"
        variants.append(impossible)
        outside = copy.deepcopy(original)
        outside["criteria"][0]["evidence"] = ["../auth.json"]
        variants.append(outside)
        inferred_too_many = copy.deepcopy(original)
        inferred_too_many["criteria"].append(copy.deepcopy(original["criteria"][0]))
        variants.append(inferred_too_many)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            for report in variants:
                with self.subTest(report=report):
                    path.write_text(json.dumps(report))
                    result = self.run_cli(path)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("驗收結果不合格", result.stderr)


if __name__ == "__main__":
    unittest.main()
