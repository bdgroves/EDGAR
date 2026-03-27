"""
edgar/data/fetch_statcast.py
─────────────────────────────
Pulls Mariners Statcast leaderboard stats.
Filters by player_id matched against active Mariners roster.
NaN values are replaced with None at every level so the
output JSON is always valid and the dashboard loads cleanly.
"""

import json
import math
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, DATA_DIR, MARINERS_ABBREV, MARINERS_ID

import pybaseball
import statsapi
import pandas as pd

pybaseball.cache.enable()


# ── NaN-safe helpers ──────────────────────────────────────────────

def clean(val, decimals=None):
    """Convert any value to a JSON-safe Python type. NaN/Inf → None."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        if decimals is not None:
            return round(f, decimals)
        return f
    except (TypeError, ValueError):
        return val


def clean_int(val):
    """Convert to int safely, return None if not possible."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def sanitize(obj):
    """
    Recursively walk a dict/list and replace any float NaN/Inf
    with None. Guarantees the output is valid JSON.
    """
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


# ── Roster lookup ─────────────────────────────────────────────────

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


# ── Fetchers ──────────────────────────────────────────────────────

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
                if col in ("name",):
                    rec[col] = val
                elif col in ("bbe", "barrels"):
                    rec[col] = clean_int(val)
                else:
                    rec[col] = clean(val, decimals=3)
        records.append(rec)

    print(f"  ✅ {len(records)} Mariners batters in Statcast")
    return records


def fetch_xba_delta(sea_ids: set) -> list:
    print("🎲 Fetching xBA vs BA delta...")
    try:
        df = pybaseball.statcast_batter_expected_stats(SEASON, minPA=1)
        if df is None or df.empty:
            return []

        if sea_ids and "player_id" in df.columns:
            sea = df[df["player_id"].isin(sea_ids)].copy()
        else:
            return []

        if sea.empty:
            print("  ⚠️  No Mariners in xBA data yet")
            return []

        # Compute delta safely — fillna so subtraction doesn't produce NaN
        sea = sea.copy()
        sea["ba_delta"] = sea["ba"].fillna(0) - sea["est_ba"].fillna(0)
        sea = sea.sort_values("ba_delta")

        records = []
        for _, row in sea.iterrows():
            records.append({
                "name":  row.get("last_name, first_name", ""),
                "ba":    clean(row.get("ba"),      decimals=3),
                "xba":   clean(row.get("est_ba"),  decimals=3),
                "delta": clean(row.get("ba_delta"), decimals=3),
                "woba":  clean(row.get("woba"),    decimals=3),
                "xwoba": clean(row.get("est_woba"), decimals=3),
                "pa":    clean_int(row.get("pa")) or 0,
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
                "sprint_spd":    clean(row.get("sprint_speed"), decimals=1),
                "hp_to_1b":      clean(row.get("hp_to_1b"),    decimals=2),
                "opportunities": clean_int(row.get("competitive_runs")) or 0,
            })

        print(f"  ✅ {len(records)} Mariners sprint speed entries")
        return records

    except Exception as e:
        print(f"  ⚠️  Sprint speed fetch failed: {e}")
        return []


# ── Main ──────────────────────────────────────────────────────────

def fetch_statcast_all():
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

    # Final safety net — walk entire output and kill any remaining NaN/Inf
    output = sanitize(output)

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "statcast.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    # Verify no NaN made it through
    raw = open(out_path).read()
    if "NaN" in raw or "Infinity" in raw:
        print("  ⚠️  WARNING: NaN/Infinity still in output!")
    else:
        print("  ✅ JSON validated — no NaN values")

    print(f"  ✅ Saved → {out_path}")
    return output


if __name__ == "__main__":
    fetch_statcast_all()
