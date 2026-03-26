# edgar/config.py
# Central config for the EDGAR project

# ── Team identifiers ──────────────────────────────────────────────
MARINERS_ID       = 136          # MLB StatsAPI team ID
MARINERS_ABBREV   = "SEA"        # pybaseball / Statcast abbreviation
TACOMA_ID         = 6047         # MiLB team ID (Tacoma Rainiers, Triple-A West/PCL)
TACOMA_ABBREV     = "TAC"

# ── AL West competitors ───────────────────────────────────────────
AL_WEST = {
    "SEA": {"name": "Mariners",  "id": 136, "color": "#005C5C"},
    "HOU": {"name": "Astros",    "id": 117, "color": "#EB6E1F"},
    "TEX": {"name": "Rangers",   "id": 140, "color": "#003278"},
    "LAA": {"name": "Angels",    "id": 108, "color": "#BA0021"},
    "OAK": {"name": "Athletics", "id": 133, "color": "#003831"},
}

# ── Mariners brand colors ─────────────────────────────────────────
COLORS = {
    "navy":      "#0C2340",
    "teal":      "#005C5C",
    "silver":    "#C4CED4",
    "white":     "#FFFFFF",
    "gold":      "#C0922B",   # subtle accent
    "bg_dark":   "#080F1A",
    "bg_card":   "#0D1E30",
    "text_dim":  "#7A94A8",
}

# ── Season ────────────────────────────────────────────────────────
SEASON = 2026

# ── Output paths ─────────────────────────────────────────────────
DATA_DIR  = "data/cache"
DOCS_DIR  = "docs"
ASSET_DIR = "docs/assets"
