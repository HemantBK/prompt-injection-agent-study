"""Layer 4: every label is computed from a logged transcript, never a literal in a results file."""
import json
import re
import unittest
from pathlib import Path

from harness.oracle import clean_reference, label

ROOT = Path(__file__).resolve().parents[1]


class NoHardcoding(unittest.TestCase):
    def test_tables_import_oracle_and_contain_no_literal_labels(self):
        src = (ROOT / "scripts" / "make_tables.py").read_text()
        self.assertIn("from harness.oracle import", src)
        self.assertIsNone(re.search(r'["\']success["\']\s*:\s*(True|False|1|0)\b', src))
        runner = (ROOT / "harness" / "runner.py").read_text()
        self.assertIsNone(re.search(r"(from|import)\s+harness\.oracle|\blabel\(", runner),
                          "runner.py must not import the oracle or compute labels at run time")

    def test_raw_rows_carry_no_labels(self):
        for p in (ROOT / "results" / "raw").glob("*.jsonl"):
            for line in p.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self.assertNotIn("success", row, p.name)
                    self.assertNotIn("success", row["transcript"], p.name)

    def test_every_published_label_recomputes_from_raw(self):
        labels = ROOT / "results" / "tables" / "labels.jsonl"
        if not labels.exists():
            self.skipTest("no labels.jsonl yet (make tables not run)")
        raw = {}
        for p in (ROOT / "results" / "raw").glob("*.jsonl"):
            for line in p.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    raw[r["trial_id"]] = r
        clean = {}
        for r in raw.values():
            if r["spec"]["arm"] == "clean":
                clean.setdefault((r["spec"]["backend"], r["spec"]["seed"]), []).append(r["transcript"])
        n = 0
        for line in labels.read_text().splitlines():
            lab = json.loads(line)
            r = raw[lab["trial_id"]]
            ref = clean_reference(clean[(r["spec"]["backend"], r["spec"]["seed"])])
            fam = "override" if r["payload"]["family"] == "poison" else r["payload"]["family"]
            re_lab = label(fam, r["payload"]["target"], r["transcript"], ref)
            self.assertEqual(re_lab["success"], lab["success"], lab["trial_id"])
            n += 1
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
