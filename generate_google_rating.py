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

INPUT_FILE = 'paris_monuments_cleaned.csv'  # input dataset
OUTPUT_CSV = 'paris_monuments_ratings.csv'  # output csv
OUTPUT_JSON = 'paris_monuments_ratings.json'  # output json

def extract_number(text):
    """Extract digits from a string and join them (e.g., '1,234' -> '1234')."""
    if not text: return None
    digits = re.findall(r'\d+', text)
    if not digits: return None
    return "".join(digits)

def find_stats_in_page(driver):
    """Fallback: scan aria-labels to detect rating (stars) and review count (reviews)."""
    found_data = {"rating": None, "review_count": None}
    elements = driver.find_elements(By.XPATH, "//*[@aria-label]")

    for el in elements:
        label = el.get_attribute("aria-label")
        if not label: continue

        if not found_data['rating']:
            rating_match = re.search(r"(\d+[.,]?\d*)\s*stars", label, re.IGNORECASE)
            if rating_match:
                found_data['rating'] = rating_match.group(1).replace(",", ".")

        if not found_data['review_count']:
            review_match = re.search(r"([\d,.]+)\s*reviews", label, re.IGNORECASE)
            if review_match:
                found_data['review_count'] = extract_number(review_match.group(1))

        if found_data['rating'] and found_data['review_count']:
            break

    return found_data

def get_google_maps_data(monument_name, driver):
    data = {"name": monument_name, "rating": None, "review_count": None, "google_maps_url": None}

    encoded_name = urllib.parse.quote(monument_name)
    search_url = f"https://www.google.com/maps/search/{encoded_name}?hl=en"  # force English labels

    try:
        driver.get(search_url)
        data['google_maps_url'] = search_url

        try:
            accept_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), 'Accept all')]]"))
            )
            accept_btn.click()
        except:
            pass

        time.sleep(2)

        try:
            rating_el = driver.find_element(By.CLASS_NAME, "fontDisplayLarge")
            data['rating'] = rating_el.text.strip().replace(",", ".")

            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                txt = btn.text.lower()
                if "reviews" in txt:
                    data['review_count'] = extract_number(txt)
                    break
                if "reviews" in (btn.get_attribute("aria-label") or "").lower():
                    data['review_count'] = extract_number(btn.get_attribute("aria-label"))
                    break
        except:
            pass

        if not data['rating'] or not data['review_count']:
            fallback_data = find_stats_in_page(driver)
            if not data['rating']:
                data['rating'] = fallback_data['rating']
            if not data['review_count']:
                data['review_count'] = fallback_data['review_count']

        print(f"[+] {monument_name}: {data['rating']} stars, {data['review_count']} reviews")

    except Exception as e:
        print(f"[!] Error processing {monument_name}: {e}")

    return data

def main():
    try:
        df = pd.read_csv(INPUT_FILE)
    except:
        df = pd.read_json(INPUT_FILE)

    results = []

    chrome_options = Options()
    chrome_options.add_argument("--lang=en-US")  # keep Google labels in English
    chrome_options.add_argument("--no-sandbox")  # avoid sandbox issues
    # chrome_options.add_argument("--headless")  # run without UI if needed

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    print(f"Starting crawl for {len(df)} monuments...")

    for index, row in df.iterrows():
        name = row['name']
        monument_data = get_google_maps_data(name, driver)
        results.append(monument_data)

        if index % 10 == 0:
            pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)  # periodic checkpoint save

        time.sleep(random.uniform(1.5, 3))  # basic rate limiting

    driver.quit()

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_CSV, index=False)
    results_df.to_json(OUTPUT_JSON, orient='records', indent=4)
    print("Done!")

if __name__ == "__main__":
    main()
