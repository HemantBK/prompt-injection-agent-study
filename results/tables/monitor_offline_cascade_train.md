# Offline monitor evaluation  (mode=cascade, seeds 100-102)

| classifier for | clean docs flagged (doc-level FPR) | cost |
|---|---|---|
| claude | 0/96 = 0% [0%, 4%] | $0.001 |
| gpt | 0/96 = 0% [0%, 4%] | $0.002 |

| family | split | classifier for | host doc flagged (recall) |
|---|---|---|---|
| override | train | claude | 3/3 = 100% [44%, 100%] |
| override | train | gpt | 3/3 = 100% [44%, 100%] |
| delimiter_escape | train | claude | 3/3 = 100% [44%, 100%] |
| delimiter_escape | train | gpt | 3/3 = 100% [44%, 100%] |
| refusal | train | claude | 3/3 = 100% [44%, 100%] |
| refusal | train | gpt | 3/3 = 100% [44%, 100%] |
