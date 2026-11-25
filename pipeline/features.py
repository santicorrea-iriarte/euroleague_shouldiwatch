"""Extract the raw facts the score is computed from (no weights here)."""
from __future__ import annotations

from . import config as C
from .pbp import SHOT_VALUE, Event


def _sign(x: int) -> int:
    return (x > 0) - (x < 0)


def lead_dynamics(events: list[Event], late_seconds: int = C.LATE_SECONDS) -> dict:
    """Lead changes, ties, late lead changes and the largest deficit for each side."""
    lead_changes = ties = late_lc = 0
    last_leader = 0  # last non-zero sign of (a - b)
    prev_diff = 0
    max_lead_a = max_lead_b = 0  # biggest lead A had over B, and vice versa
    for e in events:
        diff = e.a - e.b
        if diff == prev_diff:
            continue
        s = _sign(diff)
        if s == 0:
            ties += 1
        elif last_leader != 0 and s != last_leader:
            lead_changes += 1
            if e.period >= 4 and e.remaining <= late_seconds:
                late_lc += 1
        if s != 0:
            last_leader = s
        max_lead_a = max(max_lead_a, diff)
        max_lead_b = max(max_lead_b, -diff)
        prev_diff = diff
    return {
        "lead_changes": lead_changes,
        "ties": ties,
        "late_lead_changes": late_lc,
        "max_lead_a": max_lead_a,
        "max_lead_b": max_lead_b,
    }


def clutch(events: list[Event], window: int = C.CLUTCH_SECONDS) -> str | None:
    """Best clutch moment in the last `window` seconds of Q4 or any OT.

    Returns 'go_ahead' (made shot that turned a tie/deficit into a lead),
    'tie' (made shot that tied it) or 'missed' (missed shot that would have tied/won).
    """
    rank = {"go_ahead": 3, "tie": 2, "missed": 1}
    best = None
    for e in events:
        if e.period < 4 or e.remaining > window or not e.is_shot or e.side is None:
            continue
        v = SHOT_VALUE[e.play]
        own, opp = (e.a, e.b) if e.side == "A" else (e.b, e.a)
        if e.is_made:
            own -= v  # reconstruct the score right before the shot
        deficit = opp - own
        if deficit < 0 or v < deficit:
            continue  # shooter was ahead, or the shot could not tie
        if e.is_made:
            kind = "go_ahead" if v > deficit else "tie"
        else:
            kind = "missed"
        if best is None or rank[kind] > rank[best]:
            best = kind
    return best


def stars(box: dict | None) -> list[dict]:
    """Per-player lines that matter for star power."""
    out = []
    if not box:
        return out
    for team in box.get("Stats") or []:
        for p in team.get("PlayersStats") or []:
            pts = p.get("Points") or 0
            reb = p.get("TotalRebounds") or 0
            ast = p.get("Assistances") or 0
            pir = p.get("Valuation") or 0
            td = sum(x >= 10 for x in (pts, reb, ast, p.get("Steals") or 0, p.get("BlocksFavour") or 0)) >= 3
            if pts >= min(t for t, _ in C.STAR_TIERS) or pir >= C.STAR_PIR_MIN or td:
                out.append({
                    "name": _pretty(p.get("Player") or ""),
                    "team": (p.get("Team") or "").strip(),
                    "pts": pts, "reb": reb, "ast": ast, "pir": pir, "triple_double": td,
                })
    return out


def _pretty(name: str) -> str:
    """'LLULL, SERGIO' -> 'Sergio Llull'."""
    if "," in name:
        last, first = [s.strip() for s in name.split(",", 1)]
        name = f"{first} {last}"
    return " ".join(w.capitalize() if w.isupper() else w for w in name.split())


def extract(game: dict, events: list[Event] | None, box: dict | None) -> dict:
    """Everything the scorer needs for one game, JSON-serialisable."""
    home, away = game["local"], game["road"]
    hs, as_ = home["score"], away["score"]
    periods = 4 + len(home["partials"].get("extraPeriods") or {})
    f = {
        "margin": abs(hs - as_),
        "total_points": hs + as_,
        "periods": periods,
        "stars": stars(box),
        "has_pbp": bool(events),
    }
    if events:
        dyn = lead_dynamics(events)
        # PBP team A/B -> which one won? Use the final PBP score.
        last = events[-1]
        winner_is_a = last.a > last.b
        f.update({
            "lead_changes": dyn["lead_changes"],
            "ties": dyn["ties"],
            "late_lead_changes": dyn["late_lead_changes"],
            "winner_max_deficit": dyn["max_lead_b"] if winner_is_a else dyn["max_lead_a"],
            "clutch": clutch(events),
        })
    return f
