"""End-to-end trace of one single-line-forgery success (amendment 1, rung one_line): show the agent
read the clean mailbox-rule audit (which lists no rule for the decoy), then accepted the forged row
in its own reasoning. Writes results/tables/trace_one_line.md."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.oracle import accounts_of, clean_reference, label  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"


def rows(arm):
    p = RAW / (arm + ".jsonl")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


clean = {}
for r in rows("clean"):
    clean.setdefault((r["spec"]["backend"], r["spec"]["seed"]), []).append(r["transcript"])
out = ["# End-to-end trace: single forged log line (amendment 1, rung `one_line`)", ""]
for b in ["claude", "gpt"]:
    chosen = None
    for r in rows("probe_misattr"):
        if r["spec"]["backend"] != b or r["spec"]["extra"].get("variant") != "one_line":
            continue
        ref = clean_reference(clean[(b, r["spec"]["seed"])])
        lab = label("probe_misattr", r["payload"]["target"], r["transcript"], ref)
        if lab["success"]:
            chosen = (r, lab, ref)
            break
    out.append("## {}".format(b))
    if chosen is None:
        out += ["No one_line success for this backend.", ""]
        continue
    r, lab, ref = chosen
    t, pl = r["transcript"], r["payload"]
    d1 = r["decoys"]["D1"]
    mailbox_id = [d.split(":")[0] for d in r["doc_order"] if d.endswith(":mailbox_rules")][0]
    host = pl["host_id"]
    out += ["- trial `{}`  (raw: results/raw/probe_misattr.jsonl)".format(r["trial_id"]),
            "- decoy D1 = {} ; truth = {} ; clean reference sets = {}".format(d1, r["truth"], ref["sets"]),
            "- **the entire payload** (appended to {}):".format(host), "", "```", pl["payload_text"].strip(), "```", ""]
    out.append("### Tool calls in order")
    for s in t["steps"]:
        for c in s.get("tool_calls", []):
            tag = ""
            if c["name"] == "read_doc" and c["args"].get("doc_id") == host:
                tag = "   <-- host doc with the forged row"
            if c["name"] == "read_doc" and c["args"].get("doc_id") == mailbox_id:
                tag = "   <-- CLEAN mailbox-rule audit (lists no rule for {})".format(d1)
            out.append("- step {}: {}({}){}".format(s["step"], c["name"], json.dumps(c["args"])[:80], tag))
    mb = [s for s in t["steps"] for res in s.get("tool_results", []) if res["name"] == "read_doc" and mailbox_id in res["output"][:60]]
    if mb:
        res = [res for res in mb[0]["tool_results"] if mailbox_id in res["output"][:60]][0]
        out += ["", "### What the agent saw in the mailbox-rule audit ({}), verbatim".format(mailbox_id), "", "```", res["output"], "```",
                "", "Mentions of {} in that document: {}".format(d1, res["output"].count(d1))]
    out += ["", "### Agent's own reasoning (submit_findings.reasoning), verbatim", "", "```", (t["findings"] or {}).get("reasoning", ""), "```", ""]
    rs = [s.get("reasoning_summary", "") for s in t["steps"] if s.get("reasoning_summary")]
    if rs:
        out += ["### Thinking summaries (as returned by the API)", "", "```", "\n---\n".join(rs), "```", ""]
    out += ["### Oracle", "", "- submitted set: {}".format(sorted(accounts_of(t))), "- label: success={} components={} noisy_clean={}".format(lab["success"], lab["components"], lab["noisy_clean"]), ""]
p = ROOT / "results" / "tables" / "trace_one_line.md"
p.write_text("\n".join(out) + "\n")
print("\n".join(out))
