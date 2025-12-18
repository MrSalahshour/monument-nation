import pandas as pd
import time
import urllib.parse
import re
import os
import json
from dotenv import load_dotenv

# --- Third-Party Imports ---
from deep_translator import GoogleTranslator

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================

INPUT_FILE = './merged_datasets/france_monuments.csv'
OUTPUT_CSV = 'paris_monuments_wiki.csv'
OUTPUT_JSON = 'paris_monuments_wiki.json'
LOG_FILE = 'redirect_log.txt'

# Categories used to classify monuments based on text content
RELATED_SUBCATEGORY_SET = {
    "Church", "Temple", "Mosque", "Historic Site", "Museum", 
    "Art Museum", "History Museum", "Science Museum", "Art Gallery", 
    "Public Art", "Monument / Landmark", "Cemetery", "Garden", 
    "Sculpture Garden", "Park", "Plaza", "Bridge",
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def clean_text(text):
    """Removes citations (e.g., [1]), newlines, and extra spaces."""
    if not text: return None
    text = re.sub(r'\[.*?\]', '', text)
    text = text.replace('\n', ', ')
    return text.strip()

def translate_to_english(text):
    """Translates text to English using deep_translator (Free)."""
    if not text: return None
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated
    except Exception as e:
        print(f"    [!] Translation Error: {e}")
        return text 

def match_category(text_content):
    """
    Matches text content against the predefined English category set.
    Prioritizes longer category names first.
    """
    if not text_content: return "Historic Site"
    text_lower = text_content.lower()
    
    # Sort by length to match specific categories (e.g., "Art Museum") before general ones ("Museum")
    sorted_categories = sorted(RELATED_SUBCATEGORY_SET, key=len, reverse=True)

    for cat in sorted_categories:
        if "/" in cat:
            parts = [p.strip().lower() for p in cat.split('/')]
            if any(part in text_lower for part in parts):
                return cat
        elif cat.lower() in text_lower:
            return cat    
    return "Historic Site"

def is_valid_article_page(driver):
    """
    Determines if the current page is a valid Wikipedia article.
    Returns False for Search Results or Special pages.
    """
    try:
        url = driver.current_url.lower()
        
        # 1. Check URL patterns for Special/Search pages
        if "special:search" in url or "spécial:recherche" in url:
            return False
        if "index.php?search=" in url:
            return False

        # 2. Check for search result headings (indicates a list, not an article)
        search_results = driver.find_elements(By.CSS_SELECTOR, ".mw-search-result-heading")
        if len(search_results) > 0:
            return False

        # 3. Validation: Must have a main heading
        driver.find_element(By.ID, "firstHeading") 
        return True
    except:
        return False

def extract_raw_page_data(driver):
    """Extracts raw title, description text, and URL from the current page."""
    data = {
        "wiki_name": None,
        "description_raw": None,
        "infobox_raw": "",
        "wiki_url": driver.current_url
    }
    
    # 1. Get Title
    try:
        data['wiki_name'] = driver.find_element(By.ID, "firstHeading").text
    except: pass

    # 2. Get Description (First valid paragraph > 50 chars)
    try:
        paragraphs = driver.find_elements(By.CSS_SELECTOR, "#mw-content-text .mw-parser-output > p")
        for p in paragraphs:
            txt = clean_text(p.text)
            if txt and len(txt) > 50: 
                data['description_raw'] = txt
                break
    except: pass

    # 3. Get Infobox type/criterion (for category matching)
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table.infobox tr")
        for row in rows:
            header = row.find_element(By.TAG_NAME, "th").text.lower()
            if "type" in header or "criterion" in header:
                data['infobox_raw'] = row.find_element(By.TAG_NAME, "td").text
                break
    except: pass

    return data

# ==========================================
# MAIN LOGIC
# ==========================================

def process_monument(monument_name, driver):
    
    final_output = {
        "input_name": monument_name,
        "wiki_name": None,
        "wiki_description": None,
        "wiki_url": None,
        "category": None
    }

    # --- STEP 1: Attempt English Direct Match ---
    en_query = urllib.parse.quote(monument_name)
    en_url = f"https://en.wikipedia.org/w/index.php?search={en_query}&title=Special:Search&go=Go"
    
    driver.get(en_url)
    time.sleep(1)

    if is_valid_article_page(driver):
        print(f"[+] EN Match: {monument_name}")
        raw = extract_raw_page_data(driver)
        
        final_output['wiki_name'] = raw['wiki_name']
        final_output['wiki_description'] = raw['description_raw']
        final_output['wiki_url'] = raw['wiki_url']
        final_output['category'] = match_category(f"{raw['description_raw']} {raw['infobox_raw']}")
        return final_output

    # --- STEP 2: Fallback to French Search ---
    print(f"[-] No EN match. Checking FR...")
    fr_query = urllib.parse.quote(monument_name)
    fr_url = f"https://fr.wikipedia.org/w/index.php?search={fr_query}&title=Spécial:Recherche&go=Go"
    
    driver.get(fr_url)
    time.sleep(1) 

    # Handle Search Result Pages (List of links)
    search_results = driver.find_elements(By.CSS_SELECTOR, ".mw-search-result-heading a")
    
    if len(search_results) > 0:
        try:
            # Click the first result
            first_link = search_results[0]
            clicked_title = first_link.text
            print(f"    [>] Search list found. Clicking first: {clicked_title}")
            
            # Log the redirection/selection
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{monument_name} -> {clicked_title}\n")
            except Exception as log_error:
                print(f"    [!] Error writing log: {log_error}")

            first_link.click()
            time.sleep(2) 
        except Exception as e:
            print(f"    [!] Could not click first result: {e}")
            return final_output
    
    # --- STEP 3: Validate and Extract Data ---
    if is_valid_article_page(driver):
        try:
            raw = extract_raw_page_data(driver)
            
            # Populate fields
            final_output['wiki_name'] = raw['wiki_name'] 
            final_output['wiki_url'] = raw['wiki_url']
            
            # Translate content
            if raw['description_raw']:
                final_output['wiki_description'] = translate_to_english(raw['description_raw'])
            
            infobox_en = translate_to_english(raw['infobox_raw']) or ""
            desc_en = final_output['wiki_description'] or ""
            
            # Determine Category
            final_output['category'] = match_category(f"{desc_en} {infobox_en}")
            
            print(f"    [OK] Saved French data for: {raw['wiki_name']}")
            
        except Exception as e:
            print(f"    [!] Error extracting FR data: {e}")
    else:
        print("    [!] Page is not a valid article (maybe no results found).")

    return final_output

def main():
    # --- Load Input Data ---
    try:
        df = pd.read_csv(INPUT_FILE)
    except:
        try:
            df = pd.read_json(INPUT_FILE)
        except:
            print(f"Error reading {INPUT_FILE}")
            return

    total_monuments = len(df)

    # --- Selenium Setup ---
    chrome_options = Options()
    chrome_options.add_argument("--lang=en-US")
    # chrome_options.add_argument("--headless") 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    results = []
    print(f"--- Processing {total_monuments} monuments ---")

    # --- Processing Loop ---
    for index, row in df.iterrows():
        try:
            data = process_monument(row['name'], driver)
            results.append(data)
        except Exception as e:
            print(f"[!] Critical Error on row {index}: {e}")

        # Periodic Save (every 5 records)
        if index % 5 == 0:
            pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
            pd.DataFrame(results).to_json(OUTPUT_JSON, orient='records', indent=4)
            print(f"    [S] Periodic Save: {index + 1}/{total_monuments}")
        
    driver.quit()

    # --- Final Save ---
    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
    pd.DataFrame(results).to_json(OUTPUT_JSON, orient='records', indent=4)
    print(f"Done. Saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()