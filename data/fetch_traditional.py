"""
edgar/data/fetch_traditional.py
────────────────────────────────
Pulls traditional Mariners stats via MLB StatsAPI:

BATTING:  AVG · OBP · SLG · OPS · H · AB · R · HR · RBI · SB · BB · SO · 2B · 3B
PITCHING: ERA · W · L · SV · IP · H · R · ER · BB · SO · HR · WHIP · HLD

Outputs: data/cache/traditional.json
"""

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, DATA_DIR, MARINERS_ID

import statsapi


def safe(val, t=float, decimals=3):
    try:
        v = t(val)
        return round(v, decimals) if t == float else v
    except (TypeError, ValueError):
        return None


def fetch_batting() -> list:
    """Pull season batting stats for every Mariner with a plate appearance."""
    print("🏏 Fetching Mariners batting stats...")

    try:
        roster_raw = statsapi.get(
            "team_roster",
            {"teamId": MARINERS_ID, "rosterType": "active", "season": SEASON},
        )
        players = roster_raw.get("roster", [])
    except Exception as e:
        print(f"  ⚠️  Roster fetch failed: {e}")
        return []

    batters = []

    for p in players:
        pid   = p["person"]["id"]
        pname = p["person"]["fullName"]
        pos   = p["position"]["abbreviation"]

        try:
            stats_raw = statsapi.get("person", {
                "personId": pid,
                "hydrate": f"stats(group=hitting,type=season,season={SEASON})",
            })
            splits = (
                stats_raw.get("people", [{}])[0]
                .get("stats", [{}])[0]
                .get("splits", [])
            )
            if not splits:
                continue

            s = splits[0]["stat"]

            batters.append({
                "id":    pid,
                "name":  pname,
                "pos":   pos,
                "ab":    safe(s.get("atBats"), int),
                "avg":   safe(s.get("avg")),
                "obp":   safe(s.get("obp")),
                "slg":   safe(s.get("slg")),
                "ops":   safe(s.get("ops")),
                "h":     safe(s.get("hits"), int),
                "r":     safe(s.get("runs"), int),
                "hr":    safe(s.get("homeRuns"), int),
                "rbi":   safe(s.get("rbi"), int),
                "sb":    safe(s.get("stolenBases"), int),
                "bb":    safe(s.get("baseOnBalls"), int),
                "so":    safe(s.get("strikeOuts"), int),
                "doubles": safe(s.get("doubles"), int),
                "triples": safe(s.get("triples"), int),
                "pa":    safe(s.get("plateAppearances"), int),
                "gidp": safe(s.get("groundIntoDoublePlay"), int),
                "hbp":  safe(s.get("hitByPitch"), int),
            })

        except Exception as e:
            continue

    # Sort by PA descending — most active players first
    batters.sort(key=lambda x: (x.get("pa") or 0), reverse=True)
    batters = [b for b in batters if (b.get("ab") or 0) > 0]

    print(f"  ✅ {len(batters)} batters with stats")
    return batters


