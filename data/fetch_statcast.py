"""
edgar/data/fetch_statcast.py
─────────────────────────────
Pulls Mariners Statcast leaderboard stats.
Filters by player_id matched against active Mariners roster.
"""

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, DATA_DIR, MARINERS_ABBREV, MARINERS_ID

import pybaseball
import statsapi
import pandas as pd

pybaseball.cache.enable()


def safe_round(val, decimals=3):
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return None


def get_mariners_mlbam_ids() -> set:
    """Return set of MLBAM player IDs on the active Mariners roster."""
    try:
        roster_raw = statsapi.get(
            "team_roster",
            {"teamId": MARINERS_ID, "rosterType": "active", "season": SEASON},
        )
        ids = {p["person"]["id"] for p in roster_raw.get("roster", [])}
        print(f"  ℹ️  {len(ids)} players on active Mariners roster")
        return ids
    except Exception as e:
        print(f"  ⚠️  Roster ID lookup failed: {e}")
        return set()


def fetch_statcast_batting(sea_ids: set) -> list:
    print("🔥 Fetching Statcast batting leaders...")
    try:
        df = pybaseball.statcast_batter_exitvelo_barrels(SEASON, minBBE=1)
    except Exception as e:
        print(f"  ⚠️  Statcast batting fetch failed: {e}")
        return []

    if df is None or df.empty:
        print("  ⚠️  No Statcast batting data yet")
        return []

    # Filter by player_id matching Mariners roster
    if sea_ids and "player_id" in df.columns:
        sea = df[df["player_id"].isin(sea_ids)].copy()
    else:
        print("  ⚠️  Could not filter by team — returning empty")
        return []

    if sea.empty:
        print("  ⚠️  No Mariners batters in Statcast data yet")
        return []

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
    for _, row in sea.iterrows():
        rec = {}
        for col in col_map.values():
            if col in row:
                val = row[col]
                rec[col] = safe_round(val) if isinstance(val, float) else val
        records.append(rec)

    print(f"  ✅ {len(records)} Mariners batters in Statcast")
    return records


def fetch_xba_delta(sea_ids: set) -> list:
    print("🎲 Fetching xBA vs BA delta...")
    try:
        df = pybaseball.statcast_batter_expected_stats(SEASON, minPA=1)
        if df is None or df.empty:
            return []

        # Filter by player_id
        if sea_ids and "player_id" in df.columns:
            sea = df[df["player_id"].isin(sea_ids)].copy()
        else:
            return []

        if sea.empty:
            print("  ⚠️  No Mariners in xBA data yet")
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

        print(f"  ✅ {len(records)} Mariners in xBA data")
        return records

    except Exception as e:
        print(f"  ⚠️  xBA fetch failed: {e}")
        return []


def fetch_sprint_speed(sea_ids: set) -> list:
    print("💨 Fetching sprint speed...")
    try:
        df = pybaseball.statcast_sprint_speed(SEASON, min_opp=1)
        if df is None or df.empty:
            return []

        # Try team column first, fall back to player_id
        team_col = next((c for c in ["team", "Team", "team_name"] if c in df.columns), None)
        if team_col:
            sea = df[df[team_col] == MARINERS_ABBREV].copy()
        elif sea_ids and "player_id" in df.columns:
            sea = df[df["player_id"].isin(sea_ids)].copy()
        else:
            return []

        if sea.empty:
            return []

        sea = sea.sort_values("sprint_speed", ascending=False)

        records = []
        for _, row in sea.iterrows():
            records.append({
                "name":          row.get("last_name, first_name", ""),
                "sprint_spd":    safe_round(row.get("sprint_speed")),
                "hp_to_1b":      safe_round(row.get("hp_to_1b")),
                "opportunities": int(row.get("competitive_runs", 0)),
            })

        print(f"  ✅ {len(records)} Mariners sprint speed entries")
        return records

    except Exception as e:
        print(f"  ⚠️  Sprint speed fetch failed: {e}")
        return []


def fetch_statcast_all():
    # Get Mariners roster IDs once — used for all filters
    sea_ids = get_mariners_mlbam_ids()

    batting = fetch_statcast_batting(sea_ids)
    xba     = fetch_xba_delta(sea_ids)
    sprint  = fetch_sprint_speed(sea_ids)

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
