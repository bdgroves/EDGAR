"""
edgar/data/fetch_rainiers.py
─────────────────────────────
Tracks the Tacoma Rainiers (Triple-A, Mariners affiliate):
  - Recent results (last 7 games)
  - Current roster with batting / pitching stats
  - Top prospect stats (flagged by prospect_watch list)
  - Pacific Coast League standings (Tacoma's division)

Outputs: data/cache/rainiers.json
"""

import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, DATA_DIR, TACOMA_ID

import statsapi


# ── Prospect watch list (update as needed each season) ────────────
# These are names to highlight on the dashboard
PROSPECT_WATCH = [
    "Cole Young",
    "Harry Ford",
    "Jonah Bride",
    "Colt Emerson",
    "Lazaro Montes",
    "Bryce Miller",      # may be up/down
    "Bryan Woo",
]


def fetch_recent_games(days: int = 7) -> list[dict]:
    """Fetch Tacoma's last N days of schedule/results."""
    print(f"🌧️  Fetching Rainiers results (last {days} days)...")

    end_dt   = date.today()
    start_dt = end_dt - timedelta(days=days)

    try:
        schedule = statsapi.schedule(
            start_date=start_dt.strftime("%m/%d/%Y"),
            end_date=end_dt.strftime("%m/%d/%Y"),
            team=TACOMA_ID,
        )
    except Exception as e:
        print(f"  ⚠️  Schedule fetch failed: {e}")
        return []

    games = []
    for g in schedule:
        if g.get("status") not in ("Final", "Game Over"):
            continue
        games.append({
            "date":      g.get("game_date"),
            "home":      g.get("home_name"),
            "away":      g.get("away_name"),
            "home_score": g.get("home_score"),
            "away_score": g.get("away_score"),
            "venue":     g.get("venue_name"),
            "win":       (
                (g.get("home_name", "").startswith("Tacoma") and g.get("home_score", 0) > g.get("away_score", 0))
                or
                (g.get("away_name", "").startswith("Tacoma") and g.get("away_score", 0) > g.get("home_score", 0))
            ),
        })

    games.sort(key=lambda x: x["date"], reverse=True)
    return games


def fetch_roster_stats() -> dict:
    """Pull Tacoma 40-man roster with basic stats via MLB StatsAPI."""
    print("📋 Fetching Rainiers roster...")

    try:
        # Active roster
        roster_raw = statsapi.get(
            "team_roster",
            {"teamId": TACOMA_ID, "rosterType": "active", "season": SEASON},
        )
        players = roster_raw.get("roster", [])
    except Exception as e:
        print(f"  ⚠️  Roster fetch failed: {e}")
        return {"batters": [], "pitchers": []}

    batters   = []
    pitchers  = []

    for p in players:
        pid    = p["person"]["id"]
        pname  = p["person"]["fullName"]
        pos    = p["position"]["abbreviation"]
        is_prospect = any(pw.lower() in pname.lower() for pw in PROSPECT_WATCH)

        try:
            stats_raw = statsapi.player_stats(
                pid,
                group="hitting" if pos != "P" else "pitching",
                type="season",
            )
        except Exception:
            stats_raw = ""

        entry = {
            "id":          pid,
            "name":        pname,
            "pos":         pos,
            "prospect":    is_prospect,
            "stats_text":  stats_raw,
        }

        if pos == "P":
            pitchers.append(entry)
        else:
            batters.append(entry)

    return {"batters": batters, "pitchers": pitchers}


def fetch_pcl_standings() -> list[dict]:
    """
    Pacific Coast League standings — Tacoma's Triple-A league.
    MLB StatsAPI sport IDs: 1=MLB, 11=Triple-A
    """
    print("🏆 Fetching PCL standings...")

    try:
        raw = statsapi.standings_data(leagueId="117", season=SEASON)
        # leagueId 117 = Pacific Coast League (Triple-A West)
    except Exception:
        try:
            # Fallback: leagueId 112 covers some MiLB configs
            raw = statsapi.standings_data(leagueId="112", season=SEASON)
        except Exception as e:
            print(f"  ⚠️  PCL standings failed: {e}")
            return []

    teams = []
    for div_id, div in raw.items():
        for team in div["teams"]:
            teams.append({
                "team":   team["name"],
                "w":      team["w"],
                "l":      team["l"],
                "pct":    round(team["w"] / max(team["w"] + team["l"], 1), 3),
                "gb":     team["gb"],
                "div":    div["div_name"],
            })

    teams.sort(key=lambda x: (-x["w"], x["l"]))
    return teams


def fetch_rainiers_all():
    games     = fetch_recent_games()
    roster    = fetch_roster_stats()
    standings = fetch_pcl_standings()

    # W-L from recent games
    wins   = sum(1 for g in games if g["win"])
    losses = len(games) - wins

    output = {
        "updated":          date.today().isoformat(),
        "season":           SEASON,
        "recent_record":    f"{wins}-{losses} (last {len(games)} games)",
        "recent_games":     games,
        "roster":           roster,
        "pcl_standings":    standings,
        "prospect_watch":   PROSPECT_WATCH,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "rainiers.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✅ Saved → {out_path}")
    return output


if __name__ == "__main__":
    fetch_rainiers_all()
