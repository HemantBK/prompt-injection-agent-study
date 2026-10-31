# Defense tuning log (Fork 4 discipline)

Rule: every change to defense/monitor.py (regexes, classifier prompt, cascade mode, threshold)
is logged here with the TRAIN-family or clean-corpus evidence that motivated it. No entry may
cite a test-family payload. Test-family offline checks (`scripts/monitor_offline.py --families test`)
run only after the entry "TUNING FROZEN".

| date | change | motivated by | evidence |
|---|---|---|---|
| 2026-10-31 | initial 8 regexes written from override / refusal / delimiter_escape wording and generic injection cues | train payloads, seeds 0–4 | tests/test_monitor.py: all train hosts hit; 0 hits on 320 clean docs (seeds 0–9) |
| 2026-10-31 | classifier prompt v1 (generic: addresses an AI reader, ignore-previous, fake system/user/tool messages, superseded instructions) | generic | — |
| 2026-10-31 | mode = cascade (regex gate), threshold 0.5 | StepShield arc; cost | to be checked on tune seeds 100–109 |
| 2026-10-31 | **TUNING FROZEN** before any defended arm ran. Canonical undefended results for all six families (including the three TEST families) have now been seen; no further change to regexes, prompt, mode or threshold is permitted. Mode stays `cascade`, threshold 0.5. | discipline | results/raw/canonical.jsonl `written_at` timestamps precede every defended_* row |
| 2026-10-31 | **Freeze evidence recorded.** defense/monitor.py last modified 18:03:11 (before the pilot); first canonical row written 18:29:49; FROZEN entry written 18:54:09; first tune_monitor row 18:55:30; first defended_test row 18:59:06; first defended_train row 19:06:15; first spot_test row 19:15:04. Frozen sha256 of defense/monitor.py: `c3dde85eaf2e6490e7c26fe8f055671645ca3dd8aa72b67bd978e83e6533199f`. tests/test_monitor.py::test_monitor_source_unchanged_since_freeze fails `make verify` if the file ever changes. | discipline | `shasum -a 256 defense/monitor.py`; `grep -ho '"written_at": "[^"]*"' results/raw/defended_test.jsonl | sort | head -1` |
