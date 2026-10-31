import unittest

from harness.stats import bootstrap_rate, fisher_exact, mcnemar_exact, wilson


class Stats(unittest.TestCase):
    def test_wilson_textbook(self):
        p, lo, hi = wilson(10, 20)
        self.assertAlmostEqual(lo, 0.2993, places=3)
        self.assertAlmostEqual(hi, 0.7007, places=3)
        p, lo, hi = wilson(0, 20)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.1611, places=3)
        p, lo, hi = wilson(20, 20)
        self.assertAlmostEqual(lo, 0.8389, places=3)
        self.assertEqual(hi, 1.0)

    def test_mcnemar_exact(self):
        self.assertAlmostEqual(mcnemar_exact(1, 9), 0.021484375, places=9)   # 2*P(X<=1 | n=10, .5)
        self.assertAlmostEqual(mcnemar_exact(0, 5), 0.0625, places=6)
        self.assertEqual(mcnemar_exact(0, 0), 1.0)
        self.assertEqual(mcnemar_exact(4, 4), 1.0)

    def test_fisher_exact(self):
        # classic tea-tasting table [[3,1],[1,3]] -> two-sided p = 0.4857
        self.assertAlmostEqual(fisher_exact(3, 1, 1, 3), 0.4857, places=3)
        self.assertAlmostEqual(fisher_exact(10, 0, 0, 10), 2 / 184756, places=9)

    def test_bootstrap_bounds(self):
        m, lo, hi = bootstrap_rate([1] * 10 + [0] * 10, n_boot=500)
        self.assertAlmostEqual(m, 0.5)
        self.assertTrue(0.2 <= lo <= 0.5 <= hi <= 0.8)
        m, lo, hi = bootstrap_rate([[1, 1], [1, 1], [1, 1]], n_boot=100)
        self.assertEqual((m, lo, hi), (1.0, 1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
