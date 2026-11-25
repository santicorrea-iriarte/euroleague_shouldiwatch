"""Turn the raw Euroleague PlayByPlay JSON into a clean, ordered event list.

Each event: period (1-4 regulation, 5+ OT), remaining seconds in the period,
team side ('A'/'B'/None), play type, and the running score (a, b) *after* the event.
"""
from __future__ import annotations

from dataclasses import dataclass

QUARTERS = ["FirstQuarter", "SecondQuarter", "ThirdQuarter", "ForthQuarter"]
SHOT_VALUE = {"2FGM": 2, "2FGA": 2, "3FGM": 3, "3FGA": 3, "FTM": 1, "FTA": 1}
MADE = {"2FGM", "3FGM", "FTM"}


@dataclass
class Event:
    period: int
    remaining: int  # seconds left in the period
    side: str | None  # 'A' or 'B'
    play: str
    a: int  # score of team A after the event
    b: int  # score of team B after the event

    @property
    def is_shot(self) -> bool:
        return self.play in SHOT_VALUE

    @property
    def is_made(self) -> bool:
        return self.play in MADE


def _clock(s: str | None) -> int | None:
    if not s or ":" not in s:
        return None
    m, sec = s.strip().split(":")
    return int(m) * 60 + int(sec)


def _period_of(minute: int | None, default: int) -> int:
    """OT events come in one flat list; MINUTE 41-45 -> OT1 (5), 46-50 -> OT2 (6)..."""
    if minute is None or minute <= 40:
        return default
    return 5 + (minute - 41) // 5


def parse(raw: dict) -> list[Event]:
    code_a = (raw.get("CodeTeamA") or "").strip()
    code_b = (raw.get("CodeTeamB") or "").strip()
    blocks = [(i + 1, raw.get(q) or []) for i, q in enumerate(QUARTERS)]
    blocks.append((5, raw.get("ExtraTime") or []))

    events: list[Event] = []
    a = b = 0
    for default_period, block in blocks:
        last_clock: dict[int, int] = {}
        for e in sorted(block, key=lambda x: x.get("NUMBEROFPLAY") or 0):
            play = (e.get("PLAYTYPE") or "").strip()
            if play in ("EP", "EG"):
                continue  # End markers carry the next period's minute; ignore
            period = _period_of(e.get("MINUTE"), default_period) if default_period == 5 else default_period
            plen = 600 if period <= 4 else 300
            clk = _clock(e.get("MARKERTIME"))
            if clk is None:
                clk = last_clock.get(period, plen)
            last_clock[period] = clk
            team = (e.get("CODETEAM") or "").strip()
            side = "A" if team and team == code_a else "B" if team and team == code_b else None
            if e.get("POINTS_A") is not None and e.get("POINTS_B") is not None:
                a, b = int(e["POINTS_A"]), int(e["POINTS_B"])
            events.append(Event(period, clk, side, play, a, b))
    return events
