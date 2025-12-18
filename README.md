# Paris Monuments Data Pipeline

This project is a comprehensive data acquisition and processing pipeline designed to scrape, clean, translate, enrich, and store information about national monuments in Paris/France from the [Centre des monuments nationaux](https://www.monuments-nationaux.fr/) website, and to optionally extend the dataset using external sources (Tourpedia/Foursquare, Google Maps, Wikipedia).

## Project Overview

The pipeline covers these major steps:

1. **Scraping (CMN)**: Collects URLs of monuments and extracts detailed fields (description, prices, opening hours, services, etc.) using Selenium.
2. **Cleaning**: Standardizes raw fields, handles missing values, and formats structured columns (prices, lists, hours).
3. **Translation**: Translates descriptive fields from French to English using the Google Gemini API.
4. **Storage**: Normalizes the data (e.g., payment methods) and stores it in a relational SQLite database.
5. **Optional enrichments**:
   - **Tourpedia + Foursquare extension (notebook)**: Builds a Paris attractions subset from Tourpedia, fetches details/reviews, deduplicates, and merges with the base dataset.
   - **Google Maps enrichment**:
     - **Selenium-based ratings (script)**: Lightweight retrieval of rating/review count.
     - **Official Places API (notebook)**: Higher-quality data collection (place details + reviews), with geospatial and fuzzy matching safeguards.
   - **Wikipedia coordinate enrichment & verification (scripts)**: Extracts Wikipedia coordinates and verifies them against a reference dataset.

## Prerequisites

- **Python 3.8+**
- **Google Chrome** (for Selenium-based steps)
- **Gemini API Key** (translation and optional LLM verification)
- **Optional: Google Maps Places API Key** (for official Google Places enrichment via `googlemaps`)
  - Note: Requires an enabled Google Cloud project with Places API and billing.

## Installation

1. **Clone the repository** (if applicable) or navigate to the project folder.

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Key dependencies include `selenium`, `webdriver-manager`, `google-generativeai`, `python-dotenv`. Optional enrichment dependencies include `googlemaps`, `thefuzz`, `tqdm`.*

4. **Environment Configuration**:
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   # Optional (Places API workflow in google_maps.ipynb)
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   ```

## Usage Pipeline

Run the scripts in the following order to execute the base CMN pipeline. Optional enrichments can be run after step 4.

### 1. Collect Monument Links
Scrapes the main listing page to gather URLs for all available monuments along with their geographic coordinates.
```bash
python get_monument_links.py
```

**Output**
- `monument_urls.txt` — Plain text list of URLs (backward compatibility)
- `monument_urls_with_coords.json` — Structured JSON with name, URL, latitude, and longitude
- `monument_urls_with_coords.csv` — CSV format with monument names and coordinates

### 2. Extract Monument Details
Visits each URL found in the previous step to scrape detailed information (prices, hours, address, etc.).
```bash
python extract_monuments.py
```

**Output**: `paris_monuments_data.json`

### 3. Clean and Analyze Data
Processes the raw JSON data to fix formatting issues, handle missing values, and standardize price fields. It also generates a quality report.
```bash
python clean_and_analyse_data.py
```

**Output**: `paris_monuments_cleaned.json`, `paris_monuments_cleaned.csv`

### 4. Translate Dataset
Uses the Gemini API to translate descriptions, opening hours, and conditions from French to English.
```bash
python translate_dataset.py
```

**Output**: `paris_monuments_translated.json`, `paris_monuments_translated.csv`

### 5. Create Database
Creates a SQLite database with a normalized schema (separating payment methods) and inserts the translated data.
```bash
python create_database.py
```

**Output**: `paris_monuments.db`

---

## Part 2: Google Maps Ratings Enrichment (Selenium)

After generating the cleaned dataset, you can enrich monuments with **Google Maps rating** and **review count** using `generate_google_rating.py`.

### 6. Generate Google Ratings (scraping approach)

This script:
- Loads the cleaned dataset (`paris_monuments_cleaned.csv` by default)
- Searches each monument name on Google Maps
- Extracts:
  - `rating` (stars)
  - `review_count`
  - `google_maps_url` (the search URL used)
- Saves progress periodically

```bash
python generate_google_rating.py
```

**Input**: `paris_monuments_cleaned.csv`  
**Output**: `paris_monuments_ratings.csv`, `paris_monuments_ratings.json`

### Notes / Troubleshooting
- If Google’s cookie consent banner appears, the script attempts to click **“Accept all”** automatically.
- The crawler includes basic rate limiting (`~1.5–3s` sleep). If you get blocked/captchas, slow it down further or run with a visible browser window.

> **Project note**: In subsequent notebook-based validation (see `add_coords.ipynb`), this scraping approach showed significant location mismatch issues. For higher-quality joins, prefer the **official Places API workflow** in `google_maps.ipynb`.

---

## Part 3: Wikipedia Coordinate Enrichment & Verification

This section describes an optional pipeline for enriching monument data with Wikipedia coordinates and verifying their accuracy.

### 7. Extract Wikipedia Coordinates
Scrapes Wikipedia pages to extract geographic coordinates from the Kartographer map links.
```bash
python get_wiki_coords.py
```

**Input**: `paris_monuments_wiki.csv` (must contain a `wiki_url` column)  
**Output**: `paris_monuments_wiki_with_coordinates.csv` (adds `lat` and `lon` columns)

### 8. Verify Coordinates Against Reference Dataset
Cross-validates Wikipedia coordinates by comparing them with a reference dataset using the Haversine distance formula.
```bash
python redirect_coord_verification.py
```

**Input**
- `paris_monuments_wiki_with_coordinates.csv`
- `merged_datasets/france_monuments_merged.csv` (reference dataset)
- `redirect_log.txt` (log of redirected Wikipedia pages)

**Output**: `paris_monuments_wiki_verified.csv` (adds `is_correct` boolean column)

### 9. LLM-Based Verification for Failed Matches
Uses Google Gemini to verify whether “failed” matches refer to the same place despite name variations.
```bash
python redirect_llm_verification.py
```

**Input**: `paris_monuments_wiki_verified.csv`  
**Output**: `paris_monuments_wiki_llm_verified.csv`  
**Requires**: `GEMINI_API_KEY` in `.env`

---

## Part 4: Tourpedia + Foursquare Extension (Notebooks)

The notebook `merge.ipynb` extends the base dataset using **Tourpedia Paris attractions** and associated **Foursquare-derived metadata and reviews**.

### What `merge.ipynb` does
- Loads Tourpedia Paris attractions and filters to a curated set of relevant `subCategory` values aligned with monuments/landmarks.
- Calls Tourpedia **details** and **reviews** endpoints to build:
  - an enriched POI table (descriptions, website, polarity, Foursquare stats like users/checkins/tips/likes),
  - and a review-level table (language, polarity, timestamp, word count, tokenized/details URL).
- Runs consistency checks (e.g., `numReviews` vs. observed review counts; polarity aggregation vs. stored polarity).
- Deduplicates Tourpedia POIs using normalization + fuzzy matching and geospatial constraints, followed by an AI-assisted/manual adjudication step for ambiguous duplicates.
- Links Tourpedia POIs to the base dataset and produces a merged monuments dataset.

### Expected outputs
Depending on whether the final “save” cells are enabled, the notebook is designed to export:
- `merged_datasets/france_monuments.csv` — base dataset extended with Tourpedia records/fields
- `merged_datasets/Tourpedia_Foursquare_data.csv` — Tourpedia↔Foursquare stats table
- `merged_datasets/Tourpedia_Foursquare_reviews.csv` — Tourpedia review table

---

## Part 5: Coordinate Consolidation & Google Data QA (Notebook)

The notebook `add_coords.ipynb` consolidates coordinates into the merged dataset and performs quality checks before Google Maps enrichment.

### What `add_coords.ipynb` does
- Adds `lat/lng` to the merged monuments dataset by joining on URL using `monument_urls_with_coords.csv`.
- Performs merge-safety checks (URL overlap/uniqueness, repeated URLs).
- Loads the scraped Google Maps ratings dataset (`paris_monuments_ratings.csv`) and evaluates join quality:
  - URL-domain agreement between datasets,
  - coordinate agreement by extracting `@lat,lng` from Google Maps URLs and measuring Haversine distance to reference coordinates.
- Stops before merging when quality is insufficient and recommends recollecting via the official Places API.

---

## Part 6: Official Google Places Enrichment & Cleaning (Notebook)

The notebook `google_maps.ipynb` implements a more reliable Google Maps enrichment workflow using the **official Places API** (`googlemaps` client).

### What `google_maps.ipynb` does
- Uses a **two-step** process for each monument:
  1) `find_place` (text query with location bias) to get `place_id`
  2) `place` details to fetch rich fields, including coordinates, website, map URL, rating/vote count, opening hours, and top reviews
- Caches raw API responses to JSON for repeatable runs.
- Builds two normalized outputs:
  - `df_google_data` (place-level)
  - `df_google_reviews` (review-level, linked by `place_id`)
- Reconciles and fills missing base fields using strict geospatial thresholds:
  - **City** replaced when Google coordinates are within **500 m**
  - **URL + opening hours** filled when within **100 m** (high-confidence identity)
- Adds a fuzzy-matching fallback for URL similarity (normalized URL/domain gates + token overlap + `token_set_ratio`).
- Produces cleaned Google outputs by filtering to “good matches” (distance < 100 m OR similarity above threshold).

### Outputs written by the notebook
- Updated monuments dataset:
  - `merged_datasets/with_coords/with_google_map_url_city_opening_hour/france_monuments.csv`
- Cleaned Google places and reviews:
  - `merged_datasets/with_coords/with_google_map_url_city_opening_hour/google_maps_data_cleaned.csv`
  - `merged_datasets/with_coords/with_google_map_url_city_opening_hour/google_maps_reviews_cleaned.csv`

---

## File Structure

**Core scripts**
- `get_monument_links.py`: Selenium script to harvest monument URLs and coordinates.
- `extract_monuments.py`: Selenium script to scrape detailed data for each monument.
- `clean_and_analyse_data.py`: Data cleaning script with regex parsing and quality reporting.
- `translate_dataset.py`: Script utilizing `google.generativeai` to translate content.
- `create_database.py`: SQLite script to create tables (`monuments`, `payment_methods`) and insert data.

**Optional enrichment scripts**
- `generate_google_rating.py`: Selenium script to query Google Maps and extract rating + review count per monument.
- `get_wiki_coords.py`: Wikipedia coordinate extraction script using BeautifulSoup.
- `redirect_coord_verification.py`: Coordinate validation script using Haversine distance.
- `redirect_llm_verification.py`: LLM-based verification for ambiguous monument name matches.

**Notebooks (project development / enrichment)**
- `merge.ipynb`: Tourpedia + Foursquare enrichment, deduplication, and merge with base dataset.
- `add_coords.ipynb`: Adds base coordinates to the merged dataset and runs Google-data QA checks.
- `google_maps.ipynb`: Official Google Places API enrichment, reconciliation, cleaning, and exports.

**Directories / artifacts**
- `html_samples/`: Sample HTML files used for testing or reference.
- `merged_datasets/`: Merged/enriched datasets and intermediate outputs (including Tourpedia and Google Places outputs).
- `Tourpedia/`: Tourpedia source extracts and cached outputs (details/reviews), if used.

## Database Schema

The final SQLite database (`paris_monuments.db`) contains two main tables:

1. **`monuments`**
   - `id`, `name`, `url`, `short_description`, `address`, `opening_hours`, `ticket_price`, `ticket_price_conditions`, `visiting_services`.

2. **`payment_methods`**
   - `id`, `monument_id`, `method` (normalized payment method names).

## License

This project is for educational purposes as part of the Data Acquisition course at Paris Dauphine University.
