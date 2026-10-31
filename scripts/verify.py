"""`make verify`: run every fixture test, print PASS/FAIL per trust layer, exit non-zero on any failure."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LAYERS = [
    ("1 ORACLE TRUST", ["tests.test_oracle"]),
    ("2 ENVIRONMENT / HARNESS INTEGRITY", ["tests.test_tools", "tests.test_generator", "tests.test_payload_path"]),
    ("3 DIFFICULTY CALIBRATION", ["tests.test_baselines"]),
    ("4 REPRODUCIBILITY / NO HARDCODING", ["tests.test_stats", "tests.test_no_hardcoding"]),
    ("5 CHEAT / GAMING DETECTION", ["tests.test_e2e_mock"]),
    ("6 STATISTICAL & SPLIT DISCIPLINE", ["tests.test_monitor", "tests.test_split"]),
]


def main():
    ok_all = True
    for name, mods in LAYERS:
        suite = unittest.TestSuite()
        for m in mods:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromName(m))
        res = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0).run(suite)
        ok = res.wasSuccessful()
        ok_all &= ok
        print("{:<40} {}  ({} tests, {} failures, {} errors, {} skipped)".format(name, "PASS" if ok else "FAIL", res.testsRun, len(res.failures), len(res.errors), len(res.skipped)))
        for t, tb in res.failures + res.errors:
            print("    - {}\n      {}".format(t.id(), tb.strip().splitlines()[-1]))
    print("\nVERIFY:", "GREEN" if ok_all else "RED")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
