"""
edgar/data/fetch_rainiers.py
─────────────────────────────
Tracks the Tacoma Rainiers (Triple-A, Mariners affiliate):
  - Recent results (last 7 games)
  - Full roster batting stats (AVG, OBP, SLG, OPS, HR, RBI, SB, etc.)
  - Full roster pitching stats (ERA, WHIP, K, BB, SV, IP, etc.)
  - Top prospect stats (flagged by prospect_watch list)
  - Pacific Coast League standings

Outputs: data/cache/rainiers.json
"""

import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, DATA_DIR, TACOMA_ID

import statsapi


# ── Prospect watch list ───────────────────────────────────────────
PROSPECT_WATCH = [
    "Cole Young",
    "Harry Ford",
    "Jonah Bride",
    "Colt Emerson",
    "Lazaro Montes",
    "Bryce Miller",
    "Bryan Woo",
]


def safe(val, t=float, decimals=3):
    try:
        v = t(val)
        return round(v, decimals) if t == float else v
    except (TypeError, ValueError):
        return None


def fetch_recent_games(days: int = 7) -> list:
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
            "date":       g.get("game_date"),
            "home":       g.get("home_name"),
            "away":       g.get("away_name"),
            "home_score": g.get("home_score"),
            "away_score": g.get("away_score"),
            "venue":      g.get("venue_name"),
            "win": (
                (g.get("home_name","").startswith("Tacoma") and g.get("home_score",0) > g.get("away_score",0))
                or
                (g.get("away_name","").startswith("Tacoma") and g.get("away_score",0) > g.get("home_score",0))
            ),
        })

    games.sort(key=lambda x: x["date"], reverse=True)
    return games


def fetch_player_batting(pid: int) -> dict:
    """Pull season batting stats for one player via MLB StatsAPI."""
    try:
        raw = statsapi.get("person", {
            "personId": pid,
            "hydrate": f"stats(group=hitting,type=season,season={SEASON},sportId=11)",
        })
        splits = (
            raw.get("people", [{}])[0]
               .get("stats", [{}])[0]
               .get("splits", [])
        )
        if not splits:
            return {}
        s = splits[0]["stat"]
        return {
            "ab":      safe(s.get("atBats"), int),
            "avg":     safe(s.get("avg")),
            "obp":     safe(s.get("obp")),
            "slg":     safe(s.get("slg")),
            "ops":     safe(s.get("ops")),
            "h":       safe(s.get("hits"), int),
            "r":       safe(s.get("runs"), int),
            "hr":      safe(s.get("homeRuns"), int),
            "rbi":     safe(s.get("rbi"), int),
            "sb":      safe(s.get("stolenBases"), int),
            "bb":      safe(s.get("baseOnBalls"), int),
            "so":      safe(s.get("strikeOuts"), int),
            "doubles": safe(s.get("doubles"), int),
            "triples": safe(s.get("triples"), int),
            "pa":      safe(s.get("plateAppearances"), int),
        }
    except Exception:
        return {}


def fetch_player_pitching(pid: int) -> dict:
    """Pull season pitching stats for one player via MLB StatsAPI."""
    try:
        raw = statsapi.get("person", {
            "personId": pid,
            "hydrate": f"stats(group=pitching,type=season,season={SEASON},sportId=11)",
        })
        splits = (
            raw.get("people", [{}])[0]
               .get("stats", [{}])[0]
               .get("splits", [])
        )
        if not splits:
            return {}
        s = splits[0]["stat"]

        try:
            ip = float(s.get("inningsPitched", 0))
        except ValueError:
            ip = 0.0

        if ip == 0.0:
            return {}

        gs = safe(s.get("gamesStarted"), int) or 0
        return {
            "role":  "SP" if gs >= 1 else "RP",
            "w":     safe(s.get("wins"), int),
            "l":     safe(s.get("losses"), int),
            "era":   safe(s.get("era")),
            "g":     safe(s.get("gamesPitched"), int),
            "gs":    gs,
            "sv":    safe(s.get("saves"), int),
            "hld":   safe(s.get("holds"), int),
            "ip":    safe(ip),
            "h":     safe(s.get("hits"), int),
            "er":    safe(s.get("earnedRuns"), int),
            "bb":    safe(s.get("baseOnBalls"), int),
            "so":    safe(s.get("strikeOuts"), int),
            "hr":    safe(s.get("homeRuns"), int),
            "whip":  safe(s.get("whip")),
            "k9":    safe(s.get("strikeoutsPer9Inn")),
            "bb9":   safe(s.get("walksPer9Inn")),
            "avg":   safe(s.get("avg")),
        }
    except Exception:
        return {}


