# Paris Monuments Data Pipeline

This project is a comprehensive data acquisition and processing pipeline designed to scrape, clean, translate, and store information about national monuments in Paris and France from the [Centre des monuments nationaux](https://www.monuments-nationaux.fr/) website.

## Project Overview

The pipeline performs the following steps:
1.  **Scraping**: Collects URLs of all monuments and extracts detailed information (description, prices, opening hours, services, etc.) using Selenium.
2.  **Cleaning**: Standardizes the raw data, handles missing values, and formats fields like prices and lists.
3.  **Translation**: Translates descriptive fields from French to English using the Google Gemini API.
4.  **Storage**: Normalizes the data (specifically payment methods) and stores it in a relational SQLite database.

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
Scrapes the main listing page to gather URLs for all available monuments.
```bash
python get_monument_links.py
```
*   **Output**: `monument_urls.txt`

### 2. Extract Monument Details
Visits each URL found in the previous step to scrape detailed information (prices, hours, address, etc.).
```bash
python extract_monuments.py
```
*   **Output**: `paris_monuments_data.json`

### 3. Clean and Analyze Data
Processes the raw JSON data to fix formatting issues, handle missing values, and standardize price fields. It also generates a quality report.
```bash
python clean_and_analyse_data.py
```
*   **Output**: `paris_monuments_cleaned.json`, `paris_monuments_cleaned.csv`

### 4. Translate Dataset
Uses the Gemini API to translate descriptions, opening hours, and conditions from French to English.
```bash
python translate_dataset.py
```
*   **Output**: `paris_monuments_translated.json`, `paris_monuments_translated.csv`

### 5. Create Database
Creates a SQLite database with a normalized schema (separating payment methods) and inserts the translated data.
```bash
python create_database.py
```
*   **Output**: `paris_monuments.db`

## File Structure

*   `get_monument_links.py`: Selenium script to harvest monument URLs.
*   `extract_monuments.py`: Selenium script to scrape detailed data for each monument.
*   `clean_and_analyse_data.py`: Data cleaning script with regex parsing and quality reporting.
*   `translate_dataset.py`: Script utilizing `google.generativeai` to translate content.
*   `create_database.py`: SQLite script to create tables (`monuments`, `payment_methods`) and insert data.
*   `requirements.txt`: List of Python dependencies.
*   `html_samples/`: Directory containing sample HTML files used for testing or reference.
*   `wikipedia/`: Directory containing supplementary Wikipedia data scripts.

## Database Schema

The final SQLite database (`paris_monuments.db`) contains two main tables:

1.  **`monuments`**:
    *   `id`, `name`, `url`, `short_description`, `address`, `opening_hours`, `ticket_price`, `ticket_price_conditions`, `visiting_services`.
2.  **`payment_methods`**:
    *   `id`, `monument_id`, `method` (Normalized payment method names).

## License

This project is for educational purposes as part of the Data Acquisition course at Paris Dauphine University.
