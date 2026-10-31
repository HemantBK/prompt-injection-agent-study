"""Run one arm (or 'pilot'): python3 -m scripts.run_arm canonical [--workers 6]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import config  # noqa: E402
from harness.runner import ALL_ARMS, run_arm  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("arm", choices=ALL_ARMS + ["pilot"])
ap.add_argument("--workers", type=int, default=config.WORKERS)
a = ap.parse_args()
rows = run_arm(a.arm, workers=a.workers)
if rows:
    cost = sum(r["transcript"]["cost_usd"] + r["transcript"]["defense_cost_usd"] for r in rows)
    print("\n{} rows; measured ${:.4f}/run; total ${:.2f}".format(len(rows), cost / len(rows), cost))
