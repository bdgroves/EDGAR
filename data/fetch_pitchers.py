"""
edgar/data/fetch_pitchers.py
─────────────────────────────
Advanced pitching for every Mariners pitcher:
  - FIP, K%, BB%, K-BB%, HR/9 computed from MLB StatsAPI counting stats,
    with this season's league FIP constant
  - xERA and xwOBA from Baseball Savant's expected-stats leaderboard
  - CSW%, SwStr%, whiff% and the pitch arsenal (usage, velocity, whiff% and
    CSW% by pitch) from Savant pitch-by-pitch data

The original version read all of this from FanGraphs through pybaseball.
FanGraphs started refusing those requests (HTTP 403), the fetch returned an
empty list, and the empty list was saved: the Advanced P tab was blank from
early April 2026 to the end of the season. Everything here now comes from
MLB StatsAPI and Baseball Savant, and save() refuses to publish an empty file.

Outputs: data/cache/pitchers.json
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SEASON
from mlb import get, save, num, ip_to_outs
from fetch_traditional import player_stats, pitching_row

import pandas as pd
import pybaseball

pybaseball.cache.enable()

PITCH_NAMES = {
    "FF": "4-Seam", "SI": "Sinker", "FC": "Cutter", "SL": "Slider", "ST": "Sweeper",
    "CU": "Curve", "KC": "Knuckle Curve", "CH": "Changeup", "FS": "Splitter",
    "SV": "Slurve", "FO": "Forkball", "KN": "Knuckleball", "SC": "Screwball", "CS": "Slow Curve",
}
CALLED = {"called_strike"}
WHIFF = {"swinging_strike", "swinging_strike_blocked", "foul_tip", "missed_bunt"}
SWING = WHIFF | {"foul", "foul_bunt", "hit_into_play", "foul_pitchout"}


def league_fip_constant():
    """cFIP = lgERA - (13*HR + 3*(BB+HBP) - 2*K) / IP, from all 30 teams."""
    d = get("/teams/stats", stats="season", group="pitching", season=SEASON, sportIds=1)
    tot = {"er": 0, "outs": 0, "hr": 0, "bb": 0, "hbp": 0, "so": 0}
    for sp in d["stats"][0]["splits"]:
        s = sp["stat"]
        tot["er"] += int(s.get("earnedRuns", 0))
        tot["outs"] += ip_to_outs(s.get("inningsPitched"))
        tot["hr"] += int(s.get("homeRuns", 0))
        tot["bb"] += int(s.get("baseOnBalls", 0))
        tot["hbp"] += int(s.get("hitByPitch", 0))
        tot["so"] += int(s.get("strikeOuts", 0))
    ip = tot["outs"] / 3
    lg_era = 9 * tot["er"] / ip
    c = lg_era - (13 * tot["hr"] + 3 * (tot["bb"] + tot["hbp"]) - 2 * tot["so"]) / ip
    return round(c, 3), round(lg_era, 2)


def with_fip(p, cfip):
    ip = p["outs"] / 3
    bf = p.get("bf") or 0
    if ip > 0:
        p["fip"] = round((13 * p["hr"] + 3 * (p["bb"] + (p["hbp"] or 0)) - 2 * p["so"]) / ip + cfip, 2)
        p["hr9"] = round(9 * p["hr"] / ip, 2)
    if bf:
        p["k_pct"] = round(100 * p["so"] / bf, 1)
        p["bb_pct"] = round(100 * p["bb"] / bf, 1)
        p["k_bb_pct"] = round(p["k_pct"] - p["bb_pct"], 1)
    return p


def savant_expected(ids):
    try:
        df = pybaseball.statcast_pitcher_expected_stats(SEASON, minPA=1)
    except Exception as e:
        print(f"  ⚠️  Savant expected stats failed: {e}")
        return {}
    df = df[df["player_id"].isin(ids)]
    return {int(r.player_id): {"xera": num(r.xera, 2), "xwoba": num(r.est_woba, 3), "woba": num(r.woba, 3)}
            for r in df.itertuples()}


def pitch_level(pid):
    """Season pitch-by-pitch for one pitcher → plate discipline + arsenal."""
    df = pybaseball.statcast_pitcher(f"{SEASON}-03-01", f"{SEASON}-11-30", pid)
    if df is None or df.empty:
        return None
    df = df[df["game_type"] == "R"] if "game_type" in df.columns else df
    df = df[df["pitch_type"].notna() & (df["pitch_type"] != "PO")]
    n = len(df)
    if n == 0:
        return None
    desc = df["description"]
    called, whiff, swings = desc.isin(CALLED).sum(), desc.isin(WHIFF).sum(), desc.isin(SWING).sum()
    arsenal = []
    for pt, g in df.groupby("pitch_type"):
        k = len(g)
        if k / n < 0.02:          # ignore pitches thrown less than 2% of the time
            continue
        sw = g["description"].isin(SWING).sum()
        arsenal.append({
            "pitch_type": pt, "name": PITCH_NAMES.get(pt, pt),
            "pct": round(100 * k / n, 1),
            "avg_velo": num(g["release_speed"].mean(), 1),
            "spin": int(g["release_spin_rate"].mean()) if g["release_spin_rate"].notna().any() else None,
            "whiff_pct": round(100 * g["description"].isin(WHIFF).sum() / sw, 1) if sw else None,
            "csw_pct": round(100 * (g["description"].isin(CALLED).sum() + g["description"].isin(WHIFF).sum()) / k, 1),
        })
    arsenal.sort(key=lambda a: -a["pct"])
    return {
        "pitches": n,
        "csw_pct": round(100 * (called + whiff) / n, 1),
        "swstr_pct": round(100 * whiff / n, 1),
        "whiff_pct": round(100 * whiff / swings, 1) if swings else None,
        "arsenal": arsenal,
    }


def fetch_pitchers_all():
    print("⚾ Fetching advanced pitching...")
    cfip, lg_era = league_fip_constant()
    print(f"  ℹ️  League ERA {lg_era}, FIP constant {cfip}")

    pitchers = [pitching_row(s) for s in player_stats("pitching")]
    # Real pitchers only: position players who threw an inning don't belong in FIP tables
    pitchers = [with_fip(p, cfip) for p in pitchers if p["outs"] >= 9]
    ids = [p["id"] for p in pitchers]

    xs = savant_expected(ids)
    for p in pitchers:
        p.update(xs.get(p["id"], {}))

    pitch_mix, failures = {}, 0
    for p in pitchers:
        if p["outs"] < 30:          # under 10 IP: too few pitches to say much
            continue
        try:
            pl = pitch_level(p["id"])
        except Exception as e:
            failures += 1
            print(f"    ⚠️  pitch data failed for {p['name']}: {e}")
            continue
        if pl:
            p.update({k: pl[k] for k in ("pitches", "csw_pct", "swstr_pct", "whiff_pct")})
            pitch_mix[p["name"]] = pl["arsenal"]
            print(f"    {p['name']}: {pl['pitches']} pitches, CSW {pl['csw_pct']}%")

    pitchers.sort(key=lambda p: (p["role"] != "SP", -p["outs"]))
    output = {
        "updated": date.today().isoformat(),
        "season": SEASON,
        "league": {"era": lg_era, "fip_constant": cfip},
        "pitchers": pitchers,
        "pitch_mix": pitch_mix,
        "sources": "MLB StatsAPI (counting stats, FIP), Baseball Savant (xERA, pitch-by-pitch)",
    }
    ok = len(pitchers) >= 8 and any("fip" in p for p in pitchers)
    save("pitchers.json", output, ok,
         f"{len(pitchers)} pitchers, {len(pitch_mix)} with pitch data, {failures} pitch-data failures")
    return output


if __name__ == "__main__":
    fetch_pitchers_all()
