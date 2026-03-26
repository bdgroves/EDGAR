"""
edgar/build_site.py
────────────────────
Copies data cache JSON files into docs/assets/data/
so GitHub Pages can serve them to the frontend.

Run after fetch_all.py to complete a full update cycle.
"""

import os
import shutil
import json
from datetime import datetime

DATA_DIR  = "data/cache"
ASSET_DIR = "docs/assets/data"


def build():
    os.makedirs(ASSET_DIR, exist_ok=True)

    files = ["standings.json", "statcast.json", "pitchers.json", "rainiers.json"]
    copied = 0

    for fname in files:
        src = os.path.join(DATA_DIR, fname)
        dst = os.path.join(ASSET_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            size = os.path.getsize(dst)
            print(f"  ✅ {fname} → {dst}  ({size:,} bytes)")
            copied += 1
        else:
            print(f"  ⚠️  {fname} not found in cache — skipping")

    # Write a build manifest
    manifest = {
        "built_at": datetime.utcnow().isoformat() + "Z",
        "files":    files,
        "copied":   copied,
    }
    with open(os.path.join(ASSET_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n🏗️  Site built — {copied}/{len(files)} data files ready")
    print(f"   → Push to GitHub to deploy: git push")


if __name__ == "__main__":
    build()
