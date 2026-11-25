"""Build the site data: download new finished games, extract features, score all.

    python -m pipeline.build --season E2026            # incremental (daily)
    python -m pipeline.build --season E2026 --refetch  # re-download every game
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import api, config as C
from .features import extract
from .pbp import parse
from .scoring import score

ROOT = Path(__file__).resolve().parent.parent
FEATURES = ROOT / "data" / "features"
SITE_DATA = ROOT / "site" / "data"


def _utc(game: dict) -> datetime:
    return datetime.fromisoformat(game["utcDate"].replace("Z", "+00:00"))


def game_features(season: str, game: dict, refetch: bool) -> dict:
    code = game["gameCode"]
    path = FEATURES / season / f"{code}.json"
    if path.exists() and not refetch:
        return json.loads(path.read_text(encoding="utf-8"))
    raw = api.play_by_play(season, code, refetch)
    box = api.boxscore(season, code, refetch)
    events = parse(raw) if raw else None
    f = extract(game, events, box)
    # Cache only when complete, or when the PBP is clearly never coming
    if f["has_pbp"] or datetime.now(timezone.utc) - _utc(game) > timedelta(days=3):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
    return f


def standings_before(played: list[dict]) -> dict[int, list[str]]:
    """For each regular-season round r: club codes in the top N using only games from rounds < r."""
    rs = [g for g in played if g["phaseType"]["code"] == "RS"]
    rounds = sorted({g["round"] for g in rs})
    out = {}
    for r in rounds:
        wins, diff = defaultdict(int), defaultdict(int)
        for g in rs:
            if g["round"] >= r:
                continue
            h, a = g["local"], g["road"]
            hc, ac = h["club"]["code"], a["club"]["code"]
            d = h["score"] - a["score"]
            diff[hc] += d
            diff[ac] -= d
            wins[hc] += d > 0
            wins[ac] += d < 0
        table = sorted(wins, key=lambda c: (-wins[c], -diff[c]))
        out[r] = table[: C.CONTEXT_TOP_N]
    return out


def club(side: dict) -> dict:
    c = side["club"]
    return {"code": c["code"], "name": c.get("editorialName") or c["name"], "crest": (c.get("images") or {}).get("crest")}


def build(season: str, refetch: bool = False) -> dict:
    games = api.games(season)
    played = [g for g in games if g.get("played")]
    top = standings_before(played)
    out = []
    for g in sorted(played, key=lambda g: g["gameCode"]):
        f = game_features(season, g, refetch)
        phase = g["phaseType"]["code"]
        r = g["round"]
        ctx = {"phase": phase}
        if phase == "RS" and r >= C.CONTEXT_MIN_ROUND:
            t = top.get(r, [])
            ctx["both_top"] = g["local"]["club"]["code"] in t and g["road"]["club"]["code"] in t
        s = score(f, ctx)
        out.append({
            "id": g["identifier"],
            "code": g["gameCode"],
            "round": r,
            "phase": phase,
            "date": g["utcDate"],
            "home": club(g["local"]),
            "away": club(g["road"]),
            "result": [g["local"]["score"], g["road"]["score"]],
            **s,
        })
        print(f"{g['gameCode']:>4} R{r:<2} {g['local']['club']['code']}-{g['road']['club']['code']} "
              f"{s['score']:>3} ({s['uncapped']}) {s['label']}")
    data = {
        "season": season,
        "name": games[0]["season"]["name"] if games else season,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "games": out,
    }
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / f"games-{season}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    _update_index(season, data["name"])
    return data


def _update_index(season: str, name: str) -> None:
    path = SITE_DATA / "seasons.json"
    idx = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    idx = [s for s in idx if s["code"] != season] + [{"code": season, "name": name}]
    idx.sort(key=lambda s: s["code"], reverse=True)
    path.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="E2026")
    ap.add_argument("--refetch", action="store_true", help="re-download and re-extract every game")
    a = ap.parse_args()
    d = build(a.season, a.refetch)
    print(f"\n{len(d['games'])} games scored -> site/data/games-{a.season}.json")


if __name__ == "__main__":
    main()
