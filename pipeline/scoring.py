"""Pure scoring: features (+ context) -> score, uncapped, label, tags, breakdown.

Tags are language-neutral keys with params; the site translates them.
"""
from __future__ import annotations

from . import config as C


def score(f: dict, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    b: dict[str, float] = {}
    tags: list[dict] = []
    margin = f["margin"]

    # 1. Closeness base
    b["closeness"] = min(C.CLOSENESS_CAP, max(0, C.CLOSENESS_WINDOW - margin) * C.CLOSENESS_MULT)

    # 1b. Down to the wire
    b["wire"] = C.WIRE_BONUS if margin <= C.WIRE_MARGIN else 0
    if b["wire"]:
        tags.append({"k": "wire"})

    if f.get("has_pbp"):
        # 2. Lead changes & ties
        lc, ties = f["lead_changes"], f["ties"]
        b["lead_changes"] = min(C.LEAD_TIES_CAP, lc * C.LEAD_CHANGE_W + ties * C.TIE_W)
        if lc >= C.SEESAW_TAG_MIN_LC:
            tags.append({"k": "seesaw", "p": {"n": lc}})

        # 5. Clutch ending
        cl = f.get("clutch")
        b["clutch"] = {"go_ahead": C.CLUTCH_GO_AHEAD, "tie": C.CLUTCH_TIE, "missed": C.CLUTCH_MISSED}.get(cl, 0)
        if cl:
            tags.append({"k": f"clutch_{cl}"})

        # 7. Late drama
        late = f["late_lead_changes"]
        b["late_drama"] = (C.LATE_FIRST + (late - 1) * C.LATE_EXTRA) if late > 0 else 0
        if late:
            tags.append({"k": "late_drama", "p": {"n": late}})

        # 8. Comeback
        d = f["winner_max_deficit"]
        b["comeback"] = min(C.COMEBACK_CAP, (d - C.COMEBACK_MIN + 1) * C.COMEBACK_MULT) if d >= C.COMEBACK_MIN else 0
        if b["comeback"]:
            tags.append({"k": "comeback", "p": {"n": d}})

    # 3. Star power
    raw = 0.0
    for p in f.get("stars", []):
        raw += next((bonus for pts, bonus in C.STAR_TIERS if p["pts"] >= pts), 0)
        if p["pir"] >= C.STAR_PIR_MIN:
            raw += C.STAR_PIR_BONUS
        if p["triple_double"]:
            raw += C.TRIPLE_DOUBLE_BONUS
            tags.append({"k": "triple_double", "p": {"name": p["name"]}})
        elif p["pts"] >= C.STAR_TAG_MIN_PTS or p["pir"] >= C.STAR_TAG_MIN_PIR:
            tags.append({"k": "star", "p": {"name": p["name"], "pts": p["pts"], "pir": p["pir"]}})
    b["star_power"] = min(C.STAR_CAP, raw)

    # 4. Offensive flow
    total = f["total_points"]
    if total > C.SHOOTOUT_TOTAL:
        b["flow"] = C.SHOOTOUT_BONUS
        tags.append({"k": "shootout"})
    elif total < C.GRIND_TOTAL and margin > C.GRIND_MARGIN:
        b["flow"] = C.GRIND_PENALTY
        tags.append({"k": "grind"})
    else:
        b["flow"] = 0

    # 6. Overtime
    ot = max(0, f["periods"] - 4)
    b["overtime"] = C.OT_BONUS * ot
    if ot:
        tags.append({"k": "overtime", "p": {"n": ot}})

    # 9. Context
    ctxb = C.PHASE_BONUS.get(ctx.get("phase", ""), 0)
    if ctxb:
        tags.append({"k": "phase", "p": {"phase": ctx["phase"]}})
    if ctx.get("both_top"):
        ctxb += C.CONTEXT_TOP_BONUS
        tags.append({"k": "big_matchup"})
    b["context"] = ctxb

    uncapped = round(sum(b.values()), 1)
    final = int(round(min(100, max(0, uncapped))))
    label = next(name for thr, name in C.LABELS if final >= thr)
    return {
        "score": final,
        "uncapped": uncapped,
        "label": label,
        "tags": tags,
        "breakdown": {k: round(v, 1) for k, v in b.items()},
        "partial": not f.get("has_pbp"),
    }
