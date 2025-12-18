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
     - **Selenium-based ratings (script)**: Scrapes ratings, review counts, opening hours, and websites.
     - **Official Places API (notebook)**: Higher-quality data collection (place details + reviews), with geospatial and fuzzy matching safeguards.
   - **Wikipedia enrichment**:
     - **Coordinate verification**: Extracts Wikipedia coordinates and verifies them against a reference.
     - **Content & Categorization**: Scrapes descriptions and infoboxes to categorize monuments (e.g., Museum, Church).

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


*Key dependencies include `selenium`, `webdriver-manager`, `deep-translator`, `google-generativeai`, `python-dotenv`. Optional enrichment dependencies include `googlemaps`, `thefuzz`, `tqdm`.*
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

* `monument_urls.txt` — Plain text list of URLs (backward compatibility)
* `monument_urls_with_coords.json` — Structured JSON with name, URL, latitude, and longitude
* `monument_urls_with_coords.csv` — CSV format with monument names and coordinates

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

After generating the cleaned dataset, you can enrich monuments with **Google Maps rating**, **review count**, and **opening hours** using the provided Selenium script.

### 6. Generate Google Ratings (scraping approach)

This script performs a detailed scrape of Google Maps. It handles cookie consent popups, expands opening hour accordions, and uses regex to strictly parse review counts (avoiding false matches like phone numbers).

It extracts:

* `rating` (stars)
* `review_count` (parsed from text like "1,234 reviews" or "(123)")
* `opening_hours` (full weekly schedule)
* `website` (official link from the Maps profile)
* `Maps_url` (the specific search/profile URL)

```bash
python generate_google_rating.py
```

**Input**: `merged_datasets/france_monuments.csv`

**Output**: `paris_monuments_ratings.csv`, `paris_monuments_ratings.json`

### Notes / Troubleshooting

* **Cookie Consent**: The script automatically attempts to click "Accept all" / "Tout accepter".
* **Rate Limiting**: Includes randomized sleep intervals (`2-4s`) to mimic human behavior.
* **Robustness**: Uses dummy domains to trigger Google Search redirects and handles both "List View" and "Detail View" result pages.

---

## Part 3: Wikipedia Enrichment (Coordinates & Content)

This section describes pipelines for enriching monument data using Wikipedia to retrieve coordinates, English descriptions, and categories.

### 7. Extract Wikipedia Coordinates (Part 3a)

Scrapes Wikipedia pages to extract geographic coordinates from the Kartographer map links.
```bash
python get_wiki_coords.py
```

**Input**: `paris_monuments_wiki.csv` (must contain a `wiki_url` column)

**Output**: `paris_monuments_wiki_with_coordinates.csv` (adds `lat` and `lon` columns)

### 8. Wikipedia Content & Category Extraction (Part 3b)

*New script logic.* This process attempts to find the Wikipedia page for each monument (checking English first, falling back to French) to extract descriptive content and classify the monument.

**Features:**

* **Cross-Lingual Search**: Checks English Wikipedia; if not found, checks French Wikipedia and translates content using `deep-translator`.
* **Categorization**: Analyzes the description and Infobox type to assign categories (e.g., *Museum, Church, Historic Site, Park*).
* **Redirect Logging**: Tracks if the search query redirected to a different page title in `redirect_log.txt`.

```bash
python extract_wiki_content.py

```

*(Note: Replace with the actual filename of the content extraction script provided)*

**Input**: `merged_datasets/france_monuments.csv`
**Output**: `paris_monuments_wiki.csv`, `paris_monuments_wiki.json`

### 9. Verify Coordinates Against Reference Dataset

Cross-validates Wikipedia coordinates by comparing them with a reference dataset using the Haversine distance formula.
```bash
python redirect_coord_verification.py
```

**Input**

* `paris_monuments_wiki_with_coordinates.csv`
* `merged_datasets/france_monuments_merged.csv` (reference dataset)
* `redirect_log.txt` (log of redirected Wikipedia pages)

**Output**: `paris_monuments_wiki_verified.csv` (adds `is_correct` boolean column)

### 10. LLM-Based Verification for Failed Matches
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

## Part 7: Comprehensive Database Creation & Analytics

This section integrates all collected data sources into a single relational SQLite database with proper schema design, foreign key relationships, and analytical views.

### Create Comprehensive Database

Merges data from multiple sources (National Monuments, Google Maps, Wikipedia, Foursquare) into a normalized relational database.

```bash
python create_database.py
```

**Input**:
- `merged_datasets/with_coords/with_google_map_url_city_opening_hour/france_monuments.csv`
- `merged_datasets/with_coords/with_google_map_url_city_opening_hour/google_maps_data_cleaned.csv`
- `merged_datasets/with_coords/with_google_map_url_city_opening_hour/google_maps_reviews_cleaned.csv`
- `paris_monuments_wiki_llm_verified.csv`
- `merged_datasets/Tourpedia_Foursquare_data.csv`
- `merged_datasets/Tourpedia_Foursquare_reviews.csv`

**Output**: `monuments_database.db`

**Database Tables Created**:
1. **`attraction`** - Main table with monument info (name, location, ratings, Wikipedia data)
2. **`national_monument`** - National monument-specific data (tickets, services, payment methods)
3. **`google_maps_metadata`** - Detailed Google Maps metadata (place_id, price_level, status)
4. **`google_reviews`** - Individual Google Maps reviews with ratings and text
5. **`foursquare_data`** - Foursquare engagement metrics (checkins, likes, tips)
6. **`foursquare_reviews`** - Foursquare reviews with sentiment analysis

**Key Features**:
- Proper foreign key relationships with referential integrity
- Merges Wikipedia descriptions and categories for verified monuments
- Links Google ratings and Foursquare engagement data
- Handles missing data gracefully with LEFT JOINs
- Deduplicates records to avoid conflicts

