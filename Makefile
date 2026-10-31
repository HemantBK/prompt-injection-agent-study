PY=python3
export PYTHONPATH=.

.PHONY: help verify matrix preview split baselines pilot pilot-report reproduce tables monitor-offline lint

help:              ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*##/\t/' | expand -t 20

lint:              ## pyflakes over all python
	$(PY) -m pyflakes harness data attacks defense scripts tests

verify:            ## run every fixture test; PASS/FAIL per trust layer
	$(PY) -m scripts.verify

matrix:            ## print the trial matrix and run counts
	$(PY) -c "from harness.runner import build_arm, ALL_ARMS; t=0\nfor a in ALL_ARMS:\n n=len(build_arm(a)); t+=n; print(f'{a:<18}{n:>5}')\nprint('TOTAL', t)"

preview:           ## dump seed-0 corpus for human review -> data/preview/seed0/
	$(PY) -m scripts.preview_corpus 0

split:             ## train vs test payloads side by side -> results/tables/split_review.md
	$(PY) -m scripts.show_split 0

baselines:         ## answerability audit of the clean task (no model calls)
	$(PY) -m scripts.baselines

pilot:             ## 10 clean runs per backend (PAID, ~$4) then report measured $/run
	$(PY) -m scripts.run_arm pilot
	$(PY) -m scripts.pilot_report

pilot-report:
	$(PY) -m scripts.pilot_report

monitor-offline:   ## offline monitor FPR/recall on TRAIN families (cheap classifier calls)
	$(PY) -m scripts.monitor_offline --families train --seeds 100-109

tables:            ## recompute every table from results/raw
	$(PY) -m scripts.make_tables

# Full study. Resumable: completed trials are skipped. Order matters for the budget cut rule.
reproduce: verify baselines split
	$(PY) -m scripts.run_arm clean
	$(PY) -m scripts.pilot_report
	$(PY) -m scripts.run_arm placebo
	$(PY) -m scripts.run_arm canonical
	$(PY) -m scripts.run_arm tune_clean
	$(PY) -m scripts.run_arm tune_monitor
	$(PY) -m scripts.run_arm defended_test
	$(PY) -m scripts.run_arm defended_train
	$(PY) -m scripts.run_arm defended_clean
	$(PY) -m scripts.run_arm spot_test
	$(PY) -m scripts.run_arm spot_clean
	$(PY) -m scripts.run_arm sweep
	$(PY) -m scripts.run_arm canonical_rep2
	$(PY) -m scripts.run_arm poison
	$(PY) -m scripts.run_arm probe_length
	$(PY) -m scripts.run_arm probe_elicitation
	$(PY) -m scripts.make_tables
	$(PY) -m scripts.verify
