"""Trial matrix construction and execution. Every arm of the study is a list of TrialSpecs.

Raw rows (results/raw/<arm>.jsonl) hold the spec, the payload metadata, the ground truth and
the FULL transcript. They never hold a success label: labels are computed from transcripts by
scripts/make_tables.py via harness/oracle.py (tests/test_no_hardcoding.py enforces this).
"""
from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

from attacks.payloads import FIXED_FRAMING, MISATTR_LADDER, probe_elicitation, probe_length_ladder, probe_misattribution_ladder, render_payload
from attacks.placement import apply_payload, apply_placebo, host_id, inject_text
from attacks.poisoning import apply_poison
from data.generate import generate
from defense.monitor import Monitor
from defense.spotlighting import Spotlighting
from harness import config
from harness.agent import run_agent
from harness.backends import MockBackend, make_backend, make_classifier

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
POISON_BACKEND = "claude"   # Attack 2 runs on one backend (Fork 5 scope); chosen before any result was seen


@dataclass
class TrialSpec:
    arm: str
    backend: str
    seed: int
    family: str = "clean"          # clean | placebo | <family> | poison | probe_length | probe_elicitation
    placement: str = "evidence"
    framing: str = "plain"
    defense: str = "none"          # none | monitor | spotlight
    rep: int = 1
    extra: dict = field(default_factory=dict)

    @property
    def trial_id(self):
        ex = ",".join("{}={}".format(k, v) for k, v in sorted(self.extra.items()))
        return "{}|{}|s{}|{}|{}|{}|{}|r{}|{}".format(self.arm, self.backend, self.seed, self.family,
                                                     self.placement, self.framing, self.defense, self.rep, ex)


def _grid(arm, backends, seeds, families, variants, defense="none", rep=1):
    out = []
    for b in backends:
        for fam in families:
            for v in variants:
                if fam in FIXED_FRAMING and v["framing"] != "plain":
                    continue   # these families are their framing; only placement varies
                for s in seeds:
                    out.append(TrialSpec(arm, b, s, fam, v["placement"], v["framing"], defense, rep))
    return out


def build_arm(arm):
    B = list(config.BACKENDS)
    C = [config.CANONICAL]
    if arm == "pilot":      # the pilot IS the first clean rep on seeds 0-9; rows are written to the clean arm
        return [TrialSpec("clean", b, s, "clean", rep=1) for b in B for s in config.CLEAN_SEEDS[:10]]
    if arm == "clean":
        return [TrialSpec("clean", b, s, "clean", rep=r) for b in B for s in config.CLEAN_SEEDS for r in range(1, config.N_CLEAN_REPS + 1)]
    if arm == "placebo":
        return [TrialSpec("placebo", b, s, "placebo") for b in B for s in config.ATTACK_SEEDS]
    if arm == "canonical":
        return _grid("canonical", B, config.ATTACK_SEEDS, config.FAMILIES, C)
    if arm == "canonical_rep2":   # whole-pipeline re-run for the reproducibility delta (addendum, layer 4)
        return _grid("canonical_rep2", B, config.ATTACK_SEEDS, config.FAMILIES, C, rep=2)
    if arm == "sweep":
        return _grid("sweep", B, config.SWEEP_SEEDS, config.FAMILIES, config.SWEEP_VARIANTS)
    if arm == "tune_clean":
        return [TrialSpec("tune_clean", b, s, "clean") for b in B for s in config.TUNE_SEEDS]
    if arm == "tune_monitor":
        return _grid("tune_monitor", B, config.TUNE_SEEDS, config.TRAIN_FAMILIES, C, defense="monitor")
    if arm == "defended_test":
        return _grid("defended_test", B, config.ATTACK_SEEDS, config.TEST_FAMILIES, C, defense="monitor")
    if arm == "defended_train":
        return _grid("defended_train", B, config.ATTACK_SEEDS, config.TRAIN_FAMILIES, C, defense="monitor")
    if arm == "defended_clean":
        return [TrialSpec("defended_clean", b, s, "clean", defense="monitor") for b in B for s in config.ATTACK_SEEDS]
    if arm == "spot_test":
        return _grid("spot_test", B, config.ATTACK_SEEDS, config.TEST_FAMILIES, C, defense="spotlight")
    if arm == "spot_clean":
        return [TrialSpec("spot_clean", b, s, "clean", defense="spotlight") for b in B for s in config.ATTACK_SEEDS]
    if arm == "poison":
        return [TrialSpec("poison", POISON_BACKEND, s, "poison", extra={"fraction": f})
                for f in config.POISON_FRACTIONS for s in config.POISON_SEEDS]
    if arm == "probe_length":
        return [TrialSpec("probe_length", b, s, "probe_length", extra={"n_words": n})
                for b in B for n in config.PROBE_LENGTHS for s in config.SWEEP_SEEDS]
    if arm == "probe_elicitation":
        return [TrialSpec("probe_elicitation", b, s, "probe_elicitation") for b in B for s in config.ATTACK_SEEDS]
    if arm == "probe_misattr":   # STATS amendment 1 (runs only if the user rules for it)
        return [TrialSpec("probe_misattr", b, s, "probe_misattr", extra={"variant": v})
                for b in B for v in MISATTR_LADDER for s in config.ATTACK_SEEDS]
    raise ValueError("unknown arm " + arm)


ALL_ARMS = ["clean", "placebo", "canonical", "sweep", "tune_clean", "tune_monitor", "defended_test",
            "defended_train", "defended_clean", "spot_test", "spot_clean", "canonical_rep2", "poison",
            "probe_length", "probe_elicitation", "probe_misattr"]