### Create Analytical Views

Generates pre-built SQL views for common analytical queries and data exploration.

```bash
python create_db_views.py
```

**Input**: `monuments_database.db`

**Output**: 5 analytical views added to the database

**Views Created**:

1. **`view_comprehensive_popularity`**
   - Combines Google votes and Foursquare checkins
   - Identifies "Megastar" monuments with highest total engagement

2. **`view_hidden_gems`**
   - High-rated monuments (≥4.5 stars) with low visibility (<500 votes)
   - Perfect for discovering underrated attractions

3. **`view_category_performance`**
   - Aggregates metrics by monument category
   - Shows average ratings, total votes, and checkins per category

4. **`view_price_vs_quality`**
   - Correlates Google price levels with ratings
   - Helps identify value-for-money attractions

5. **`view_national_monument_prestige`**
   - Focuses on official National Monuments
   - Shows ticket prices, services, and popularity metrics

### Database Quality Check

Performs comprehensive data quality analysis and generates visual reports as PNG images.

```bash
python db_quality_check.py
```

**Input**: `monuments_database.db`

**Output**: Multiple PNG reports in `qa_reports/` folder

**Quality Checks Performed**:

1. **Database Overview** (`00_db_overview.png`)
   - Row counts and column counts for each table

2. **Completeness Reports** (per table)
   - Missing value counts and percentages
   - Identifies data gaps that need attention

3. **Referential Integrity** (`integrity_check.png`)
   - Validates all foreign key relationships
   - Detects orphan records (PASS/FAIL status)

4. **Statistical Reports**
   - Distribution analysis for numeric fields (ratings, votes, coordinates)
   - Detects negative values and outliers
   - Summary statistics (mean, median, min, max, std)

5. **Categorical Distribution**
   - Top 15 monument categories by frequency
   - Price level distribution from Google Maps

**Dependencies**: Requires `matplotlib` for generating PNG visualizations.

---

## File Structure

**Core scripts**
- `get_monument_links.py`: Selenium script to harvest monument URLs and coordinates.
- `extract_monuments.py`: Selenium script to scrape detailed data for each monument.
- `clean_and_analyse_data.py`: Data cleaning script with regex parsing and quality reporting.
- `translate_dataset.py`: Script utilizing `google.generativeai` to translate content.

**Optional enrichment scripts**
- `generate_google_rating.py`: Selenium script to query Google Maps and extract rating + review count per monument.
- `get_wiki_coords.py`: Wikipedia coordinate extraction script using BeautifulSoup.
- `redirect_coord_verification.py`: Coordinate validation script using Haversine distance.
- `redirect_llm_verification.py`: LLM-based verification for ambiguous monument name matches.

**Database scripts**
- `create_database.py`: Comprehensive database creation script integrating multiple data sources.
- `create_db_views.py`: Script to generate analytical SQL views for common queries.
- `db_quality_check.py`: Data quality validation script with PNG report generation.

**Notebooks (project development / enrichment)**
- `merge.ipynb`: Tourpedia + Foursquare enrichment, deduplication, and merge with base dataset.
- `add_coords.ipynb`: Adds base coordinates to the merged dataset and runs Google-data QA checks.
- `google_maps.ipynb`: Official Google Places API enrichment, reconciliation, cleaning, and exports.

**Directories / artifacts**
- `html_samples/`: Sample HTML files used for testing or reference.
- `merged_datasets/`: Merged/enriched datasets and intermediate outputs (including Tourpedia and Google Places outputs).
- `Tourpedia/`: Tourpedia source extracts and cached outputs (details/reviews), if used.
- `qa_reports/`: Directory containing quality check reports as PNG images.

## Database Schema

The comprehensive SQLite database (`monuments_database.db`) contains a relational schema with the following tables:

### Core Tables

1. **`attraction`** (Main table)
   - `id` (PK), `name`, `url`, `opening_hours`, `address`, `city`, `category`
   - `lat`, `lng`, `description`, `wiki_url`
   - `google_rating`, `google_votes_count`, `website`, `phone`

2. **`national_monument`**
   - `id` (PK), `attraction_id` (FK → attraction.id)
   - `ticket_price`, `visiting_services`, `ticket_price_raw`
   - `advertising_title`, `price_conditions`, `payment_methods`

3. **`google_maps_metadata`**
   - `place_id` (PK), `monument_id` (FK → attraction.id)
   - `name`, `status`, `lat`, `lng`, `price_level`
   - `address`, `city`, `map_url`, `opening_hours`

4. **`google_reviews`**
   - `id` (PK), `place_id` (FK → google_maps_metadata.place_id)
   - `author_name`, `rating`, `text`, `language`
   - `original_language`, `timestamp`, `author_url`

5. **`foursquare_data`**
   - `Tourpedia_id` (PK), `monument_id` (FK → attraction.id)
   - `original_id`, `Foursquare_url`
   - `Foursquare_users_count`, `Foursquare_checkins_count`
   - `Foursquare_tip_count`, `Foursquare_likes`

6. **`foursquare_reviews`**
   - `id` (PK), `Tourpedia_id` (FK → foursquare_data.Tourpedia_id)
   - `language`, `polarity`, `text`, `time`
   - `words_count`, `tokenized_text_url`

### Analytical Views

- `view_comprehensive_popularity`: Combined engagement metrics
- `view_hidden_gems`: High-quality, low-visibility attractions
- `view_category_performance`: Aggregated stats by category
- `view_price_vs_quality`: Price level vs. rating analysis
- `view_national_monument_prestige`: National monument metrics

## License

This project is for educational purposes as part of the Data Acquisition course at Paris Dauphine University.
