"""
edgar/data/fetch_traditional.py
────────────────────────────────
Pulls traditional Mariners stats via MLB StatsAPI.
Team totals are aggregated from roster stats as fallback
when the team endpoint returns 404 early in the season.
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
            ab = safe(s.get("atBats"), int) or 0
            if ab == 0:
                continue

            batters.append({
                "id":      pid,
                "name":    pname,
                "pos":     pos,
                "ab":      ab,
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
                "hbp":     safe(s.get("hitByPitch"), int),
                "gidp":    safe(s.get("groundIntoDoublePlay"), int),
            })
        except Exception:
            continue

    batters.sort(key=lambda x: (x.get("pa") or 0), reverse=True)
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

            try:
                ip = float(s.get("inningsPitched", 0))
            except ValueError:
                ip = 0.0
            if ip == 0.0:
                continue

            gs   = safe(s.get("gamesStarted"), int) or 0
            role = "SP" if gs >= 1 else "RP"

            pitchers.append({
                "id":   pid,
                "name": pname,
                "pos":  pos,
                "role": role,
                "w":    safe(s.get("wins"), int),
                "l":    safe(s.get("losses"), int),
                "era":  safe(s.get("era")),
                "g":    safe(s.get("gamesPitched"), int),
                "gs":   gs,
                "sv":   safe(s.get("saves"), int),
                "hld":  safe(s.get("holds"), int),
                "ip":   safe(ip),
                "h":    safe(s.get("hits"), int),
                "r":    safe(s.get("runs"), int),
                "er":   safe(s.get("earnedRuns"), int),
                "bb":   safe(s.get("baseOnBalls"), int),
                "so":   safe(s.get("strikeOuts"), int),
                "hr":   safe(s.get("homeRuns"), int),
                "whip": safe(s.get("whip")),
                "k9":   safe(s.get("strikeoutsPer9Inn")),
                "bb9":  safe(s.get("walksPer9Inn")),
                "avg":  safe(s.get("avg")),
            })
        except Exception:
            continue

    starters  = sorted([p for p in pitchers if p["role"] == "SP"],
                       key=lambda x: x.get("ip") or 0, reverse=True)
    relievers = sorted([p for p in pitchers if p["role"] == "RP"],
                       key=lambda x: x.get("ip") or 0, reverse=True)

    print(f"  ✅ {len(starters)} starters, {len(relievers)} relievers with stats")
    return starters + relievers


def aggregate_team_batting(batters: list) -> dict:
    """
    Aggregate team batting totals from roster stats.
    Used as fallback when the team endpoint returns 404 early season.
    """
    if not batters:
        return {}

    totals = {
        "h": 0, "ab": 0, "r": 0, "hr": 0, "rbi": 0,
        "sb": 0, "bb": 0, "so": 0, "pa": 0,
        "doubles": 0, "triples": 0,
    }
    for b in batters:
        for k in totals:
            totals[k] += b.get(k) or 0

    ab  = totals["ab"]
    pa  = totals["pa"]
    h   = totals["h"]
    bb  = totals["bb"]
    hr  = totals["hr"]

    avg  = round(h / ab, 3)       if ab  > 0 else None
    obp  = round((h + bb) / pa, 3) if pa > 0 else None
    tb   = h + totals["doubles"] + 2 * totals["triples"] + 3 * hr
    slg  = round(tb / ab, 3)      if ab  > 0 else None
    ops  = round(obp + slg, 3)    if (obp and slg) else None

    return {
        "avg":  avg,
        "obp":  obp,
        "slg":  slg,
        "ops":  ops,
        "hr":   hr,
        "rbi":  totals["rbi"],
        "r":    totals["r"],
        "sb":   totals["sb"],
        "bb":   bb,
        "so":   totals["so"],
        "h":    h,
        "ab":   ab,
        "source": "aggregated",
    }


def aggregate_team_pitching(pitchers: list) -> dict:
    """Aggregate team pitching totals from roster stats."""
    if not pitchers:
        return {}

    totals = {"er": 0, "ip": 0.0, "so": 0, "bb": 0, "hr": 0, "sv": 0, "h": 0}
    for p in pitchers:
        totals["er"]  += p.get("er") or 0
        totals["ip"]  += p.get("ip") or 0
        totals["so"]  += p.get("so") or 0
        totals["bb"]  += p.get("bb") or 0
        totals["hr"]  += p.get("hr") or 0
        totals["sv"]  += p.get("sv") or 0
        totals["h"]   += p.get("h")  or 0

    ip   = totals["ip"]
    era  = round((totals["er"] * 9) / ip, 2) if ip > 0 else None
    whip = round((totals["bb"] + totals["h"]) / ip, 3) if ip > 0 else None

    return {
        "era":  era,
        "whip": whip,
        "so":   totals["so"],
        "bb":   totals["bb"],
        "hr":   totals["hr"],
        "sv":   totals["sv"],
        "ip":   round(ip, 1),
        "source": "aggregated",
    }


def fetch_traditional_all():
    batters  = fetch_batting()
    pitchers = fetch_pitching()

    # Try official team endpoint first, fall back to aggregation
    print("📊 Computing team totals...")
    team_batting  = aggregate_team_batting(batters)
    team_pitching = aggregate_team_pitching(pitchers)

    if team_batting:
        print(f"  ✅ Team AVG: {team_batting.get('avg')} · OPS: {team_batting.get('ops')} · HR: {team_batting.get('hr')}")
    if team_pitching:
        print(f"  ✅ Team ERA: {team_pitching.get('era')} · WHIP: {team_pitching.get('whip')} · SO: {team_pitching.get('so')}")

    output = {
        "updated":       date.today().isoformat(),
        "season":        SEASON,
        "batting":       batters,
        "pitching":      pitchers,
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
