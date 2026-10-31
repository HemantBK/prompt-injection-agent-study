import re
import unittest
from itertools import combinations
from pathlib import Path

from attacks.payloads import render_payload
from data.generate import generate
from harness import config

STOP = set("the a an of to and in for is are be this that with by on as at or it its from your you must not do if has have been was were will when before after only all any".split())


def words(t):
    return {w for w in re.findall(r"[a-z_]+", t.lower()) if w not in STOP and len(w) > 2}


class Split(unittest.TestCase):
    def test_split_matches_preregistration(self):
        stats = (Path(__file__).resolve().parents[1] / "STATS.md").read_text()
        self.assertIn("override, delimiter_escape, refusal", stats)
        self.assertIn("tool_hijack, exfiltration, misattribution", stats)
        self.assertEqual(set(config.TRAIN_FAMILIES), {"override", "delimiter_escape", "refusal"})
        self.assertEqual(set(config.TEST_FAMILIES), {"tool_hijack", "exfiltration", "misattribution"})

    def test_cross_split_overlap_below_within_train(self):
        """Mechanical paraphrase screen: no train-test pair overlaps more than the most similar train-train pair."""
        for s in range(3):
            c = generate(s)
            tx = {f: words(render_payload(c, f, "plain")[0]) for f in config.FAMILIES}
            within = max(len(tx[a] & tx[b]) / len(tx[a] | tx[b]) for a, b in combinations(config.TRAIN_FAMILIES, 2))
            for a in config.TRAIN_FAMILIES:
                for b in config.TEST_FAMILIES:
                    j = len(tx[a] & tx[b]) / len(tx[a] | tx[b])
                    self.assertLessEqual(j, within, "{} vs {} overlap {:.2f} exceeds within-train max {:.2f}".format(a, b, j, within))


if __name__ == "__main__":
    unittest.main()
