# Paris Monuments Data Pipeline

This project is a comprehensive data acquisition and processing pipeline designed to scrape, clean, translate, and store information about national monuments in Paris and France from the [Centre des monuments nationaux](https://www.monuments-nationaux.fr/) website.

## Project Overview

The pipeline performs the following steps:
1.  **Scraping**: Collects URLs of all monuments and extracts detailed information (description, prices, opening hours, services, etc.) using Selenium.
2.  **Cleaning**: Standardizes the raw data, handles missing values, and formats fields like prices and lists.
3.  **Translation**: Translates descriptive fields from French to English using the Google Gemini API.
4.  **Storage**: Normalizes the data (specifically payment methods) and stores it in a relational SQLite database.
5.  **Google Ratings Enrichment**: Queries Google Maps for each monument name to retrieve a public rating and review count, and exports the results as CSV/JSON.

## Prerequisites

*   **Python 3.8+**
*   **Google Chrome**: Required for Selenium automation.
*   **Gemini API Key**: Required for the translation step.

## Installation

1.  **Clone the repository** (if applicable) or navigate to the project folder.

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Key dependencies include `selenium`, `webdriver-manager`, `google-generativeai`, and `python-dotenv`.*

4.  **Environment Configuration**:
    Create a `.env` file in the root directory and add your Gemini API key:
    ```env
    GEMINI_API_KEY=your_api_key_here
    ```

## Usage Pipeline

Run the scripts in the following order to execute the full pipeline.

### 1. Collect Monument Links
Scrapes the main listing page to gather URLs for all available monuments along with their geographic coordinates.
```bash
python get_monument_links.py
```

* **Output**: 
  * `monument_urls.txt` - Plain text list of URLs (backward compatibility)
  * `monument_urls_with_coords.json` - Structured JSON with name, URL, latitude, and longitude
  * `monument_urls_with_coords.csv` - CSV format with monument names and coordinates

### 2. Extract Monument Details

Visits each URL found in the previous step to scrape detailed information (prices, hours, address, etc.).

```bash
python extract_monuments.py
```

* **Output**: `paris_monuments_data.json`

### 3. Clean and Analyze Data

Processes the raw JSON data to fix formatting issues, handle missing values, and standardize price fields. It also generates a quality report.

```bash
python clean_and_analyse_data.py
```

* **Output**: `paris_monuments_cleaned.json`, `paris_monuments_cleaned.csv`

### 4. Translate Dataset

Uses the Gemini API to translate descriptions, opening hours, and conditions from French to English.

```bash
python translate_dataset.py
```

* **Output**: `paris_monuments_translated.json`, `paris_monuments_translated.csv`

---

## Part 2: Google Maps Ratings Enrichment

After generating the cleaned dataset, you can enrich the monuments with **Google Maps rating** and **review count** by running `generate_google_rating.py`.

### 6. Generate Google Ratings

This script:

* Loads the cleaned dataset (`paris_monuments_cleaned.csv` by default)
* Searches each monument name on Google Maps
* Extracts:

  * `rating` (stars)
  * `review_count`
  * `google_maps_url` (the search URL used)
* Saves progress periodically (checkpoint every 10 rows)

```bash
python generate_google_rating.py
```

* **Input**: `paris_monuments_cleaned.csv`
* **Output**: `paris_monuments_ratings.csv`, `paris_monuments_ratings.json`

### Notes / Troubleshooting

* If Google’s cookie consent banner appears, the script attempts to click **“Accept all”** automatically.
* The crawler includes basic rate limiting (`~1.5–3s` sleep between queries). If you get blocked or see captchas, slow it down further or run with a visible browser window.
* To run without opening a browser UI, uncomment the headless option in the script:

  ```python
  # chrome_options.add_argument("--headless")
  ```

---

## Part 3: Wikipedia Coordinate Enrichment & Verification

This section describes an optional pipeline for enriching monument data with Wikipedia coordinates and verifying their accuracy.

### 7. Extract Wikipedia Coordinates

Scrapes Wikipedia pages to extract geographic coordinates from the Kartographer map links.

```bash
python get_wiki_coords.py
```

* **Input**: `paris_monuments_wiki.csv` (must contain a `wiki_url` column)
* **Output**: `paris_monuments_wiki_with_coordinates.csv` (adds `lat` and `lon` columns)
* **Features**:
  * Extracts coordinates from `data-lat` and `data-lon` attributes in Wikipedia's coordinate span
  * Includes rate limiting (0.5s delay between requests) to respect Wikipedia's servers
  * Provides progress updates and success rate statistics

### 8. Verify Coordinates Against Reference Dataset

Cross-validates Wikipedia coordinates by comparing them with a reference dataset using the Haversine distance formula.

```bash
python redirect_coord_verification.py
```

* **Input**: 
  * `paris_monuments_wiki_with_coordinates.csv` (Wikipedia data with coordinates)
  * `merged_datasets/france_monuments_merged.csv` (reference dataset)
  * `redirect_log.txt` (log of redirected Wikipedia pages)
* **Output**: `paris_monuments_wiki_verified.csv` (adds `is_correct` boolean column)
* **Logic**:
  * Non-redirected pages: Assumed correct (marked `True`)
  * Redirected pages: Verified by checking if coordinates are within 2km of reference data
  * Missing coordinates or reference data: Marked `False`

### 9. LLM-Based Verification for Failed Matches

Uses Google Gemini to verify if monument names that failed coordinate verification actually refer to the same place.

```bash
python redirect_llm_verification.py
```

* **Input**: `paris_monuments_wiki_verified.csv`
* **Output**: `paris_monuments_wiki_llm_verified.csv`
* **Features**:
  * Only processes rows marked `False` with missing coordinates
  * Uses LLM to compare input name vs. Wikipedia name considering description and category
  * Includes automatic rate limiting (4s between requests, 15 requests/min)
  * Recovers valid matches that were incorrectly flagged due to name variations

**Note**: Requires `GEMINI_API_KEY` in your `.env` file.

---

## Part 4: Comprehensive Database Creation & Analytics

This section integrates all collected data sources into a single relational SQLite database with proper schema design, foreign key relationships, and analytical views.

### 10. Create Comprehensive Database

Merges data from multiple sources (National Monuments, Google Maps, Wikipedia, Foursquare) into a normalized relational database.

```bash
python create_database.py
```

* **Input**:
  * `merged_datasets/with_coords/with_google_map_url_city_opening_hour/france_monuments.csv`
  * `merged_datasets/with_coords/with_google_map_url_city_opening_hour/google_maps_data_cleaned.csv`
  * `merged_datasets/with_coords/with_google_map_url_city_opening_hour/google_maps_reviews_cleaned.csv`
  * `paris_monuments_wiki_llm_verified.csv`
  * `merged_datasets/Tourpedia_Foursquare_data.csv`
  * `merged_datasets/Tourpedia_Foursquare_reviews.csv`
* **Output**: `monuments_database.db`

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

### 11. Create Analytical Views

Generates pre-built SQL views for common analytical queries and data exploration.

```bash
python create_db_views.py
```

* **Input**: `monuments_database.db`
* **Output**: 5 analytical views added to the database

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

### 12. Database Quality Check

Performs comprehensive data quality analysis and generates visual reports as PNG images.

```bash
python db_quality_check.py
```

* **Input**: `monuments_database.db`
* **Output**: Multiple PNG reports in `qa_reports/` folder

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

* `get_monument_links.py`: Selenium script to harvest monument URLs and coordinates.
* `extract_monuments.py`: Selenium script to scrape detailed data for each monument.
* `clean_and_analyse_data.py`: Data cleaning script with regex parsing and quality reporting.
* `translate_dataset.py`: Script utilizing `google.generativeai` to translate content.
* `generate_google_rating.py`: Selenium script to query Google Maps and extract rating + review count per monument.
* `get_wiki_coords.py`: Wikipedia coordinate extraction script using BeautifulSoup.
* `redirect_coord_verification.py`: Coordinate validation script using Haversine distance.
* `redirect_llm_verification.py`: LLM-based verification for ambiguous monument name matches.
* `create_database.py`: Comprehensive database creation script integrating multiple data sources.
* `create_db_views.py`: Script to generate analytical SQL views for common queries.
* `db_quality_check.py`: Data quality validation script with PNG report generation.
* `requirements.txt`: List of Python dependencies.
* `html_samples/`: Directory containing sample HTML files used for testing or reference.
* `merged_datasets/`: Directory containing reference datasets and merged data from multiple sources.
* `qa_reports/`: Directory containing quality check reports as PNG images.

## Database Schema

The final SQLite database (`monuments_database.db`) contains a comprehensive relational schema with the following tables:

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