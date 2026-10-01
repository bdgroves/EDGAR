"""
edgar/data/fetch_standings.py
─────────────────────────────
AL West and AL Wild Card standings from the MLB StatsAPI /standings endpoint,
plus where the postseason stands.

Earlier versions used statsapi.standings_data(), which returns only W/L/GB:
streak, last-ten and runs came back empty all season, and the "wild card"
table was simply the ten best AL records (division leaders included).

Outputs: data/cache/standings.json
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, MARINERS_ID
from mlb import get, save, num

AL = 103
AL_WEST_DIV = 200


def _split(rec, kind):
    for s in rec.get("records", {}).get("splitRecords", []):
        if s.get("type") == kind:
            return f"{s['wins']}-{s['losses']}"
    return ""


def _xwl(rec):
    for s in rec.get("records", {}).get("expectedRecords", []):
        if s.get("type") == "xWinLossSeason":
            return f"{s['wins']}-{s['losses']}"
    return ""


def _row(rec, abbrevs):
    t = rec["team"]
    w, l = rec["wins"], rec["losses"]
    return {
        "id": t["id"],
        "team": t.get("name", ""),
        "abbrev": t.get("abbreviation") or abbrevs.get(t["id"], ""),
        "w": w, "l": l,
        "pct": round(w / max(w + l, 1), 3),
        "gb": rec.get("divisionGamesBack") or rec.get("gamesBack", "-"),
        "wc_gb": rec.get("wildCardGamesBack", ""),
        "wc_rank": rec.get("wildCardRank"),
        "div_rank": rec.get("divisionRank"),
        "streak": (rec.get("streak") or {}).get("streakCode", ""),
        "l10": _split(rec, "lastTen"),
        "home": _split(rec, "home"),
        "away": _split(rec, "away"),
        "one_run": _split(rec, "oneRun"),
        "extra": _split(rec, "extraInning"),
        "x_record": _xwl(rec),
        "rs": rec.get("runsScored", 0),
        "ra": rec.get("runsAllowed", 0),
        "diff": rec.get("runDifferential", 0),
        "games": rec.get("gamesPlayed", 0),
        "clinch": rec.get("clinchIndicator", ""),
        "elim": rec.get("eliminationNumber", ""),
        "div_champ": rec.get("divisionChamp", False),
    }


def fetch_postseason():
    """Series, results so far, and whether SEA is in it."""
    try:
        d = get("/schedule/postseason/series", season=SEASON, sportId=1)
    except Exception as e:
        print(f"  ⚠️  Postseason fetch failed: {e}")
        return None
    out = []
    for s in d.get("series", []):
        games = s.get("games", [])
        if not games:
            continue
        g0 = games[0]
        a, h = g0["teams"]["away"]["team"], g0["teams"]["home"]["team"]
        wins = {a["name"]: 0, h["name"]: 0}
        for g in games:
            for side in ("away", "home"):
                if g["teams"][side].get("isWinner"):
                    wins[g["teams"][side]["team"]["name"]] = wins.get(g["teams"][side]["team"]["name"], 0) + 1
        out.append({
            "series": g0.get("seriesDescription", ""),
            "label": g0.get("description", "").replace(" Game 1", ""),
            "teams": list(wins.keys()),
            "wins": wins,
            "games_in_series": g0.get("gamesInSeries"),
            "start": g0.get("officialDate"),
        })
    return out


def fetch_standings():
    print("📊 Fetching standings...")
    teams = get("/teams", sportId=1, season=SEASON)["teams"]
    abbrevs = {t["id"]: t.get("abbreviation", "") for t in teams}
    names = {t["id"]: t.get("name", "") for t in teams}

    reg = get("/standings", leagueId=AL, season=SEASON, standingsTypes="regularSeason", hydrate="team")
    al_all, al_west = [], []
    for block in reg["records"]:
        for rec in block["teamRecords"]:
            row = _row(rec, abbrevs)
            row["div_id"] = block["division"]["id"]
            al_all.append(row)
            if block["division"]["id"] == AL_WEST_DIV:
                al_west.append(row)
    al_west.sort(key=lambda r: int(r["div_rank"] or 9))

    wc = get("/standings", leagueId=AL, season=SEASON, standingsTypes="wildCard")
    wildcard = []
    for block in wc["records"]:
        for rec in block["teamRecords"]:
            row = _row(rec, abbrevs)
            row["team"] = names.get(row["id"], row["team"])
            wildcard.append(row)
    wildcard.sort(key=lambda r: int(r["wc_rank"] or 99))

    sea = next((r for r in al_west if r["id"] == MARINERS_ID), None)
    games_left = sum(162 - r["games"] for r in al_all)
    post = fetch_postseason()

    output = {
        "updated": date.today().isoformat(),
        "season": SEASON,
        "final": games_left == 0,
        "al_west": al_west,
        "al_wildcard": wildcard,
        "sea_rank": int(sea["div_rank"]) if sea and sea["div_rank"] else None,
        "postseason": post,
    }
    ok = len(al_west) == 5 and sea is not None and sea["w"] + sea["l"] > 0
    save("standings.json", output, ok, f"{len(al_west)} AL West teams, SEA {sea['w']}-{sea['l']}" if sea else "SEA missing")
    return output


if __name__ == "__main__":
    fetch_standings()
