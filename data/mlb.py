"""
edgar/data/mlb.py
─────────────────
Shared helpers for the fetchers.

- get(): MLB StatsAPI over plain requests (the endpoints are public and
  documented by use; going direct avoids the statsapi wrapper hiding fields).
- save(): writes a cache file ONLY when the payload passes its check.
  data/cache/ starts empty on every Actions run and build_site.py copies only
  files that exist, so a failed or empty fetch leaves yesterday's published
  file in place instead of blanking the dashboard. (pitchers.json sat empty
  from April to October 2026 because the old code saved whatever it got.)
- every save() also records a line in health.json so the page can say what
  is fresh and what is stale.
"""

import json
import math
import os
import sys
from datetime import date, datetime, timezone

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DATA_DIR

API = "https://statsapi.mlb.com/api/v1"
_session = requests.Session()
_session.headers["User-Agent"] = "EDGAR dashboard (github.com/bdgroves/EDGAR)"
HEALTH = {}


def get(path, **params):
    r = _session.get(API + path, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def num(v, decimals=None):
    """StatsAPI sends rates as strings ('.281', '-.---'). None when not a number."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, decimals) if decimals is not None else f


def integer(v):
    f = num(v)
    return int(f) if f is not None else None


def ip_to_outs(ip):
    """'36.2' innings = 36 innings and 2 outs = 110 outs."""
    if ip in (None, ""):
        return 0
    whole, _, frac = str(ip).partition(".")
    return int(whole or 0) * 3 + int(frac or 0)


def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def save(name, payload, ok, detail=""):
    """Write data/cache/<name> only if ok. Records the outcome in HEALTH."""
    HEALTH[name] = {"ok": bool(ok), "detail": detail,
                    "checked": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if not ok:
        print(f"  ⚠️  {name}: check failed ({detail}) — keeping the published copy")
        print(f"::warning::EDGAR {name} not updated: {detail}")
        return False
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = sanitize(payload)
    payload.setdefault("updated", date.today().isoformat())
    with open(os.path.join(DATA_DIR, name), "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {name} saved ({detail})")
    return True


def write_health():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "health.json"), "w") as f:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "modules": HEALTH}, f, indent=2)
