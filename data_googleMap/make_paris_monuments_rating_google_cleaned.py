from __future__ import annotations

import re
import pandas as pd
from pathlib import Path

INPUT_FILES = [
    Path("./GoogleMap_Monument.csv"),
    Path("./GoogleMap_Museum.csv"),
    Path("./GoogleMap_TouristAttraction.csv"),
]

OUT_STEM = "paris_monuments_rating_google_cleaned"
OUT_DIR = Path("./")
OUT_CSV = OUT_DIR / f"{OUT_STEM}.csv"
OUT_JSON = OUT_DIR / f"{OUT_STEM}.json"


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def norm_text(s: pd.Series) -> pd.Series:
    # lowercase, trim, collapse whitespace; keep accents as-is (fine for matching)
    s = s.fillna("").astype(str).str.strip().str.lower()
    s = s.str.replace(r"\s+", " ", regex=True)
    return s


def main() -> None:
    missing = [str(p) for p in INPUT_FILES if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing input files:\n  - " + "\n  - ".join(missing))

    OUT_DIR.mkdir(parents=True, exist_ok=True)  # <-- added (optional but safe)

    frames = []
    for p in INPUT_FILES:
        df = pd.read_csv(p, dtype=str)

        # We’ll read these for dedupe; output will still be only 4 columns
        required_for_output = ["name", "rating", "review_count", "place_link"]
        for col in required_for_output:
            if col not in df.columns:
                raise ValueError(f"Missing column '{col}' in {p.name}")

        # Optional-but-helpful for dedupe:
        for col in ["place_id", "full_address"]:
            if col not in df.columns:
                df[col] = None

        df = df[["name", "rating", "review_count", "place_link", "place_id", "full_address"]].copy()

        # Clean numeric columns
        df["rating"] = to_numeric(df["rating"])
        df["review_count"] = to_numeric(df["review_count"]).round().astype("Int64")

        # Basic string cleaning
        df["name"] = df["name"].fillna("").astype(str).str.strip()
        df["place_link"] = df["place_link"].fillna("").astype(str).str.strip()
        df["place_id"] = df["place_id"].fillna("").astype(str).str.strip()
        df["full_address"] = df["full_address"].fillna("").astype(str).str.strip()

        frames.append(df)

    out = pd.concat(frames, ignore_index=True)

    # Drop rows missing essentials
    out = out[(out["name"] != "") & (out["place_link"] != "")]
    out = out.dropna(subset=["rating"])

    # Build a dedupe key with priority: place_id > place_link > (name+address)
    name_n = norm_text(out["name"])
    addr_n = norm_text(out["full_address"])
    link_n = norm_text(out["place_link"])
    pid_n = norm_text(out["place_id"])

    out["__dedupe_key"] = pd.Series("", index=out.index, dtype="string")
    out.loc[pid_n != "", "__dedupe_key"] = "pid:" + pid_n[pid_n != ""]
    out.loc[(pid_n == "") & (link_n != ""), "__dedupe_key"] = "link:" + link_n[(pid_n == "") & (link_n != "")]
    out.loc[(pid_n == "") & (link_n == ""), "__dedupe_key"] = "na:" + name_n[(pid_n == "") & (link_n == "")] + "|" + addr_n[(pid_n == "") & (link_n == "")]

    # If duplicates exist, keep the “best” row:
    # - highest review_count (more reliable)
    # - then highest rating
    out["__review_count_sort"] = out["review_count"].fillna(-1).astype("Int64")
    out = out.sort_values(by=["__dedupe_key", "__review_count_sort", "rating"], ascending=[True, False, False])

    out = out.drop_duplicates(subset=["__dedupe_key"], keep="first")

    # Final columns (exactly what you requested)
    out = out[["name", "rating", "review_count", "place_link"]].reset_index(drop=True)

    out.to_csv(OUT_CSV, index=False, encoding="utf-8")
    out.to_json(OUT_JSON, orient="records", force_ascii=False, indent=2)

    print(f"Wrote: {OUT_CSV} ({len(out)} unique places)")
    print(f"Wrote: {OUT_JSON} ({len(out)} unique places)")


if __name__ == "__main__":
    main()
