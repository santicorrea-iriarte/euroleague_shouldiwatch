"""Tuning aid: score distribution, label shares, top/bottom games and component averages.

    python -m pipeline.calibrate --season E2026
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="E2026")
    ap.add_argument("-n", type=int, default=10)
    a = ap.parse_args()
    games = json.loads((ROOT / "site" / "data" / f"games-{a.season}.json").read_text(encoding="utf-8"))["games"]
    n = len(games)
    print(f"{n} games\n\nHistogram (score buckets of 10):")
    hist = Counter(min(9, g["score"] // 10) for g in games)
    for b in range(10):
        print(f"  {b*10:>3}-{b*10+9:<3} {'#' * hist[b]} {hist[b]}")
    print("\nLabels:")
    for lab, c in Counter(g["label"] for g in games).most_common():
        print(f"  {lab:<6} {c:>4}  {100*c/n:5.1f}%")
    print("\nMean contribution per component:")
    keys = sorted({k for g in games for k in g["breakdown"]})
    for k in keys:
        vals = [g["breakdown"].get(k, 0) for g in games]
        print(f"  {k:<13} {sum(vals)/n:6.2f}  (non-zero in {sum(v != 0 for v in vals)})")

    def line(g):
        return (f"  {g['uncapped']:>6} R{g['round']:<2} {g['home']['name']} {g['result'][0]}-{g['result'][1]} "
                f"{g['away']['name']}  [{', '.join(t['k'] for t in g['tags'])}]")

    ranked = sorted(games, key=lambda g: g["uncapped"], reverse=True)
    print(f"\nTop {a.n}:")
    for g in ranked[: a.n]:
        print(line(g))
    print(f"\nBottom {a.n}:")
    for g in ranked[-a.n:]:
        print(line(g))


if __name__ == "__main__":
    main()
