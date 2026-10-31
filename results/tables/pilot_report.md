# Pilot report (clean task, seeds 0-9, rep 1)

| backend | runs | mean $/run | max $/run | mean steps | mean in-tokens | mean out-tokens | exact-set correct | mean wall s |
|---|---|---|---|---|---|---|---|---|
| claude | 10 | $0.0372 | $0.0442 | 3.0 | 11767 | 1536 | 10/10 | 14 |
| gpt | 10 | $0.0355 | $0.0420 | 5.3 | 19236 | 809 | 10/10 | 20 |

Pre-pilot estimate: $0.20/run. Measured mean: $0.0363/run (0.18x estimate).
Full matrix: 1620 agent runs -> projected $59 (+ monitor classifier calls, small; defended runs cost slightly more because withheld docs change the trajectory).
Fork 5 rule: cut only if measured > 2x estimate ($0.40). NO CUT NEEDED.
