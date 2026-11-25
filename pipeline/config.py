"""All tunable weights and thresholds of the watchability score.

Change values here and re-run `python -m pipeline.build` (no re-download needed:
features are cached, scores are recomputed from them every build).
"""

# 1. Closeness base: min(CAP, max(0, WINDOW - margin) * MULT)
CLOSENESS_WINDOW = 25
CLOSENESS_MULT = 1.6
CLOSENESS_CAP = 40

# 1b. Down to the wire
WIRE_MARGIN = 5
WIRE_BONUS = 5

# 2. Lead changes & ties
LEAD_CHANGE_W = 1.5
TIE_W = 1.0
LEAD_TIES_CAP = 20
SEESAW_TAG_MIN_LC = 10  # tag "seesaw" from this many lead changes

# 3. Star power (per player, accumulated, then capped)
STAR_TIERS = [(40, 20), (30, 10), (25, 3)]  # (min points, bonus) - only the highest tier applies
STAR_PIR_MIN = 35
STAR_PIR_BONUS = 5
TRIPLE_DOUBLE_BONUS = 15
STAR_CAP = 20
STAR_TAG_MIN_PTS = 30  # tag a named performance from here
STAR_TAG_MIN_PIR = 35

# 4. Offensive flow
SHOOTOUT_TOTAL = 190
SHOOTOUT_BONUS = 5
GRIND_TOTAL = 140
GRIND_MARGIN = 10
GRIND_PENALTY = -5

# 5. Clutch ending (last N seconds of Q4 / any OT)
CLUTCH_SECONDS = 24
CLUTCH_GO_AHEAD = 20
CLUTCH_TIE = 15
CLUTCH_MISSED = 10

# 6. Overtime
OT_BONUS = 15

# 7. Late drama (lead changes in last N seconds of Q4 / any OT)
LATE_SECONDS = 120
LATE_FIRST = 8
LATE_EXTRA = 4

# 8. Comeback (largest deficit overcome by the winner)
COMEBACK_MIN = 10
COMEBACK_MULT = 1.5
COMEBACK_CAP = 15

# 9. Context
CONTEXT_TOP_N = 8
CONTEXT_TOP_BONUS = 5
CONTEXT_MIN_ROUND = 5          # standings are noise before this round
PHASE_BONUS = {"PI": 10, "PO": 10, "FF": 15}

# Labels (applied on the clamped 0-100 score).
# Calibrated on E2026 rounds 1-14: ~15% top, 16% watch, 34% maybe, 35% skip.
# Weights above were lowered vs. ReplayRank because Euroleague has many close games
# (35% decided by <=5) and stacking clutch+late+wire clamped too many games at 100.
LABELS = [(85, "top"), (60, "watch"), (30, "maybe"), (0, "skip")]
