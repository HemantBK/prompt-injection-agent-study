import unittest

from harness.oracle import clean_reference, label
from tests.fixtures_oracle import FIXTURES


class OracleFixtures(unittest.TestCase):
    def test_every_fixture(self):
        wrong = []
        for name, fam, target, t, clean, exp_s, exp_noisy, note in FIXTURES:
            lab = label(fam, target, t, clean_reference(clean))
            if lab["success"] != exp_s or lab["noisy_clean"] != exp_noisy:
                wrong.append("{}: got success={} noisy={} expected {}/{} ({})".format(name, lab["success"], lab["noisy_clean"], exp_s, exp_noisy, note))
        self.assertEqual(wrong, [], "\n".join(wrong))

    def test_fixture_precision_recall_are_perfect_by_construction(self):
        """Report the oracle's precision/recall on the fixture set (should be 1.0/1.0; any drift fails)."""
        tp = fp = fn = 0
        for name, fam, target, t, clean, exp_s, _, _ in FIXTURES:
            got = label(fam, target, t, clean_reference(clean))["success"]
            tp += got and exp_s
            fp += got and not exp_s
            fn += (not got) and exp_s
        self.assertEqual((fp, fn), (0, 0), "oracle fixture precision={:.2f} recall={:.2f}".format(tp / max(1, tp + fp), tp / max(1, tp + fn)))

    def test_fixture_set_has_edge_cases(self):
        names = {f[0] for f in FIXTURES}
        for must in ["refusal_soft_still_submits", "exfil_canary_coincidence_in_reasoning", "override_partial_add_only", "hijack_clean_also_fired"]:
            self.assertIn(must, names)
        self.assertGreaterEqual(len(FIXTURES), 15)


if __name__ == "__main__":
    unittest.main()
