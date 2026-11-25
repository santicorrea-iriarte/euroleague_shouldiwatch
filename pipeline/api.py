"""Thin client for the public Euroleague APIs with an on-disk cache of raw JSON."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
UA = "euroleague-watchability/0.1 (static site generator)"
GAMES_URL = "https://api-live.euroleague.net/v2/competitions/{comp}/seasons/{season}/games"
PBP_URL = "https://live.euroleague.net/api/PlayByPlay?gamecode={code}&seasoncode={season}"
BOX_URL = "https://live.euroleague.net/api/Boxscore?gamecode={code}&seasoncode={season}"

_last_call = 0.0


def _get(url: str, retries: int = 4) -> dict:
    global _last_call
    for attempt in range(retries):
        wait = 0.5 - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == retries - 1:
                raise RuntimeError(f"GET {url} failed: {e}") from e
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def games(season: str, comp: str = "E") -> list[dict]:
    """Full schedule of a season (always fetched fresh)."""
    data = _get(GAMES_URL.format(comp=comp, season=season))
    path = CACHE / season / "games.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data["data"]


def _cached(season: str, code: int, name: str, url: str, refetch: bool) -> dict | None:
    path = CACHE / season / str(code) / f"{name}.json"
    if path.exists() and not refetch:
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        data = _get(url)
    except RuntimeError:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def play_by_play(season: str, code: int, refetch: bool = False) -> dict | None:
    return _cached(season, code, "pbp", PBP_URL.format(code=code, season=season), refetch)


def boxscore(season: str, code: int, refetch: bool = False) -> dict | None:
    return _cached(season, code, "boxscore", BOX_URL.format(code=code, season=season), refetch)
