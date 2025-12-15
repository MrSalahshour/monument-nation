from __future__ import annotations

import pandas as pd
from pathlib import Path

INPUT_FILES = [
    Path("./data_googleMap/GoogleMap_Monument.csv"),
    Path("./data_googleMap/GoogleMap_Museum.csv"),
    Path("./data_googleMap/GoogleMap_TouristAttraction.csv"),
]

OUT_STEM = "paris_monuments_rating_google_cleaned"
OUT_CSV = Path(f"{OUT_STEM}.csv")
OUT_JSON = Path(f"{OUT_STEM}.json")


def to_numeric(series: pd.Series) -> pd.Series:
    # Convert to numeric safely; invalid -> NaN
    return pd.to_numeric(series, errors="coerce")


def main() -> None:
    missing = [str(p) for p in INPUT_FILES if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "These input files were not found:\n  - " + "\n  - ".join(missing)
        )

    frames = []
    for p in INPUT_FILES:
        df = pd.read_csv(p, dtype=str)

        # Keep only the columns we need
        needed = ["name", "rating", "review_count", "place_link"]
        for col in needed:
            if col not in df.columns:
                raise ValueError(f"Missing column '{col}' in {p.name}")

        df = df[needed].copy()

        # Clean types
        df["rating"] = to_numeric(df["rating"])
        df["review_count"] = to_numeric(df["review_count"])

        # Keep review_count as nullable integer when possible
        df["review_count"] = df["review_count"].round().astype("Int64")

        frames.append(df)

    out = pd.concat(frames, ignore_index=True)

    # Basic cleaning
    out["name"] = out["name"].astype(str).str.strip()
    out["place_link"] = out["place_link"].astype(str).str.strip()

    # Drop rows missing essentials
    out = out[(out["name"] != "") & (out["place_link"] != "")]
    out = out.dropna(subset=["rating"])  # rating is essential

    # Remove exact duplicates (same name + link)
    out = out.drop_duplicates(subset=["name", "place_link"], keep="first")

    # Final column order
    out = out[["name", "rating", "review_count", "place_link"]].reset_index(drop=True)

    # Write CSV
    out.to_csv(OUT_CSV, index=False, encoding="utf-8")

    # Write JSON (same data, just different format)
    # records -> list of objects; nulls preserved for missing review_count
    out.to_json(OUT_JSON, orient="records", force_ascii=False, indent=2)

    print(f"Wrote: {OUT_CSV} ({len(out)} rows)")
    print(f"Wrote: {OUT_JSON} ({len(out)} records)")


if __name__ == "__main__":
    main()
