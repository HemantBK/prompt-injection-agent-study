"""Layer 3: the clean task is not leaky. No-evidence guessers must not recover the exact set."""
import contextlib
import io
import unittest
from pathlib import Path

from scripts import baselines


class Baselines(unittest.TestCase):
    def test_no_evidence_baselines_fail(self):
        with contextlib.redirect_stdout(io.StringIO()):
            baselines.main()
        txt = (Path(__file__).resolve().parents[1] / "results" / "tables" / "baselines.md").read_text()
        for name in ["empty", "everyone", "random3", "no_evidence_mentions", "riskflags_only"]:
            row = [l for l in txt.splitlines() if l.startswith("| " + name + " ")][0]
            k = int(row.split("|")[2].strip().split("/")[0])
            self.assertLessEqual(k, 3, "{} recovers the exact set too often: {}".format(name, row))


if __name__ == "__main__":
    unittest.main()
