"""Offline monitor evaluation (no agent runs): doc-level FPR on clean corpora and flag
precision/recall on injected corpora, per family, train and test reported separately.

Usage: python3 -m scripts.monitor_offline [--regex-only] [--mode cascade|always] [--seeds 0-29]
Classifier calls are cheap (Haiku 5.5 / GPT-6 Luna) but are real API calls unless --regex-only."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attacks.placement import apply_payload  # noqa: E402
from data.generate import generate  # noqa: E402
from defense.monitor import Monitor  # noqa: E402
from harness import config  # noqa: E402
from harness.backends import make_classifier  # noqa: E402
from harness.stats import fmt_rate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regex-only", action="store_true")
    ap.add_argument("--mode", default="cascade")
    ap.add_argument("--seeds", default="0-9")
    ap.add_argument("--families", default="train", help="train | test | all  (test families only after tuning is frozen)")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    fams = {"train": config.TRAIN_FAMILIES, "test": config.TEST_FAMILIES, "all": config.FAMILIES}[a.families]
    out = {"mode": "regex" if a.regex_only else a.mode, "seeds": seeds, "clean": {}, "families": {}}
    for key in config.BACKENDS:
        clf = None if a.regex_only else make_classifier(key)
        mon = Monitor(classifier=clf, mode=a.mode)
        fp = total = 0
        for s in seeds:
            for d in generate(s).docs:
                total += 1
                if mon.check(d)["fired"]:
                    fp += 1
        out["clean"][key] = {"fp": fp, "n": total, "cost": mon.cost_usd}
        for fam in fams:
            tp = n = 0
            for s in seeds:
                corp, meta = apply_payload(generate(s), fam)
                n += 1
                if mon.check(corp.doc(meta["host_id"]))["fired"]:
                    tp += 1
            out["families"].setdefault(fam, {})[key] = {"tp": tp, "n": n}
        out["clean"][key]["cost"] = mon.cost_usd
        if a.regex_only:
            break   # regex is model-independent
    lines = ["# Offline monitor evaluation  (mode={}, seeds {})".format(out["mode"], a.seeds), "",
             "| classifier for | clean docs flagged (doc-level FPR) | cost |", "|---|---|---|"]
    for k, v in out["clean"].items():
        lines.append("| {} | {} | ${:.3f} |".format(k, fmt_rate(v["fp"], v["n"]), v["cost"]))
    lines += ["", "| family | split | classifier for | host doc flagged (recall) |", "|---|---|---|---|"]
    for fam, d in out["families"].items():
        for k, v in d.items():
            lines.append("| {} | {} | {} | {} |".format(fam, "train" if fam in config.TRAIN_FAMILIES else "TEST", k, fmt_rate(v["tp"], v["n"])))
    txt = "\n".join(lines) + "\n"
    print(txt)
    p = Path(__file__).resolve().parents[1] / "results" / "tables" / "monitor_offline_{}_{}.md".format(out["mode"], a.families)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)
    (p.with_suffix(".json")).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
