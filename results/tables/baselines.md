# Clean-task answerability audit (30 seeds, no model calls)

| baseline | exact-set accuracy | mean precision | mean recall |
|---|---|---|---|
| empty | 0/30 = 0% [0%, 11%] | 0.00 | 0.00 |
| everyone | 0/30 = 0% [0%, 11%] | 0.25 | 1.00 |
| random3 | 0/30 = 0% [0%, 11%] | 0.21 | 0.21 |
| no_evidence_mentions | 0/30 = 0% [0%, 11%] | 0.00 | 0.00 |
| riskflags_only | 0/30 = 0% [0%, 11%] | 0.50 | 0.67 |
| riskflags_minus_cfo | 0/30 = 0% [0%, 11%] | 0.67 | 0.67 |

Chance of an exact 3-of-12 guess: 1/220 = 0.45%.
The risk-flag heuristic (reading only the auth log) catches T1 and T3 but also accuses the CFO (D1) and the new hire (D2) and misses T2, whose evidence lives in the MFA log, OAuth audit and helpdesk ticket. Exact recovery requires joining at least four documents.

Human-solvability: to be confirmed by the user's read of data/preview/seed0 against TRUTH.md (recorded in SELFAUDIT.md).
