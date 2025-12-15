import pandas as pd
import time
import random
import urllib.parse
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

INPUT_FILE = 'paris_monuments_cleaned.csv'
OUTPUT_CSV = 'paris_monuments_wiki_clean.csv'

def clean_text(text):
    """Removes citations [1], newlines, and extra spaces."""
    if not text: return None
    # Remove references like [1], [a]
    text = re.sub(r'\[.*?\]', '', text)
    # Replace newlines with a comma and space
    text = text.replace('\n', ', ')
    return text.strip()

def get_wikipedia_data(monument_name, driver):
    # 1. Initialize with ONLY the specific columns you want
    data = {
        "name": monument_name,
        "wiki_description": None,
        "wiki_url": None,
        "categories": None,
        "fact_style": None,      # Architectural style
        "fact_completed": None,  # Completed / Opened
        "fact_type": None,       # Type / Function
        "fact_built": None,      # Founded / Built / Established
        "fact_built_by": None,   # Architect / Founder
        "fact_visitors": None    # Annual visitors
    }

    # Search query
    search_query = f"{monument_name} France" # "France" helps avoid global duplicates
    encoded_query = urllib.parse.quote(search_query)
    search_url = f"https://en.wikipedia.org/w/index.php?search={encoded_query}&title=Special:Search&go=Go"

    try:
        driver.get(search_url)
        
        # Handle "Search Results" vs "Direct Article"
        try:
            if "search results" in driver.title.lower():
                first_result = driver.find_element(By.CSS_SELECTOR, ".mw-search-results li a")
                first_result.click()
                time.sleep(2)
        except:
            pass

        data['wiki_url'] = driver.current_url

        # --- Extract Description ---
        try:
            # Get first substantial paragraph
            paragraphs = driver.find_elements(By.CSS_SELECTOR, "#mw-content-text .mw-parser-output > p")
            for p in paragraphs:
                txt = clean_text(p.text)
                if txt and len(txt) > 60: # Skip coordinates or empty lines
                    data['wiki_description'] = txt
                    break
        except:
            pass

        # --- Extract Categories ---
        try:
            cat_links = driver.find_elements(By.CSS_SELECTOR, "#mw-normal-catlinks ul li a")
            # Join top 5 categories with comma
            data['categories'] = ", ".join([c.text for c in cat_links[:5]])
        except:
            pass

        # --- Extract Specific Facts (The Mapping Logic) ---
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table.infobox tr")
            
            for row in rows:
                try:
                    header_el = row.find_element(By.TAG_NAME, "th")
                    value_el = row.find_element(By.TAG_NAME, "td")
                    
                    header = header_el.text.lower().strip()
                    value = clean_text(value_el.text)

                    # MAPPING DICTIONARY
                    # We check the header and assign to the correct fixed column
                    
                    if "style" in header:
                        data['fact_style'] = value
                    
                    elif "completed" in header or "opened" in header:
                        data['fact_completed'] = value
                        
                    elif "type" in header or "criterion" in header:
                        data['fact_type'] = value
                        
                    # Prioritize exact "built" or "founded" match for this column
                    elif any(x in header for x in ["built", "founded", "established", "construction"]):
                        # Only fill if empty to avoid overwriting specific dates with vague ones
                        if not data['fact_built']: 
                            data['fact_built'] = value
                            
                    elif any(x in header for x in ["architect", "founder", "designer", "engineer"]):
                        data['fact_built_by'] = value
                        
                    elif "visitors" in header or "visitation" in header:
                        data['fact_visitors'] = value

                except:
                    continue # Skip rows without th/td pair
        except:
            pass

        print(f"[+] {monument_name}: Scraped.")

    except Exception as e:
        print(f"[!] Error {monument_name}: {e}")

    return data

def main():
    # Load input
    try:
        df = pd.read_csv(INPUT_FILE)
    except:
        df = pd.read_json(INPUT_FILE)

    chrome_options = Options()
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--headless") 

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    results = []
    print(f"Starting Clean Crawl for {len(df)} monuments...")

    for index, row in df.iterrows():
        name = row['name']
        row_data = get_wikipedia_data(name, driver)
        results.append(row_data)

        # Periodic Save
        if index % 10 == 0:
            pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
        
        time.sleep(1)

    driver.quit()

    # Final Save
    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)
    print("Done! Saved to", OUTPUT_CSV)

if __name__ == "__main__":
    main()