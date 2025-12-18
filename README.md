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

### 5. Create Database

Creates a SQLite database with a normalized schema (separating payment methods) and inserts the translated data.

```bash
python create_database.py
```

* **Output**: `paris_monuments.db`

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

## File Structure

* `get_monument_links.py`: Selenium script to harvest monument URLs and coordinates.
* `extract_monuments.py`: Selenium script to scrape detailed data for each monument.
* `clean_and_analyse_data.py`: Data cleaning script with regex parsing and quality reporting.
* `translate_dataset.py`: Script utilizing `google.generativeai` to translate content.
* `create_database.py`: SQLite script to create tables (`monuments`, `payment_methods`) and insert data.
* `generate_google_rating.py`: Selenium script to query Google Maps and extract rating + review count per monument.
* `get_wiki_coords.py`: Wikipedia coordinate extraction script using BeautifulSoup.
* `redirect_coord_verification.py`: Coordinate validation script using Haversine distance.
* `redirect_llm_verification.py`: LLM-based verification for ambiguous monument name matches.
* `requirements.txt`: List of Python dependencies.
* `html_samples/`: Directory containing sample HTML files used for testing or reference.
* `merged_datasets/`: Directory containing reference datasets for coordinate verification.

## Database Schema

The final SQLite database (`paris_monuments.db`) contains two main tables:

1. **`monuments`**:

   * `id`, `name`, `url`, `short_description`, `address`, `opening_hours`, `ticket_price`, `ticket_price_conditions`, `visiting_services`.
2. **`payment_methods`**:

   * `id`, `monument_id`, `method` (Normalized payment method names).

## License

This project is for educational purposes as part of the Data Acquisition course at Paris Dauphine University.