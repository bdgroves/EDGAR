"""
edgar/build_site.py
────────────────────
Copies data cache JSON files into docs/assets/data/
so GitHub Pages can serve them to the frontend.
"""

import os
import shutil
from datetime import datetime, timezone

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATA_DIR, ASSET_DIR


def build():
    os.makedirs(ASSET_DIR, exist_ok=True)

    files = [
        "standings.json",
        "traditional.json",
        "statcast.json",
        "pitchers.json",
        "rainiers.json",
    ]
    copied = 0

    print(f"\n🏗️  Building site...")
    print(f"   Source:  {DATA_DIR}")
    print(f"   Output:  {ASSET_DIR}\n")

    for fname in files:
        src = os.path.join(DATA_DIR, fname)
        dst = os.path.join(ASSET_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            size = os.path.getsize(dst)
            print(f"  ✅ {fname} ({size:,} bytes)")
            copied += 1
        else:
            print(f"  ⚠️  {fname} not found in cache — skipping")

    print(f"\n  {copied}/{len(files)} data files deployed to docs/assets/data/")
    print(f"  → git add . && git commit -m 'data: update' && git push\n")


if __name__ == "__main__":
    build()