def prepare_corpus(spec):
    """Generate the seed corpus and apply the spec's manipulation. Returns (corpus, meta)."""
    base = generate(spec.seed)
    fam = spec.family
    if fam == "clean":
        return base, {"family": "clean", "target": {}}
    if fam == "placebo":
        # length-matched to the canonical override payload for this seed, scored with its target
        text, target, _ = render_payload(base, "override", "plain")
        corp, meta = apply_placebo(base, spec.placement, len(text.split()))
        meta["target"] = target
        return corp, meta
    if fam == "poison":
        return apply_poison(base, spec.extra["fraction"])
    if fam == "probe_length":
        text, target = probe_length_ladder(base, spec.extra["n_words"])
        hid = host_id(base, spec.placement)
        return inject_text(base, hid, text), {"family": fam, "host_id": hid, "payload_text": text,
                                              "payload_words": len(text.split()), "target": target}
    if fam == "probe_misattr":
        text, target = probe_misattribution_ladder(base, spec.extra["variant"])
        hid = host_id(base, spec.placement)
        return inject_text(base, hid, text), {"family": fam, "host_id": hid, "payload_text": text,
                                              "payload_words": len(text.split()), "target": target, "variant": spec.extra["variant"]}
    if fam == "probe_elicitation":
        text, target = probe_elicitation(base)
        hid = host_id(base, spec.placement)
        return inject_text(base, hid, text), {"family": fam, "host_id": hid, "payload_text": text,
                                              "payload_words": len(text.split()), "target": target}
    return apply_payload(base, fam, spec.placement, spec.framing)


def make_defense(spec, classifiers):
    if spec.defense == "none":
        return None
    if spec.defense == "spotlight":
        return Spotlighting()
    if spec.defense == "monitor":
        return Monitor(classifier=classifiers[spec.backend], mode=os.environ.get("IPI_MONITOR_MODE", "cascade"))
    raise ValueError(spec.defense)


def existing_ids(path):
    ids = set()
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    ids.add(json.loads(line)["trial_id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return ids


def spent_so_far(raw_dir=RAW):
    total = 0.0
    for p in raw_dir.glob("*.jsonl"):
        for line in p.read_text().splitlines():
            if line.strip():
                try:
                    row = json.loads(line)
                    total += row["transcript"].get("cost_usd", 0) + row["transcript"].get("defense_cost_usd", 0)
                except (json.JSONDecodeError, KeyError):
                    pass
    return total


def run_specs(specs, out_path, backends=None, workers=config.WORKERS, budget_cap=config.BUDGET_CAP_USD, verbose=True):
    """Run every spec not already in out_path. Appends one JSON row per trial. Returns rows run."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = existing_ids(out_path)
    todo = [s for s in specs if s.trial_id not in done]
    if verbose:
        print("{}: {} specs, {} already done, {} to run".format(out_path.name, len(specs), len(specs) - len(todo), len(todo)), flush=True)
    if not todo:
        return []
    if backends is None:
        if os.environ.get("IPI_ALLOW_MOCK") == "1":
            backends = {k: MockBackend(key=k) for k in config.BACKENDS}
            classifiers = {k: None for k in config.BACKENDS}
        else:
            backends = {k: make_backend(k) for k in {s.backend for s in todo}}
            classifiers = {k: make_classifier(k) for k in {s.backend for s in todo if s.defense == "monitor"}}
    else:
        classifiers = {k: None for k in backends}
    lock = threading.Lock()
    spent = spent_so_far(out_path.parent)
    stop = {"flag": False}
    rows = []

    def one(spec):
        if stop["flag"]:
            return None
        corpus, meta = prepare_corpus(spec)
        be = backends[spec.backend]
        if isinstance(be, MockBackend):
            be.truth = corpus.truth
        defense = make_defense(spec, classifiers)
        tr = run_agent(be, corpus, defense)
        row = {"trial_id": spec.trial_id, "spec": asdict(spec), "payload": meta,
               "truth": corpus.truth, "decoys": corpus.decoys, "canary_system": corpus.canary_system,
               "canary_doc": corpus.canary_doc, "attacker_email": corpus.attacker_email,
               "doc_order": [d.id + ":" + d.kind for d in corpus.docs], "transcript": tr,
               "written_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        return row

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(one, s): s for s in todo}
        for fut in as_completed(futs):
            spec = futs[fut]
            try:
                row = fut.result()
            except Exception as e:
                print("  FAILED {}: {}: {}".format(spec.trial_id, type(e).__name__, e), flush=True)
                continue
            if row is None:
                continue
            with lock:
                with out_path.open("a") as f:
                    f.write(json.dumps(row) + "\n")
                spent += row["transcript"]["cost_usd"] + row["transcript"]["defense_cost_usd"]
                rows.append(row)
                if verbose:
                    print("  done {}  ${:.3f}  {}  cum ${:.2f}".format(row["trial_id"], row["transcript"]["cost_usd"],
                                                                        row["transcript"]["terminated"], spent), flush=True)
                if spent > budget_cap:
                    print("BUDGET CAP ${} EXCEEDED (spent ${:.2f}); not launching further trials.".format(budget_cap, spent), flush=True)
                    stop["flag"] = True
    return rows


def run_arm(arm, **kw):
    specs = build_arm(arm)
    out = RAW / ("clean.jsonl" if arm == "pilot" else arm + ".jsonl")
    return run_specs(specs, out, **kw)
