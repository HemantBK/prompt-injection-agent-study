"""Remove api_error rows from an arm's raw file (archiving them under results/raw/errors/) and
re-run the arm so the missing trials are retried. Transport errors are not evidence.
Usage: python3 -m scripts.retry_errors <arm> [<arm> ...]"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.runner import RAW, run_arm  # noqa: E402

ERR = RAW / "errors"
ERR.mkdir(exist_ok=True)
for arm in sys.argv[1:]:
    p = RAW / (arm + ".jsonl")
    if not p.exists():
        continue
    keep, drop = [], []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        (drop if row["transcript"].get("terminated") == "api_error" else keep).append(line)
    if drop:
        with (ERR / "{}_errors.jsonl".format(arm)).open("a") as f:
            f.write("\n".join(drop) + "\n")
        p.write_text("\n".join(keep) + ("\n" if keep else ""))
        with (ERR / "README.md").open("a") as f:
            f.write("- {}: {} api_error rows removed from {} and retried\n".format(time.strftime("%Y-%m-%dT%H:%M:%S"), len(drop), arm))
        print("{}: removed {} api_error rows, retrying".format(arm, len(drop)))
        run_arm(arm)
    else:
        print("{}: no api_error rows".format(arm))
