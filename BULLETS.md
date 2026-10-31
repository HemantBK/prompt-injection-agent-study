# Résumé bullet candidates

Each one factual sentence with a number produced by this repo; source table in brackets.

1. Built a two-backend (Claude Sonnet 5.5, GPT-6.1 Sol) indirect-prompt-injection benchmark for a
   document-reading agent with programmatic flip-from-clean labels, a zero-noise clean baseline
   (120/120, 0 self-disagreement) and a 5-point whole-pipeline reproducibility delta; all five
   instruction-style payload families scored 0/20 on both backends while forged log evidence with no
   instruction flipped 18/20 and 20/20 [RESULTS.md §1, §2, §5].

2. Tuned a regex→cross-family-LLM injection monitor on three payload families and evaluated it on
   three unseen ones: 100% flag precision, 0/40 clean-run false positives, intervention at step 2 of a
   4–6 step episode, but 67% held-out recall because it is blind to the only attack that worked
   [RESULTS.md §4a].

3. Showed that spotlighting (datamarking + "untrusted data" framing) cut forged-evidence acceptance
   from 20/20 to 9/20 on GPT-6.1 Sol (seed-paired McNemar p = 0.001, pre-registered test) at zero
   cost and zero clean false positives, by inducing the cross-document check the undefended agent
   skipped [RESULTS.md §4b; transcripts in results/raw/spot_test.jsonl].

Alternate (exploratory, must be labelled post-hoc if used): a single forged sign-in row appended to a
trusted log flipped the agent's conclusion in 20/20 trials on each backend while the exonerating
annotation alone flipped 0/20 [RESULTS.md §7c].
