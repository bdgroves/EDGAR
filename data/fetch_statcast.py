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
from datetime import date

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


def fetch_statcast_batting() -> list:
    """Pull season-to-date Statcast batting leaders for the Mariners."""
    print("🔥 Fetching Statcast batting leaders...")

    try:
        df = pybaseball.statcast_batter_exitvelo_barrels(SEASON, minBBE=10)
    except Exception as e:
        print(f"  ⚠️  Statcast batting fetch failed: {e}")
        return []

    if df is None or df.empty:
        print("  ⚠️  No Statcast batting data yet (early season)")
        return []

    print(f"  ℹ️  Columns available: {list(df.columns)}")

    # Try multiple possible team column names — Savant changes these occasionally
    team_col = None
    for candidate in ["team_name", "team_name_alt", "team", "Team"]:
        if candidate in df.columns:
            team_col = candidate
            break

    if team_col is None:
        print(f"  ⚠️  No team column found. Returning all players (no team filter).")
        sea = df.copy()
    else:
        sea = df[df[team_col].str.contains("Seattle", case=False, na=False)].copy()

    if sea.empty:
        print("  ⚠️  No Mariners batters in Statcast data yet")
        return []

    # Rename whichever columns are present
    col_map = {
        "last_name, first_name": "name",
        "attempts":              "bbe",
        "avg_hit_speed":         "avg_ev",
        "max_hit_speed":         "max_ev",
        "barrel_batted_rate":    "barrel_pct",
        "brl":                   "barrels",
        "hard_hit_percent":      "hard_hit_pct",
        "avg_distance":          "avg_dist",
        "sweet_spot_percent":    "sweet_spot_pct",
        "avg_launch_angle":      "avg_la",
    }
    sea = sea.rename(columns={k: v for k, v in col_map.items() if k in sea.columns})

    records = []
    target_cols = set(col_map.values())
    for _, row in sea.iterrows():
        rec = {}
        for col in target_cols:
            if col in row:
                val = row[col]
                rec[col] = safe_round(val) if isinstance(val, float) else val
        records.append(rec)

    return records


def fetch_xba_delta() -> list:
    """Pull xBA vs actual BA — who's getting lucky or unlucky."""
    print("🎲 Fetching xBA vs BA delta...")

    try:
        df = pybaseball.statcast_batter_expected_stats(SEASON, minPA=20)
        if df is None or df.empty:
            return []

        # Flexible team column detection
        team_col = next((c for c in ["team_name", "team_name_alt", "team", "Team"]
                         if c in df.columns), None)
        if team_col:
            sea = df[df[team_col].str.contains("Seattle", case=False, na=False)].copy()
        else:
            sea = df.copy()

        if sea.empty:
            return []

        sea["ba_delta"] = sea["ba"] - sea["est_ba"]
        sea = sea.sort_values("ba_delta")

        records = []
        for _, row in sea.iterrows():
            records.append({
                "name":  row.get("last_name, first_name", ""),
                "ba":    safe_round(row.get("ba")),
                "xba":   safe_round(row.get("est_ba")),
                "delta": safe_round(row.get("ba_delta"), 3),
                "woba":  safe_round(row.get("woba")),
                "xwoba": safe_round(row.get("est_woba")),
                "pa":    int(row.get("pa", 0)),
            })
        return records

    except Exception as e:
        print(f"  ⚠️  xBA fetch failed: {e}")
        return []


def fetch_sprint_speed() -> list:
    """Pull sprint speed leaderboard filtered to Mariners."""
    print("💨 Fetching sprint speed...")

    try:
        df = pybaseball.statcast_sprint_speed(SEASON, min_opp=5)
        if df is None or df.empty:
            return []

        # Flexible team column
        team_col = next((c for c in ["team", "Team", "team_name"] if c in df.columns), None)
        if team_col:
            sea = df[df[team_col] == MARINERS_ABBREV].copy()
        else:
            sea = df.copy()

        if sea.empty:
            return []

        sea = sea.sort_values("sprint_speed", ascending=False)

        records = []
        for _, row in sea.iterrows():
            records.append({
                "name":         row.get("last_name, first_name", ""),
                "sprint_spd":   safe_round(row.get("sprint_speed")),
                "hp_to_1b":     safe_round(row.get("hp_to_1b")),
                "opportunities": int(row.get("competitive_runs", 0)),
            })
        return records

    except Exception as e:
        print(f"  ⚠️  Sprint speed fetch failed: {e}")
        return []


def fetch_statcast_all():
    batting = fetch_statcast_batting()
    xba     = fetch_xba_delta()
    sprint  = fetch_sprint_speed()

    output = {
        "updated":         date.today().isoformat(),
        "season":          SEASON,
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
