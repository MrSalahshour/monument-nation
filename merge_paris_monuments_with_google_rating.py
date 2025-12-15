import re
import json
import unicodedata
from pathlib import Path

import pandas as pd

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except Exception:
    HAS_RAPIDFUZZ = False

not_found = []


# Paths
GOOGLE_CSV = Path("./data_googleMap/paris_monuments_rating_google_cleaned.csv")
FR_CSV     = Path("./paris_monuments_cleaned.csv")
EN_CSV     = Path("./paris_monuments_translated.csv")

OUT_CSV  = Path("./paris_monuments_merged.csv")
OUT_JSON = Path("./paris_monuments_merged.json")


# Normalization helpers
BILINGUAL_STOPWORDS = {
    # articles / prepositions
    "de", "du", "des", "d", "la", "le", "les", "l", "a", "au", "aux", "et", "en", "sur",
    "of", "the", "and", "in", "on", "at",
    # common attraction words
    "museum", "musée", "musee",
    "monument", "memorial", "mémorial", "memorial",
    "basilique", "basilica",
    "cathedrale", "cathédrale", "cathedral",
    "eglise", "église", "church",
    "chapelle", "chapel",
    "chateau", "château", "castle",
    "tour", "tower",
    "palais", "palace",
    "jardin", "gardens", "garden",
    "parc", "park",
    "pont", "bridge",
    "place", "square",
    "saint", "st",
}

def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def normalize_name(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = strip_accents(s)
    s = s.replace("&", " and ")
    # keep letters/numbers as tokens
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [t for t in s.split() if t and t not in BILINGUAL_STOPWORDS]
    return " ".join(toks)

def simple_token_similarity(a: str, b: str) -> float:
    """Fallback similarity if rapidfuzz isn't available."""
    A = set(normalize_name(a).split())
    B = set(normalize_name(b).split())
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


# Load data
df_g = pd.read_csv(GOOGLE_CSV, dtype=str).fillna("")
df_fr = pd.read_csv(FR_CSV, dtype=str).fillna("")
df_en = pd.read_csv(EN_CSV, dtype=str).fillna("")

# Make sure expected columns exist
for col in ["name", "rating", "review_count", "place_link"]:
    if col not in df_g.columns:
        raise ValueError(f"Google CSV missing required column: {col}")

for col in ["name", "url", "short_description", "ticket_price", "ticket_price_conditions",
            "opening_hours", "payment_methods", "address", "visiting_services", "ticket_price_raw"]:
    if col not in df_en.columns:
        raise ValueError(f"Translated CSV missing required column: {col}")


# Build alias names for each EN row using FR file (helps when EN name is different)
# Match EN<->FR primarily by url (most reliable), otherwise by exact name.
fr_by_url = {}
if "url" in df_fr.columns:
    fr_by_url = {u: n for u, n in zip(df_fr["url"], df_fr["name"]) if u}

fr_by_name = {n: n for n in df_fr.get("name", pd.Series([], dtype=str)).tolist()}

def get_aliases_for_en_row(row) -> list[str]:
    aliases = []
    en_name = row.get("name", "") or ""
    url = row.get("url", "") or ""
    if en_name:
        aliases.append(en_name)
    fr_name = fr_by_url.get(url, "")
    if fr_name:
        aliases.append(fr_name)
    # sometimes EN name equals FR name; also try FR exact-name lookup
    if en_name in fr_by_name and en_name not in aliases:
        aliases.append(fr_by_name[en_name])
    # return unique, keep order
    seen = set()
    out = []
    for a in aliases:
        if a and a not in seen:
            out.append(a)
            seen.add(a)
    return out


# Prepare Google index for fuzzy matching
g_names = df_g["name"].tolist()
g_norm = [normalize_name(x) for x in g_names]

# A quick exact dictionary on normalized name (fast path)
g_exact = {}
for i, nn in enumerate(g_norm):
    if nn and nn not in g_exact:
        g_exact[nn] = i

def find_best_google_match(aliases: list[str], min_score: float = 82.0):
    """
    Returns index in df_g or None.
    min_score is rapidfuzz score (0-100). With fallback similarity (0-1), threshold is adapted.
    """
    # 1) exact normalized match
    for a in aliases:
        nn = normalize_name(a)
        if nn and nn in g_exact:
            return g_exact[nn]

    # 2) fuzzy match (preferred)
    if HAS_RAPIDFUZZ:
        best_i = None
        best_score = -1.0
        for a in aliases:
            query = normalize_name(a)
            if not query:
                continue
            # match against normalized names, using token_set_ratio (handles reorder + partial overlap)
            match = process.extractOne(
                query,
                g_norm,
                scorer=fuzz.token_set_ratio
            )
            if match:
                _, score, idx = match
                if score > best_score:
                    best_score = score
                    best_i = idx
        if best_i is not None and best_score >= min_score:
            return best_i
        return None

    # 3) fallback (no rapidfuzz): token Jaccard on normalized tokens
    best_i = None
    best_score = -1.0
    for a in aliases:
        for i, gn in enumerate(g_names):
            score = simple_token_similarity(a, gn)  # 0..1
            if score > best_score:
                best_score = score
                best_i = i
    return best_i if best_score >= 0.60 else None


# Merge: iterate EN rows, attach Google fields (or empty if not found)
google_rating = []
google_review_count = []
place_link_google_map = []

for _, row in df_en.iterrows():
    aliases = get_aliases_for_en_row(row)
    gi = find_best_google_match(aliases)

    if gi is None:
        # collect + print one line
        name = row.get("name", "")
        url = row.get("url", "")
        print(f"NOT_FOUND: {name} | {url}")
        not_found.append({"name": name, "url": url})

        google_rating.append("")
        google_review_count.append("")
        place_link_google_map.append("")
    else:
        google_rating.append(df_g.at[gi, "rating"])
        google_review_count.append(df_g.at[gi, "review_count"])
        place_link_google_map.append(df_g.at[gi, "place_link"])

df_out = df_en.copy()
df_out["google_rating"] = google_rating
df_out["google_review_count"] = google_review_count
df_out["place_link_google_map"] = place_link_google_map

# Enforce final column order exactly as requested
final_cols = [
    "name",
    "url",
    "short_description",
    "ticket_price",
    "ticket_price_conditions",
    "opening_hours",
    "payment_methods",
    "address",
    "visiting_services",
    "ticket_price_raw",
    "google_rating",
    "google_review_count",
    "place_link_google_map",
]
# Create any missing columns as empty (just in case)
for c in final_cols:
    if c not in df_out.columns:
        df_out[c] = ""
df_out = df_out[final_cols]

# Write outputs (CSV + JSON with identical records)
df_out.to_csv(OUT_CSV, index=False, encoding="utf-8")

records = df_out.to_dict(orient="records")
OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Wrote:\n- {OUT_CSV}\n- {OUT_JSON}")
print(f"RapidFuzz enabled: {HAS_RAPIDFUZZ}")
