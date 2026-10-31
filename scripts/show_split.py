"""Render train vs test payloads side by side for the Fork 4 paraphrase check.
Writes results/tables/split_review.md. Also prints content-word Jaccard overlap between every
pair of families as a crude, mechanical paraphrase screen."""
import re
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attacks.payloads import render_payload  # noqa: E402
from data.generate import generate  # noqa: E402
from harness import config  # noqa: E402

STOP = set("the a an of to and in for is are be this that with by on as at or it its from your you must not do if "
           "has have been was were will when before after only all any".split())


def words(t):
    return {w for w in re.findall(r"[a-z_]+", t.lower()) if w not in STOP and len(w) > 2}


seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
c = generate(seed)
texts = {f: render_payload(c, f, "plain")[0] for f in config.FAMILIES}
targets = {f: render_payload(c, f, "plain")[1] for f in config.FAMILIES}
lines = ["# Train / test payload review (seed {}, canonical plain framing)".format(seed), "",
         "Fork 4 split. Defense regexes and classifier prompt were written from TRAIN only.", ""]
for split, fams in [("TRAIN (defense tuned here)", config.TRAIN_FAMILIES), ("TEST (held-out; headline defense numbers)", config.TEST_FAMILIES)]:
    lines.append("## {}".format(split))
    for f in fams:
        lines += ["", "### {}  -> oracle target: {}".format(f, targets[f]), "", "```", texts[f].strip("\n"), "```"]
    lines.append("")
lines += ["## Mechanical paraphrase screen: content-word Jaccard overlap", "",
          "| family A | family B | pair type | Jaccard | shared words |", "|---|---|---|---|---|"]
rows = []
for a, b in combinations(config.FAMILIES, 2):
    wa, wb = words(texts[a]), words(texts[b])
    j = len(wa & wb) / len(wa | wb)
    kind = "within-train" if a in config.TRAIN_FAMILIES and b in config.TRAIN_FAMILIES else \
           "within-test" if a in config.TEST_FAMILIES and b in config.TEST_FAMILIES else "CROSS (train-test)"
    rows.append((j, a, b, kind, sorted(wa & wb)))
for j, a, b, kind, shared in sorted(rows, reverse=True):
    lines.append("| {} | {} | {} | {:.2f} | {} |".format(a, b, kind, j, ", ".join(shared)[:120]))
lines += ["", "Reading: a CROSS pair with overlap at or above the highest within-train pair would indicate paraphrase leakage. "
          "Shared tokens like 'findings', 'account', 'assistant', 'submitting' are the task vocabulary, not the attack mechanism; "
          "the mechanism difference per pair is stated in DECISIONS.md Fork 4."]
out = Path(__file__).resolve().parents[1] / "results" / "tables" / "split_review.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
