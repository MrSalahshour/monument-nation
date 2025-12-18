import pandas as pd
import time
import random
import urllib.parse
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

INPUT_FILE = './merged_datasets/france_monuments.csv'
OUTPUT_CSV = 'paris_monuments_ratings.csv'
OUTPUT_JSON = 'paris_monuments_ratings.json'

def extract_review_count(text):
    """
    Extracts review count strictly to avoid matching phone numbers or hours.
    Matches patterns like "(1,234)" or "1,234 reviews".
    """
    if not text: return None
    
    # Normalize spaces
    text = text.replace('\u202f', ' ').replace(' ', ' ')

    # Pattern A: Parentheses -> "(1,234)"
    match_parens = re.search(r'\(([\d,.\s]+)\)', text)
    if match_parens:
        clean_num = re.sub(r'[^\d]', '', match_parens.group(1))
        if clean_num: 
            return clean_num

    # Pattern B: Explicit Label -> "1,234 reviews"
    match_label = re.search(r'([\d,.\s]+)\s+(?:reviews|avis|rezensionen)', text, re.IGNORECASE)
    if match_label:
        clean_num = re.sub(r'[^\d]', '', match_label.group(1))
        if clean_num:
            return clean_num

    return None

def handle_cookie_consent(driver):
    """Clicks 'Accept all' on the Google cookie consent popup if present."""
    try:
        accept_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button//span[contains(text(), 'Accept all') or contains(text(), 'Tout accepter')]"))
        )
        driver.execute_script("arguments[0].click();", accept_btn)
        time.sleep(1)
    except:
        pass

def get_opening_hours(driver):
    """Expands and extracts opening hours for the week."""
    days_found = []
    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    try:
        # Attempt to expand the hours section
        try:
            expand_btn = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label*='opening hours'], [aria-label*='Horaires']"))
            )
            driver.execute_script("arguments[0].click();", expand_btn)
            time.sleep(0.5)
        except:
            pass

        # Parse rows for days and times
        rows = driver.find_elements(By.TAG_NAME, "tr")
        if len(rows) < 2:
            rows = driver.find_elements(By.CSS_SELECTOR, "div[aria-label]")

        for row in rows:
            text = row.get_attribute("aria-label") or row.text
            if not text: continue
            clean_text = text.strip().replace("\n", " ")
            
            for day in week_days:
                if day in clean_text:
                    if any(d.startswith(day) for d in days_found): continue
                    hours = clean_text.replace(day, "").strip().lstrip(":, ")
                    if any(c.isdigit() for c in hours) or "Closed" in hours or "Open" in hours:
                        days_found.append(f"{day}={hours}")
    except Exception:
        pass
    return "; ".join(days_found) if days_found else None

def get_google_maps_data(monument_name, driver, counter):
    data = {
        "name": monument_name, 
        "rating": None, 
        "review_count": None, 
        "website": None, 
        "opening_hours": None,
        "google_maps_url": None
    }

    # Use a dummy domain to trigger a Google Search redirect structure
    encoded_name = urllib.parse.quote(monument_name)
    search_url = f"https://www.google.com/maps/search/{encoded_name}"

    try:
        driver.get(search_url)
        handle_cookie_consent(driver)

        # Handle disambiguation (List View vs Details View)
        try:
            WebDriverWait(driver, 5).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']"))
                )
            )
            if not driver.find_elements(By.CSS_SELECTOR, "h1"):
                first_result = driver.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
                if first_result:
                    driver.execute_script("arguments[0].click();", first_result[0])
                    time.sleep(2)
        except:
            pass
        
        data['google_maps_url'] = driver.current_url

        # 1. Extract Rating
        try:
            star_xpath = "//div[@role='main']//span[contains(@aria-label, 'stars') or contains(@aria-label, 'étoiles')]"
            star_element = driver.find_element(By.XPATH, star_xpath)
            rating_text = star_element.get_attribute("aria-label")
            match = re.search(r'(\d+[.,]\d+)', rating_text)
            if match:
                data['rating'] = match.group(1).replace(",", ".")
        except:
            try:
                # Fallback for large font display
                rating_el = driver.find_element(By.CSS_SELECTOR, "div.fontDisplayLarge")
                data['rating'] = rating_el.text.strip().replace(",", ".")
            except:
                pass

        # 2. Extract Review Count
        try:
            candidates = driver.find_elements(By.XPATH, "//div[@role='main']//button") + \
                         driver.find_elements(By.XPATH, "//div[@role='main']//span")
            
            for el in candidates:
                # Check visible text then aria-label
                count = extract_review_count(el.text) or extract_review_count(el.get_attribute("aria-label"))
                if count:
                    data['review_count'] = count
                    break
        except Exception:
            pass

        # 3. Extract Website URL
        try:
            website_btn = driver.find_element(By.CSS_SELECTOR, "[data-item-id='authority']")
            data['website'] = website_btn.get_attribute("href")
        except:
            pass

        # 4. Extract Opening Hours
        data['opening_hours'] = get_opening_hours(driver)

        # Logging results to console
        r_log = data['rating'] if data['rating'] else "N/A"
        rc_log = data['review_count'] if data['review_count'] else "N/A"
        url_status = "Found" if data['website'] else "Not Found"
        time_status = "Found" if data['opening_hours'] else "Not Found"

        print(f"[{counter}] {monument_name[:25]:<25} | Rating: {r_log:<4} | Reviews: {rc_log:<6} | URL: {url_status} | Time: {time_status}")

    except Exception as e:
        print(f"[{counter}] Error processing {monument_name}: {e}")

    return data

def main():
    try:
        df = pd.read_csv(INPUT_FILE)
    except:
        try:
            df = pd.read_json(INPUT_FILE)
        except:
            print("Error reading input file.")
            return

    results = []
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()

    print(f"Starting crawl for {len(df)} monuments...")

    for index, row in df.iterrows():
        name = row['name']
        # Pass index + 1 to serve as the counter
        monument_data = get_google_maps_data(name, driver, index + 1)
        results.append(monument_data)

        # Save partial results every 5 entries
        if index % 5 == 0:
            pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)

        time.sleep(random.uniform(2, 4))

    driver.quit()

    # Final Save
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_CSV, index=False)
    results_df.to_json(OUTPUT_JSON, orient='records', indent=4)
    print("Done!")

if __name__ == "__main__":
    main()