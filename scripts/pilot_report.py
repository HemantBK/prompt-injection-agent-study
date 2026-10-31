"""Report measured $/run, tokens and steps from the pilot (clean seeds 0-9, rep 1) per backend,
and compare with the pre-pilot estimate (Fork 5 stopping rule)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import config  # noqa: E402
from harness.runner import build_arm  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
rows = {}
p = RAW / "clean.jsonl"
if p.exists():
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["trial_id"]] = r
pilot_ids = [s.trial_id for s in build_arm("pilot")]
lines = ["# Pilot report (clean task, seeds 0-9, rep 1)", "", "| backend | runs | mean $/run | max $/run | mean steps | mean in-tokens | mean out-tokens | exact-set correct | mean wall s |", "|---|---|---|---|---|---|---|---|---|"]
total_runs = sum(len(build_arm(a)) for a in ["clean", "placebo", "canonical", "sweep", "tune_clean", "tune_monitor", "defended_test", "defended_train", "defended_clean", "spot_test", "spot_clean", "canonical_rep2", "poison", "probe_length", "probe_elicitation"])
proj = {}
for b in config.BACKENDS:
    rs = [rows[i] for i in pilot_ids if i in rows and rows[i]["spec"]["backend"] == b]
    if not rs:
        lines.append("| {} | 0 | - | - | - | - | - | - | - |".format(b))
        continue
    n = len(rs)
    costs = [r["transcript"]["cost_usd"] for r in rs]
    steps = [len(r["transcript"]["steps"]) for r in rs]
    tin = [r["transcript"]["usage"].get("input_tokens", 0) + r["transcript"]["usage"].get("cache_read_input_tokens", 0) + r["transcript"]["usage"].get("cache_creation_input_tokens", 0) for r in rs]
    tout = [r["transcript"]["usage"].get("output_tokens", 0) for r in rs]
    exact = sum(1 for r in rs if r["transcript"]["findings"] and set(r["transcript"]["findings"]["compromised_accounts"]) == set(r["truth"]))
    wall = [r["transcript"]["wall_s"] for r in rs]
    proj[b] = sum(costs) / n
    lines.append("| {} | {} | ${:.4f} | ${:.4f} | {:.1f} | {:.0f} | {:.0f} | {}/{} | {:.0f} |".format(
        b, n, sum(costs) / n, max(costs), sum(steps) / n, sum(tin) / n, sum(tout) / n, exact, n, sum(wall) / n))
if proj:
    mean = sum(proj.values()) / len(proj)
    lines += ["", "Pre-pilot estimate: ${:.2f}/run. Measured mean: ${:.4f}/run ({:.2f}x estimate).".format(config.EST_COST_PER_RUN, mean, mean / config.EST_COST_PER_RUN),
              "Full matrix: {} agent runs -> projected ${:.0f} (+ monitor classifier calls, small; defended runs cost slightly more because withheld docs change the trajectory).".format(total_runs, total_runs * mean),
              "Fork 5 rule: cut only if measured > 2x estimate (${:.2f}). {}".format(2 * config.EST_COST_PER_RUN, "NO CUT NEEDED." if mean <= 2 * config.EST_COST_PER_RUN else "CUT ORDER APPLIES: sweep -> 2 variants, sweep -> 0, defended_train -> N=10.")]
txt = "\n".join(lines) + "\n"
print(txt)
out = Path(__file__).resolve().parents[1] / "results" / "tables" / "pilot_report.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(txt)
