"""
edgar/data/fetch_standings.py
─────────────────────────────
Pulls AL West standings + wild card picture via MLB StatsAPI.
Outputs: data/cache/standings.json
"""

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, DATA_DIR

import statsapi


def fetch_standings() -> dict:
    print("📊 Fetching standings...")

    raw = statsapi.standings_data(leagueId="103", season=SEASON)

    al_west_data  = []
    wildcard_data = []

    for div_id, div in raw.items():
        for team in div["teams"]:
            record = {
                "team":     team["name"],
                "abbrev":   team.get("abbreviation", ""),
                "w":        team["w"],
                "l":        team["l"],
                "pct":      round(team["w"] / max(team["w"] + team["l"], 1), 3),
                "gb":       team.get("gb", "-"),
                "streak":   team.get("streak", ""),
                "l10":      team.get("lastTen", ""),
                "rs":       team.get("runsScored", 0),
                "ra":       team.get("runsAllowed", 0),
                "div_id":   div_id,
                "div_name": div["div_name"],
            }
            if div["div_name"] == "American League West":
                al_west_data.append(record)
            if "American" in div["div_name"]:
                wildcard_data.append(record)

    al_west_data.sort(key=lambda x: (-x["w"], x["l"]))
    wildcard_data.sort(key=lambda x: (-x["w"], x["l"]))

    # Match Mariners by name — abbrev field unreliable on opening day
    sea_rank = next(
        (i + 1 for i, t in enumerate(al_west_data)
         if "seattle" in t["team"].lower()),
        None
    )

    # Also backfill abbreviation if missing
    abbrev_map = {
        "seattle mariners":    "SEA",
        "houston astros":      "HOU",
        "texas rangers":       "TEX",
        "los angeles angels":  "LAA",
        "athletics":           "OAK",
        "oakland athletics":   "OAK",
    }
    for t in al_west_data:
        if not t["abbrev"]:
            t["abbrev"] = abbrev_map.get(t["team"].lower(), "")

    output = {
        "updated":     date.today().isoformat(),
        "season":      SEASON,
        "al_west":     al_west_data,
        "al_wildcard": wildcard_data[:10],
        "sea_rank":    sea_rank,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "standings.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✅ Saved → {out_path}")
    print(f"  🧢 Mariners rank in AL West: #{sea_rank}")
    print(f"  📋 Teams: {[t['team'] + ' (' + t['abbrev'] + ') ' + str(t['w']) + '-' + str(t['l']) for t in al_west_data]}")

    return output


if __name__ == "__main__":
    fetch_standings()
