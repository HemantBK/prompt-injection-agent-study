# Offline monitor evaluation  (mode=regex, seeds 0-19)

| classifier for | clean docs flagged (doc-level FPR) | cost |
|---|---|---|
| claude | 0/640 = 0% [0%, 1%] | $0.000 |

| family | split | classifier for | host doc flagged (recall) |
|---|---|---|---|
| tool_hijack | TEST | claude | 20/20 = 100% [84%, 100%] |
| exfiltration | TEST | claude | 20/20 = 100% [84%, 100%] |
| misattribution | TEST | claude | 0/20 = 0% [0%, 16%] |
