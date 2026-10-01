"""
edgar/data/fetch_season.py
──────────────────────────
The season as a story: every Mariners game, and every AL West team's record
day by day, from the MLB StatsAPI schedule.

  - games:   date, opponent, home/away, runs for/against, W/L, game number,
             record after the game, games over .500, gamePk
  - race:    each AL West team's wins and losses after every date it played,
             for the games-back chart
  - splits:  by month, home/away, one-run games, blowouts (5+ runs),
             vs AL West, longest winning and losing streaks

Outputs: data/cache/season.json
"""

import os
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON, MARINERS_ID, AL_WEST
from mlb import get, save

AL_WEST_IDS = {v["id"]: k for k, v in AL_WEST.items()}


def team_games(team_id):
    d = get("/schedule", sportId=1, teamId=team_id, season=SEASON, gameType="R")
    out, seen = [], set()
    for day in d.get("dates", []):
        for g in day["games"]:
            if g["status"].get("abstractGameState") != "Final" or g["gamePk"] in seen:
                continue
            if g["status"].get("detailedState", "").startswith(("Postponed", "Cancelled")):
                continue
            seen.add(g["gamePk"])
            home = g["teams"]["home"]["team"]["id"] == team_id
            me, opp = (g["teams"]["home"], g["teams"]["away"]) if home else (g["teams"]["away"], g["teams"]["home"])
            if me.get("score") is None or opp.get("score") is None:
                continue
            out.append({
                "date": g.get("officialDate") or day["date"],
                "pk": g["gamePk"],
                "home": home,
                "opp_id": opp["team"]["id"],
                "opp": opp["team"]["name"],
                "rf": me["score"], "ra": opp["score"],
                "w": bool(me.get("isWinner")),
                "innings": g.get("scheduledInnings", 9),
                "dh": g.get("doubleHeader", "N"), "game_number": g.get("gameNumber", 1),
            })
    out.sort(key=lambda x: (x["date"], x["game_number"]))
    return out


def rec(games):
    w = sum(g["w"] for g in games)
    return {"w": w, "l": len(games) - w, "rf": sum(g["rf"] for g in games), "ra": sum(g["ra"] for g in games)}


def streaks(games):
    best = {"W": (0, None, None), "L": (0, None, None)}
    run, kind, start = 0, None, None
    for g in games:
        k = "W" if g["w"] else "L"
        if k == kind:
            run += 1
        else:
            kind, run, start = k, 1, g["date"]
        if run > best[k][0]:
            best[k] = (run, start, g["date"])
    return {k: {"len": v[0], "from": v[1], "to": v[2]} for k, v in best.items()}


def fetch_season():
    print("📈 Fetching season game logs...")
    sea = team_games(MARINERS_ID)
    w = l = 0
    for i, g in enumerate(sea, 1):
        w += g["w"]; l += not g["w"]
        g.update({"n": i, "wins": w, "losses": l, "over500": w - l, "abbr_opp": AL_WEST_IDS.get(g["opp_id"])})

    # AL West race: record after each date for all five teams
    race = {}
    for tid, abbr in AL_WEST_IDS.items():
        games = sea if tid == MARINERS_ID else team_games(tid)
        by_date, w = {}, 0
        for i, g in enumerate(games, 1):
            w += g["w"]
            by_date[g["date"]] = [w, i - w]
        race[abbr] = by_date
    # games back from the division lead on each date
    dates = sorted({d for t in race.values() for d in t})
    last = {t: [0, 0] for t in race}
    gb_series = {t: [] for t in race}
    for d in dates:
        for t in race:
            if d in race[t]:
                last[t] = race[t][d]
        lead = max(wl[0] - wl[1] for wl in last.values())
        for t in race:
            gb_series[t].append((lead - (last[t][0] - last[t][1])) / 2)

    months = defaultdict(list)
    for g in sea:
        months[g["date"][:7]].append(g)
    splits = {
        "months": [{"month": m, **rec(gs)} for m, gs in sorted(months.items())],
        "home": rec([g for g in sea if g["home"]]),
        "away": rec([g for g in sea if not g["home"]]),
        "one_run": rec([g for g in sea if abs(g["rf"] - g["ra"]) == 1]),
        "blowouts": rec([g for g in sea if abs(g["rf"] - g["ra"]) >= 5]),
        "vs_al_west": rec([g for g in sea if g["opp_id"] in AL_WEST_IDS]),
        "streaks": streaks(sea),
        "high_water": max(sea, key=lambda g: g["over500"])["over500"] if sea else None,
        "high_water_date": max(sea, key=lambda g: (g["over500"], g["n"]))["date"] if sea else None,
        "low_water": min(sea, key=lambda g: g["over500"])["over500"] if sea else None,
        "low_water_date": min(sea, key=lambda g: (g["over500"], -g["n"]))["date"] if sea else None,
    }

    output = {
        "updated": date.today().isoformat(),
        "season": SEASON,
        "games": sea,
        "race": {"dates": dates, "gb": gb_series},
        "splits": splits,
    }
    ok = len(sea) >= 1
    save("season.json", output, ok, f"{len(sea)} Mariners games, {len(dates)} race dates")
    return output


if __name__ == "__main__":
    fetch_season()
