"""
edgar/data/fetch_traditional.py
────────────────────────────────
Season batting and pitching for every player who appeared for the Mariners,
and the official team totals, from the MLB StatsAPI /stats endpoint.

Earlier versions walked the *active* roster and summed it for team totals.
That dropped anyone traded, released or optioned (Luis Castillo's 99⅔
innings, Luke Raley, Matt Brash...), and summing innings pitched as decimals
(36.2 + 36.2 = 72.4, not 73⅓) made the team totals wrong too.

Outputs: data/cache/traditional.json
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, MARINERS_ID
from mlb import get, save, num, integer, ip_to_outs


def player_stats(group, team_id=MARINERS_ID, sport_id=1):
    d = get("/stats", stats="season", group=group, teamId=team_id, season=SEASON,
            sportIds=sport_id, playerPool="ALL", limit=500)
    return d["stats"][0]["splits"] if d.get("stats") else []


def batting_row(sp):
    s, p = sp["stat"], sp["player"]
    return {
        "id": p["id"], "name": p["fullName"],
        "pos": (sp.get("position") or {}).get("abbreviation", ""),
        "g": integer(s.get("gamesPlayed")),
        "pa": integer(s.get("plateAppearances")), "ab": integer(s.get("atBats")),
        "avg": num(s.get("avg"), 3), "obp": num(s.get("obp"), 3),
        "slg": num(s.get("slg"), 3), "ops": num(s.get("ops"), 3),
        "h": integer(s.get("hits")), "r": integer(s.get("runs")),
        "doubles": integer(s.get("doubles")), "triples": integer(s.get("triples")),
        "hr": integer(s.get("homeRuns")), "rbi": integer(s.get("rbi")),
        "sb": integer(s.get("stolenBases")), "cs": integer(s.get("caughtStealing")),
        "bb": integer(s.get("baseOnBalls")), "so": integer(s.get("strikeOuts")),
        "hbp": integer(s.get("hitByPitch")), "gidp": integer(s.get("groundIntoDoublePlay")),
        "babip": num(s.get("babip"), 3),
    }


def pitching_row(sp):
    s, p = sp["stat"], sp["player"]
    g, gs = integer(s.get("gamesPitched")) or 0, integer(s.get("gamesStarted")) or 0
    outs = ip_to_outs(s.get("inningsPitched"))
    return {
        "id": p["id"], "name": p["fullName"], "pos": "P",
        # a starter is someone who started at least half his games
        "role": "SP" if gs and gs * 2 >= g else "RP",
        "w": integer(s.get("wins")), "l": integer(s.get("losses")),
        "era": num(s.get("era"), 2), "g": g, "gs": gs,
        "sv": integer(s.get("saves")), "hld": integer(s.get("holds")),
        "bs": integer(s.get("blownSaves")),
        "ip": s.get("inningsPitched"), "outs": outs,
        "h": integer(s.get("hits")), "r": integer(s.get("runs")), "er": integer(s.get("earnedRuns")),
        "bb": integer(s.get("baseOnBalls")), "so": integer(s.get("strikeOuts")),
        "hr": integer(s.get("homeRuns")), "hbp": integer(s.get("hitByPitch")),
        "bf": integer(s.get("battersFaced")),
        "whip": num(s.get("whip"), 2), "k9": num(s.get("strikeoutsPer9Inn"), 2),
        "bb9": num(s.get("walksPer9Inn"), 2), "avg": num(s.get("avg"), 3),
    }


def team_totals():
    d = get(f"/teams/{MARINERS_ID}/stats", stats="season", group="hitting,pitching", season=SEASON)
    out = {}
    for block in d["stats"]:
        s = block["splits"][0]["stat"] if block["splits"] else {}
        out[block["group"]["displayName"]] = s
    h, p = out.get("hitting", {}), out.get("pitching", {})
    tb = {
        "g": integer(h.get("gamesPlayed")),
        "avg": num(h.get("avg"), 3), "obp": num(h.get("obp"), 3), "slg": num(h.get("slg"), 3),
        "ops": num(h.get("ops"), 3), "hr": integer(h.get("homeRuns")), "rbi": integer(h.get("rbi")),
        "r": integer(h.get("runs")), "sb": integer(h.get("stolenBases")), "bb": integer(h.get("baseOnBalls")),
        "so": integer(h.get("strikeOuts")), "h": integer(h.get("hits")), "ab": integer(h.get("atBats")),
        "pa": integer(h.get("plateAppearances")), "source": "official",
    }
    tp = {
        "era": num(p.get("era"), 2), "whip": num(p.get("whip"), 2), "so": integer(p.get("strikeOuts")),
        "bb": integer(p.get("baseOnBalls")), "hr": integer(p.get("homeRuns")), "sv": integer(p.get("saves")),
        "bs": integer(p.get("blownSaves")), "hld": integer(p.get("holds")), "ip": p.get("inningsPitched"),
        "r": integer(p.get("runs")), "er": integer(p.get("earnedRuns")),
        "k9": num(p.get("strikeoutsPer9Inn"), 2), "source": "official",
    }
    return tb, tp


def fetch_traditional_all():
    print("🏏 Fetching Mariners batting + pitching (everyone who played)...")
    batting = [batting_row(s) for s in player_stats("hitting")]
    batting = [b for b in batting if (b["pa"] or 0) > 0 and b["pos"] != "P" or (b["pa"] or 0) >= 10]
    batting.sort(key=lambda b: -(b["pa"] or 0))

    pitching = [pitching_row(s) for s in player_stats("pitching")]
    pitching = [p for p in pitching if p["outs"] > 0]
    # Position players who mopped up an inning go last, after the real bullpen
    pitching.sort(key=lambda p: (p["role"] != "SP", p["id"] in {b["id"] for b in batting if (b["pa"] or 0) >= 30}, -p["outs"]))

    tb, tp = team_totals()
    output = {
        "updated": date.today().isoformat(),
        "season": SEASON,
        "batting": batting,
        "pitching": pitching,
        "team_batting": tb,
        "team_pitching": tp,
    }
    ok = len(batting) >= 9 and len(pitching) >= 8 and tb.get("g")
    save("traditional.json", output, ok, f"{len(batting)} hitters, {len(pitching)} pitchers, team G={tb.get('g')}")
    return output


if __name__ == "__main__":
    fetch_traditional_all()
