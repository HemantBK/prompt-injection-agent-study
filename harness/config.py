"""Study configuration. Every number that shapes the experiment lives here (Fork 5)."""
import os

EFFORT = "medium"                 # matched across backends (DECISIONS.md, backends)
MAX_STEPS = 16                    # agent loop cap
WORKERS = int(os.environ.get("IPI_WORKERS", "6"))
BUDGET_CAP_USD = float(os.environ.get("IPI_BUDGET_CAP", "450"))   # hard stop for the whole study

# Backends under attack (Option B). Prices are USD per 1M tokens.
# OpenAI cached-input price for gpt-6.1-sol is not published in a source I could verify;
# 0.5x input is a deliberately conservative ASSUMPTION (over-estimates cost).
BACKENDS = {
    "claude": {"provider": "anthropic", "model": "claude-sonnet-5-5",
               "price": {"in": 2.00, "out": 10.00, "cache_read": 0.20, "cache_write_mult": 1.25}},
    "gpt":    {"provider": "openai", "model": "gpt-6.1-sol",
               "price": {"in": 2.00, "out": 10.00, "cached_in": 1.00}},
}
# Monitor classifier is cross-family: never the attacked model's family.
MONITOR_CLASSIFIER = {
    "claude": {"provider": "openai", "model": "gpt-6-luna", "price": {"in": 0.10, "out": 0.50, "cached_in": 0.05}},
    "gpt":    {"provider": "anthropic", "model": "claude-haiku-5-5", "price": {"in": 0.10, "out": 0.50, "cache_read": 0.01, "cache_write_mult": 1.25}},
}
EST_COST_PER_RUN = 0.20          # pre-pilot estimate; the pilot replaces it with a measurement

FAMILIES = ["override", "tool_hijack", "exfiltration", "misattribution", "refusal", "delimiter_escape"]
TRAIN_FAMILIES = ["override", "delimiter_escape", "refusal"]      # defense tuned here only (Fork 4)
TEST_FAMILIES = ["tool_hijack", "exfiltration", "misattribution"]  # all headline defense numbers
assert sorted(TRAIN_FAMILIES + TEST_FAMILIES) == sorted(FAMILIES)

PLACEMENTS = ["evidence", "peripheral"]
FRAMINGS = ["plain", "authority", "format_mimic"]
CANONICAL = {"placement": "evidence", "framing": "plain"}
SWEEP_VARIANTS = [{"placement": "evidence", "framing": "authority"},
                  {"placement": "evidence", "framing": "format_mimic"},
                  {"placement": "peripheral", "framing": "plain"}]

# Seeds are fixed and listed. No seed is dropped without a logged reason (results/CUT_CELLS.md).
CLEAN_SEEDS = list(range(0, 30))      # clean control, 2 reps each
ATTACK_SEEDS = list(range(0, 20))     # N=20 per cell, one trial per seed, paired across conditions
SWEEP_SEEDS = list(range(0, 10))
TUNE_SEEDS = list(range(100, 110))    # defense tuning uses seeds disjoint from evaluation seeds
POISON_SEEDS = list(range(0, 10))
POISON_FRACTIONS = [0.05, 0.10, 0.20, 0.40]   # 0.0 is the clean control
PROBE_LENGTHS = [40, 20, 10, 5, 2]
N_CLEAN_REPS = 2