def fetch_pitching() -> list:
    """Pull season pitching stats for every Mariner pitcher."""
    print("⚾ Fetching Mariners pitching stats...")

    try:
        roster_raw = statsapi.get(
            "team_roster",
            {"teamId": MARINERS_ID, "rosterType": "active", "season": SEASON},
        )
        players = roster_raw.get("roster", [])
    except Exception as e:
        print(f"  ⚠️  Roster fetch failed: {e}")
        return []

    pitchers = []

    for p in players:
        if p["position"]["abbreviation"] not in ("P", "SP", "RP", "CL"):
            # Also try two-way players
            pass

        pid   = p["person"]["id"]
        pname = p["person"]["fullName"]
        pos   = p["position"]["abbreviation"]

        try:
            stats_raw = statsapi.get("person", {
                "personId": pid,
                "hydrate": f"stats(group=pitching,type=season,season={SEASON})",
            })
            splits = (
                stats_raw.get("people", [{}])[0]
                .get("stats", [{}])[0]
                .get("splits", [])
            )
            if not splits:
                continue

            s = splits[0]["stat"]

            ip_raw = s.get("inningsPitched", "0.0")
            try:
                ip = float(ip_raw)
            except ValueError:
                ip = 0.0

            if ip == 0.0:
                continue

            # Determine role from games started
            gs = safe(s.get("gamesStarted"), int) or 0
            role = "SP" if gs >= 1 else "RP"

            pitchers.append({
                "id":    pid,
                "name":  pname,
                "pos":   pos,
                "role":  role,
                "w":     safe(s.get("wins"), int),
                "l":     safe(s.get("losses"), int),
                "era":   safe(s.get("era")),
                "g":     safe(s.get("gamesPitched"), int),
                "gs":    gs,
                "sv":    safe(s.get("saves"), int),
                "hld":   safe(s.get("holds"), int),
                "ip":    safe(ip),
                "h":     safe(s.get("hits"), int),
                "r":     safe(s.get("runs"), int),
                "er":    safe(s.get("earnedRuns"), int),
                "bb":    safe(s.get("baseOnBalls"), int),
                "so":    safe(s.get("strikeOuts"), int),
                "hr":    safe(s.get("homeRuns"), int),
                "whip":  safe(s.get("whip")),
                "k9":    safe(s.get("strikeoutsPer9Inn")),
                "bb9":   safe(s.get("walksPer9Inn")),
                "avg":   safe(s.get("avg")),
            })

        except Exception:
            continue

    # Sort: starters first by IP, then relievers by IP
    starters  = sorted([p for p in pitchers if p["role"] == "SP"],
                       key=lambda x: x.get("ip") or 0, reverse=True)
    relievers = sorted([p for p in pitchers if p["role"] == "RP"],
                       key=lambda x: x.get("ip") or 0, reverse=True)

    print(f"  ✅ {len(starters)} starters, {len(relievers)} relievers with stats")
    return starters + relievers


def fetch_team_batting() -> dict:
    """Team-level aggregate batting line."""
    print("📊 Fetching team batting totals...")
    try:
        stats_raw = statsapi.get("team_stats", {
            "teamId": MARINERS_ID,
            "group":  "hitting",
            "type":   "season",
            "season": SEASON,
        })
        splits = stats_raw.get("stats", [{}])[0].get("splits", [])
        if not splits:
            return {}
        s = splits[0]["stat"]
        return {
            "avg":  safe(s.get("avg")),
            "obp":  safe(s.get("obp")),
            "slg":  safe(s.get("slg")),
            "ops":  safe(s.get("ops")),
            "hr":   safe(s.get("homeRuns"), int),
            "rbi":  safe(s.get("rbi"), int),
            "r":    safe(s.get("runs"), int),
            "sb":   safe(s.get("stolenBases"), int),
            "so":   safe(s.get("strikeOuts"), int),
            "bb":   safe(s.get("baseOnBalls"), int),
        }
    except Exception as e:
        print(f"  ⚠️  Team batting failed: {e}")
        return {}


def fetch_team_pitching() -> dict:
    """Team-level aggregate pitching line."""
    print("📊 Fetching team pitching totals...")
    try:
        stats_raw = statsapi.get("team_stats", {
            "teamId": MARINERS_ID,
            "group":  "pitching",
            "type":   "season",
            "season": SEASON,
        })
        splits = stats_raw.get("stats", [{}])[0].get("splits", [])
        if not splits:
            return {}
        s = splits[0]["stat"]
        return {
            "era":  safe(s.get("era")),
            "whip": safe(s.get("whip")),
            "so":   safe(s.get("strikeOuts"), int),
            "bb":   safe(s.get("baseOnBalls"), int),
            "hr":   safe(s.get("homeRuns"), int),
            "sv":   safe(s.get("saves"), int),
        }
    except Exception as e:
        print(f"  ⚠️  Team pitching failed: {e}")
        return {}


def fetch_traditional_all():
    batting        = fetch_batting()
    pitching       = fetch_pitching()
    team_batting   = fetch_team_batting()
    team_pitching  = fetch_team_pitching()

    output = {
        "updated":       date.today().isoformat(),
        "season":        SEASON,
        "batting":       batting,
        "pitching":      pitching,
        "team_batting":  team_batting,
        "team_pitching": team_pitching,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "traditional.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  ✅ Saved → {out_path}")
    return output


if __name__ == "__main__":
    fetch_traditional_all()
