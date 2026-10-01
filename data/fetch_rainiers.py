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


def fetch_recent_games(n: int = 10) -> list:
    """The last n completed Rainiers games of the season.

    Used to be "games in the last 7 days", which went empty the day the
    Triple-A season ended (Sept. 20) and stayed empty all offseason."""
    print(f"🌧️  Fetching the last {n} Rainiers results...")
    from mlb import get
    try:
        d = get("/schedule", sportId=11, teamId=TACOMA_ID, season=SEASON)
    except Exception as e:
        print(f"  ⚠️  Schedule fetch failed: {e}")
        return []
    games = []
    for day in d.get("dates", []):
        for g in day["games"]:
            if g["status"].get("abstractGameState") != "Final":
                continue
            h, a = g["teams"]["home"], g["teams"]["away"]
            if h.get("score") is None:
                continue
            tac_home = h["team"]["id"] == TACOMA_ID
            games.append({
                "date": g.get("officialDate") or day["date"],
                "home": h["team"]["name"], "away": a["team"]["name"],
                "home_score": h["score"], "away_score": a["score"],
                "game_pk": g["gamePk"],
                "win": bool((h if tac_home else a).get("isWinner")),
            })
    games.sort(key=lambda x: x["date"], reverse=True)
    return games[:n]


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
    """Everyone who played for Tacoma this season (not just today's roster)."""
    print("📋 Fetching Rainiers season stats...")
    from fetch_traditional import player_stats, batting_row, pitching_row
    try:
        bat = [batting_row(sp) for sp in player_stats("hitting", TACOMA_ID, 11)]
        pit = [pitching_row(sp) for sp in player_stats("pitching", TACOMA_ID, 11)]
    except Exception as e:
        print(f"  ⚠️  Rainiers stats failed: {e}")
        return {"batters": [], "pitchers": []}
    for p in bat + pit:
        p["prospect"] = any(pw.lower() in p["name"].lower() for pw in PROSPECT_WATCH)
    batters = sorted([b for b in bat if (b["ab"] or 0) > 0 and b["pos"] != "P"], key=lambda b: -(b["pa"] or 0))
    pitchers = sorted([p for p in pit if p["outs"] > 0], key=lambda p: (p["role"] != "SP", -p["outs"]))
    print(f"  ✅ {len(batters)} batters, {len(pitchers)} pitchers")
    return {"batters": batters, "pitchers": pitchers}


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

    tac = next((t for t in standings if "Tacoma" in t["team"]), None)
    output = {
        "updated":        date.today().isoformat(),
        "season":         SEASON,
        "season_record":  f"{tac['w']}-{tac['l']}" if tac else None,
        "recent_record":  f"{wins}-{losses} (last {len(games)} games)",
        "recent_games":   games,
        "roster":         roster,
        "pcl_standings":  standings,
        "prospect_watch": PROSPECT_WATCH,
    }

    from mlb import save
    ok = len(roster["batters"]) >= 9 and len(standings) >= 5
    save("rainiers.json", output, ok,
         f"{len(roster['batters'])} batters, {len(roster['pitchers'])} pitchers, {len(games)} recent games")
    return output


if __name__ == "__main__":
    fetch_rainiers_all()
