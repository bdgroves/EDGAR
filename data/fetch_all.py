"""
edgar/data/fetch_all.py
───────────────────────
Runs all five data fetchers in sequence.
Called by GitHub Actions every morning.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fetch_standings   import fetch_standings
from fetch_statcast    import fetch_statcast_all
from fetch_pitchers    import fetch_pitchers_all
from fetch_rainiers    import fetch_rainiers_all
from fetch_traditional import fetch_traditional_all


def main():
    print(f"\n{'='*50}")
    print(f"  EDGAR data fetch — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    results = {}

    try:
        results["standings"] = fetch_standings()
        print()
    except Exception as e:
        print(f"❌ Standings failed: {e}\n")

    try:
        results["traditional"] = fetch_traditional_all()
        print()
    except Exception as e:
        print(f"❌ Traditional stats failed: {e}\n")

    try:
        results["statcast"] = fetch_statcast_all()
        print()
    except Exception as e:
        print(f"❌ Statcast failed: {e}\n")

    try:
        results["pitchers"] = fetch_pitchers_all()
        print()
    except Exception as e:
        print(f"❌ Pitchers failed: {e}\n")

    try:
        results["rainiers"] = fetch_rainiers_all()
        print()
    except Exception as e:
        print(f"❌ Rainiers failed: {e}\n")

    print(f"{'='*50}")
    print(f"  ✅ Fetch complete — {len(results)}/5 modules succeeded")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