def fetch_roster_stats() -> dict:
    """Pull full Tacoma active roster with batting + pitching stats."""
    print("📋 Fetching Rainiers roster + stats...")

    try:
        roster_raw = statsapi.get(
            "team_roster",
            {"teamId": TACOMA_ID, "rosterType": "active", "season": SEASON},
        )
        players = roster_raw.get("roster", [])
    except Exception as e:
        print(f"  ⚠️  Roster fetch failed: {e}")
        return {"batters": [], "pitchers": []}

    batters  = []
    pitchers = []

    for p in players:
        pid       = p["person"]["id"]
        pname     = p["person"]["fullName"]
        pos       = p["position"]["abbreviation"]
        is_prospect = any(pw.lower() in pname.lower() for pw in PROSPECT_WATCH)

        if pos == "P":
            stats = fetch_player_pitching(pid)
            if stats:
                pitchers.append({
                    "id":       pid,
                    "name":     pname,
                    "pos":      pos,
                    "prospect": is_prospect,
                    **stats,
                })
        else:
            stats = fetch_player_batting(pid)
            if stats:
                batters.append({
                    "id":       pid,
                    "name":     pname,
                    "pos":      pos,
                    "prospect": is_prospect,
                    **stats,
                })

    # Sort batters by PA desc, pitchers: SP first then RP by IP
    batters.sort(key=lambda x: (x.get("pa") or 0), reverse=True)
    batters = [b for b in batters if (b.get("ab") or 0) > 0]

    sp = sorted([p for p in pitchers if p.get("role") == "SP"],
                key=lambda x: x.get("ip") or 0, reverse=True)
    rp = sorted([p for p in pitchers if p.get("role") == "RP"],
                key=lambda x: x.get("ip") or 0, reverse=True)

    print(f"  ✅ {len(batters)} batters, {len(sp)} starters, {len(rp)} relievers")
    return {"batters": batters, "pitchers": sp + rp}


def fetch_pcl_standings() -> list:
    print("🏆 Fetching PCL standings...")
    try:
        raw = statsapi.standings_data(leagueId="112", season=SEASON)
    except Exception as e:
        print(f"  ⚠️  PCL standings failed: {e}")
        return []

    teams = []
    for div_id, div in raw.items():
        for team in div["teams"]:
            teams.append({
                "team": team["name"],
                "w":    team["w"],
                "l":    team["l"],
                "pct":  round(team["w"] / max(team["w"] + team["l"], 1), 3),
                "gb":   team.get("gb", "-"),
                "div":  div["div_name"],
                "streak": team.get("streak", ""),
                "l10":    team.get("lastTen", ""),
            })

    teams.sort(key=lambda x: (-x["w"], x["l"]))
    return teams


def fetch_rainiers_all():
    games   = fetch_recent_games()
    roster  = fetch_roster_stats()
    standings = fetch_pcl_standings()

    wins   = sum(1 for g in games if g["win"])
    losses = len(games) - wins

    output = {
        "updated":        date.today().isoformat(),
        "season":         SEASON,
        "recent_record":  f"{wins}-{losses} (last {len(games)} games)",
        "recent_games":   games,
        "roster":         roster,
        "pcl_standings":  standings,
        "prospect_watch": PROSPECT_WATCH,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "rainiers.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✅ Saved → {out_path}")
    return output


if __name__ == "__main__":
    fetch_rainiers_all()
