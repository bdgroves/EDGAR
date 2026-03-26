"""
edgar/data/fetch_statcast.py
─────────────────────────────
Pulls Mariners Statcast leaderboard stats:
  - Barrels & barrel %
  - Exit velocity (max + avg hard hit)
  - Sprint speed
  - xBA vs BA ("lucky/unlucky" delta)
  - Sweet spot %

Outputs: data/cache/statcast.json
"""

import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, DATA_DIR, MARINERS_ABBREV

import pybaseball
import pandas as pd

pybaseball.cache.enable()


def safe_round(val, decimals=3):
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return None


def fetch_statcast_batting() -> list[dict]:
    """Pull season-to-date Statcast batting leaders for the Mariners."""

    print("🔥 Fetching Statcast batting leaders...")

    # Season-level Statcast batting (Baseball Savant)
    df = pybaseball.statcast_batter_exitvelo_barrels(SEASON, minBBE=10)

    # Filter to Mariners
    sea = df[df["team_name"] == "Seattle Mariners"].copy()

    if sea.empty:
        print("  ⚠️  No Mariners Statcast batting data yet (season may be early)")
        return []

    sea = sea.sort_values("barrel_batted_rate", ascending=False)

    cols = {
        "last_name, first_name": "name",
        "attempts":              "bbe",        # batted ball events
        "avg_hit_speed":         "avg_ev",
        "max_hit_speed":         "max_ev",
        "barrel_batted_rate":    "barrel_pct",
        "brl":                   "barrels",
        "hard_hit_percent":      "hard_hit_pct",
        "avg_distance":          "avg_dist",
        "sweet_spot_percent":    "sweet_spot_pct",
        "avg_launch_angle":      "avg_la",
    }
    sea = sea.rename(columns={k: v for k, v in cols.items() if k in sea.columns})

    records = []
    for _, row in sea.iterrows():
        records.append({k: safe_round(v) if isinstance(v, float) else v
                        for k, v in row.items()
                        if k in cols.values()})
    return records


def fetch_xba_delta() -> list[dict]:
    """Pull xBA vs actual BA — who's getting lucky or unlucky."""

    print("🎲 Fetching xBA vs BA delta...")

    try:
        df = pybaseball.statcast_batter_expected_stats(SEASON, minPA=20)
        sea = df[df["team_name"] == "Seattle Mariners"].copy()
        if sea.empty:
            return []

        sea["ba_delta"] = sea["ba"] - sea["est_ba"]   # positive = lucky
        sea = sea.sort_values("ba_delta")

        records = []
        for _, row in sea.iterrows():
            records.append({
                "name":      row.get("last_name, first_name", ""),
                "ba":        safe_round(row.get("ba")),
                "xba":       safe_round(row.get("est_ba")),
                "delta":     safe_round(row.get("ba_delta"), 3),
                "woba":      safe_round(row.get("woba")),
                "xwoba":     safe_round(row.get("est_woba")),
                "pa":        int(row.get("pa", 0)),
            })
        return records
    except Exception as e:
        print(f"  ⚠️  xBA fetch failed: {e}")
        return []


def fetch_sprint_speed() -> list[dict]:
    """Pull sprint speed leaderboard filtered to Mariners."""

    print("💨 Fetching sprint speed...")

    try:
        df = pybaseball.statcast_sprint_speed(SEASON, min_opp=5)
        sea = df[df["team"] == MARINERS_ABBREV].copy()
        if sea.empty:
            return []

        sea = sea.sort_values("hp_to_1b")  # fastest home-to-first

        records = []
        for _, row in sea.iterrows():
            records.append({
                "name":       row.get("last_name, first_name", ""),
                "sprint_spd": safe_round(row.get("sprint_speed")),
                "hp_to_1b":   safe_round(row.get("hp_to_1b")),
                "opportunities": int(row.get("competitive_runs", 0)),
            })
        return records
    except Exception as e:
        print(f"  ⚠️  Sprint speed fetch failed: {e}")
        return []


def fetch_statcast_all():
    batting    = fetch_statcast_batting()
    xba        = fetch_xba_delta()
    sprint     = fetch_sprint_speed()

    output = {
        "updated":  date.today().isoformat(),
        "season":   SEASON,
        "batting_leaders": batting,
        "xba_delta":       xba,
        "sprint_speed":    sprint,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "statcast.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✅ Saved → {out_path}")
    return output


if __name__ == "__main__":
    fetch_statcast_all()
