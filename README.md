# ¿Merece la pena? · EuroLeague watchability

Spoiler-free 0–100 ratings for EuroLeague games, adapted from ReplayRank's method
(see `site/methodology.html` and `replayrank.txt`).

## Local use

```bash
python -m pipeline.build --season E2026      # download new finished games + score everything
python -m pipeline.calibrate --season E2026  # distribution, label shares, top/bottom games
python -m pytest -q
python -m http.server -d site 8000           # http://localhost:8000
```

- Weights and thresholds: `pipeline/config.py`. After changing them, just re-run `build`:
  scores are recomputed from the cached features in `data/features/` (nothing is re-downloaded).
  If you change the weights, update the numbers in `site/methodology.html` too.
- When the feature *extraction* changes (`pipeline/features.py`, `pipeline/pbp.py`), run with `--refetch`.
- The raw API JSON is cached in `.cache/` (gitignored).

## Deploy (GitHub Pages)

1. Create a repo on GitHub and push this folder to `main`.
2. Settings → Pages → Source: **GitHub Actions**.
3. Actions → "Update scores and deploy" → *Run workflow*. After that it runs every day at
   07:00 and 23:30 UTC, commits the new data and publishes `site/`.

New season: change `--season` in `.github/workflows/update.yml` (e.g. `E2027`).
The site always loads the most recent season listed in `site/data/seasons.json`.
