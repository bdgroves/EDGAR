"""
edgar/data/fetch_pitchers.py
─────────────────────────────
Pulls Mariners starting & bullpen pitcher stats:
  - Standard: ERA, WHIP, K/9, BB/9, IP
  - Advanced: FIP, xFIP, WAR, CSW%, Stuff+, SwStr%
  - Pitch mix breakdown per starter (% usage by pitch type)

Outputs: data/cache/pitchers.json
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


def safe(val, decimals=2):
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return None


def fetch_fangraphs_pitching() -> list[dict]:
    """Season-level FanGraphs pitching stats for Mariners starters + relievers."""
    print("⚾ Fetching FanGraphs pitching stats...")

    try:
        df = pybaseball.pitching_stats(SEASON, SEASON, qual=1)
    except Exception as e:
        print(f"  ⚠️  FanGraphs pitch fetch failed: {e}")
        return []

    sea = df[df["Team"] == "SEA"].copy()
    if sea.empty:
        return []

    want = [
        "Name", "G", "GS", "IP", "W", "L", "SV",
        "ERA", "FIP", "xFIP", "WHIP",
        "K/9", "BB/9", "K%", "BB%", "K-BB%",
        "SwStr%", "CSW%",
        "WAR", "Age",
    ]
    available = [c for c in want if c in df.columns]
    sea = sea[available].copy()

    # Tag role
    sea["role"] = sea["GS"].apply(lambda gs: "SP" if gs >= 1 else "RP")
    sea = sea.sort_values(["role", "IP"], ascending=[True, False])

    records = []
    for _, row in sea.iterrows():
        rec = {col: safe(row[col]) if col not in ("Name", "role") else row[col]
               for col in sea.columns}
        records.append(rec)

    return records


def fetch_pitch_mix(starters: list[dict]) -> dict[str, list]:
    """
    For each Mariners starter, pull pitch type usage % from Statcast.
    Returns dict keyed by player name.
    """
    print("🎯 Fetching pitch mix for starters...")

    pitch_mix = {}

    # Get Mariners roster to find MLBAM IDs
    try:
        roster = statsapi.roster(MARINERS_ID, rosterType="40Man")
    except Exception as e:
        print(f"  ⚠️  Roster fetch failed: {e}")
        return pitch_mix

    starter_names = {r["Name"] for r in starters if r.get("role") == "SP"}

    for line in roster.split("\n"):
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        # Rough name match — statsapi roster lines: "#  POS  Full Name"
        name = " ".join(parts[2:])
        if name not in starter_names:
            continue

        try:
            ids = pybaseball.playerid_lookup(
                name.split()[-1], name.split()[0]
            )
            if ids.empty:
                continue
            mlbam_id = int(ids.iloc[0]["key_mlbam"])

            # Current season pitch data (start of season to today)
            season_start = f"{SEASON}-03-20"
            season_end   = date.today().isoformat()

            pdf = pybaseball.statcast_pitcher(season_start, season_end, mlbam_id)
            if pdf.empty:
                continue

            mix = (
                pdf.groupby("pitch_type")
                .size()
                .reset_index(name="count")
            )
            mix["pct"] = (mix["count"] / mix["count"].sum() * 100).round(1)

            # Avg velo per pitch
            velo = pdf.groupby("pitch_type")["release_speed"].mean().round(1)
            mix["avg_velo"] = mix["pitch_type"].map(velo)

            pitch_mix[name] = mix.to_dict("records")

        except Exception as e:
            print(f"    ⚠️  Pitch mix failed for {name}: {e}")
            continue

    return pitch_mix


def fetch_pitchers_all():
    fangraphs = fetch_fangraphs_pitching()
    starters  = [p for p in fangraphs if p.get("role") == "SP"]
    pitch_mix = fetch_pitch_mix(starters)

    output = {
        "updated":   date.today().isoformat(),
        "season":    SEASON,
        "pitchers":  fangraphs,
        "pitch_mix": pitch_mix,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "pitchers.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✅ Saved → {out_path}")
    return output


if __name__ == "__main__":
    fetch_pitchers_all()
