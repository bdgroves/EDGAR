"""Probe MLB StatsAPI / Savant / FanGraphs shapes from Actions (sandbox has no network)."""
import json, traceback, requests
out = {}
B = "https://statsapi.mlb.com/api/v1"
def get(path, **p):
    r = requests.get(B + path, params=p, timeout=60); r.raise_for_status(); return r.json()
def trunc(o, n=3):
    if isinstance(o, list): return [trunc(x, n) for x in o[:n]] + ([f"...{len(o)}"] if len(o) > n else [])
    if isinstance(o, dict): return {k: trunc(v, n) for k, v in o.items()}
    return o
def step(name, fn):
    try: out[name] = fn()
    except Exception as e: out[name] = {"error": traceback.format_exc()[-1500:]}
step("standings", lambda: trunc(get("/standings", leagueId=103, season=2026, standingsTypes="regularSeason", hydrate="team"), 2))
step("wildcard", lambda: trunc(get("/standings", leagueId=103, season=2026, standingsTypes="wildCard"), 2))
step("team_stats", lambda: get("/teams/136/stats", stats="season", group="hitting,pitching", season=2026))
step("players_hit", lambda: (lambda d: {"n": len(d["stats"][0]["splits"]), "sample": d["stats"][0]["splits"][:2], "names": [s["player"]["fullName"] + " " + str(s["stat"].get("plateAppearances")) for s in d["stats"][0]["splits"]]})(get("/stats", stats="season", group="hitting", teamId=136, season=2026, playerPool="ALL", limit=300)))
step("players_pit", lambda: (lambda d: {"n": len(d["stats"][0]["splits"]), "sample": d["stats"][0]["splits"][:1], "names": [s["player"]["fullName"] + " " + str(s["stat"].get("inningsPitched")) for s in d["stats"][0]["splits"]]})(get("/stats", stats="season", group="pitching", teamId=136, season=2026, playerPool="ALL", limit=300)))
step("league_pitching", lambda: (lambda d: {"n": len(d["stats"][0]["splits"]), "sample": d["stats"][0]["splits"][:1]})(get("/teams/stats", stats="season", group="pitching", season=2026, sportIds=1)))
step("schedule", lambda: (lambda d: {"dates": len(d["dates"]), "first": d["dates"][0], "last": d["dates"][-1]})(get("/schedule", sportId=1, teamId=136, season=2026, gameType="R")))
step("postseason", lambda: trunc(get("/schedule/postseason/series", season=2026, sportId=1), 2))
step("rainiers_sched", lambda: (lambda d: {"dates": len(d["dates"]), "last": d["dates"][-1] if d["dates"] else None})(get("/schedule", sportId=11, teamId=529, season=2026)))
def pb():
    import pybaseball as p
    r = {}
    for name, f in [("fg_pitching", lambda: p.pitching_stats(2026, 2026, qual=1).shape),
                    ("pitcher_expected", lambda: (lambda d: [d.shape, list(d.columns)])(p.statcast_pitcher_expected_stats(2026, minPA=1))),
                    ("arsenal_stats", lambda: (lambda d: [d.shape, list(d.columns)])(p.statcast_pitcher_arsenal_stats(2026, minPA=1))),
                    ("pitch_arsenal_speed", lambda: (lambda d: [d.shape, list(d.columns)])(p.statcast_pitcher_pitch_arsenal(2026, minP=1, arsenal_type="avg_speed"))),
                    ("pitcher_pitchlevel", lambda: (lambda d: [d.shape, d["description"].value_counts().to_dict(), d["pitch_type"].value_counts().to_dict()])(p.statcast_pitcher("2026-03-20", "2026-10-01", 669302))),
                    ("batter_percentile", lambda: (lambda d: [d.shape, list(d.columns)])(p.statcast_batter_percentile_ranks(2026)))]:
        try: r[name] = f()
        except Exception as e: r[name] = "ERROR " + repr(e)[:400]
    return r
step("pybaseball", pb)
json.dump(out, open("tools/probe_out.json", "w"), indent=1, default=str)
