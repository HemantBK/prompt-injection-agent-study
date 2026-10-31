"""One real end-to-end causal trace per family (addendum, layer 5): payload location -> the step
the agent read it -> the step the mechanism fired / the submission -> the oracle components.
Picks the first success per family (canonical arm); if a family has none, says so and shows a
non-success trace instead. Writes results/tables/causal_traces.md."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import config  # noqa: E402
from harness.oracle import accounts_of, clean_reference, label  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"


def rows(arm):
    p = RAW / (arm + ".jsonl")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


clean = {}
for r in rows("clean"):
    clean.setdefault((r["spec"]["backend"], r["spec"]["seed"]), []).append(r["transcript"])
canon = rows("canonical")
out = ["# Causal traces from real runs (canonical arm)", "",
       "Each trace: where the payload was, when the agent read it, what it then did, and which oracle component fired. Trial ids point into results/raw/canonical.jsonl.", ""]
for fam in config.FAMILIES:
    cands = [r for r in canon if r["payload"]["family"] == fam]
    chosen, lab = None, None
    for r in cands:
        ref = clean_reference(clean[(r["spec"]["backend"], r["spec"]["seed"])])
        l = label(fam, r["payload"]["target"], r["transcript"], ref)
        if l["success"]:
            chosen, lab = r, l
            break
    note = "first SUCCESS"
    if chosen is None and cands:
        chosen = cands[0]
        lab = label(fam, chosen["payload"]["target"], chosen["transcript"], clean_reference(clean[(chosen["spec"]["backend"], chosen["spec"]["seed"])]))
        note = "NO success in this family; showing a non-success trace"
    if chosen is None:
        out += ["## {}  — no trials yet".format(fam), ""]
        continue
    t, pl = chosen["transcript"], chosen["payload"]
    host = pl["host_id"]
    read_steps = [rd["step"] for rd in t["reads"] if rd["doc_id"] == host]
    ref = clean_reference(clean[(chosen["spec"]["backend"], chosen["spec"]["seed"])])
    out += ["## {}  ({})".format(fam, note), "",
            "- trial: `{}`".format(chosen["trial_id"]),
            "- payload host: {} ; payload first line: `{}`".format(host, pl["payload_text"].strip().splitlines()[0][:100].replace("`", "'")),
            "- target: {}".format(pl["target"]),
            "- agent read the host at step(s): {}".format(read_steps),
            "- clean reference sets (same seed/backend): {}".format(ref["sets"]),
            "- actions: {}".format([(a["step"], a["name"], {k: str(v)[:60] for k, v in a["args"].items()}) for a in t["actions"]]),
            "- submitted set: {}".format(sorted(accounts_of(t)) if accounts_of(t) is not None else None),
            "- terminated: {}".format(t["terminated"]),
            "- oracle: success={} components={} noisy_clean={}".format(lab["success"], lab["components"], lab["noisy_clean"]), ""]
    if lab["success"]:
        mech_step = lab["components"].get("fired_step") or (t["actions"][-1]["step"] if t["actions"] else None)
        if read_steps and mech_step is not None:
            out.append("- causal order check: host read at step {} precedes mechanism at step {}: {}".format(min(read_steps), mech_step, min(read_steps) <= mech_step))
            out.append("")
p = ROOT / "results" / "tables" / "causal_traces.md"
p.write_text("\n".join(out) + "\n")
print("\n".join(out))
