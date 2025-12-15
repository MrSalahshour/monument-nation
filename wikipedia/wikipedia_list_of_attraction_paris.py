from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
from urllib.parse import urljoin
import json


# ---------------- CONFIG ----------------

url = "https://en.wikipedia.org/wiki/List_of_tourist_attractions_in_Paris"
output_csv = "paris_attractions_wikipedia.csv"
output_json = "paris_attractions_wikipedia.json"
headless = True  # whether to run browser in headless mode
# ----------------------------------------

def make_driver(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")  # Uncomment to run invisible
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def clean_text(t):
    if not t:
        return t
    return t.replace("[edit]", "").strip()

def scrape_by_sequential_children(url, driver, pause_between_sections=0.05):
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "mw-parser-output")))
    time.sleep(0.8)  # let page render a bit

    parser = driver.find_element(By.CLASS_NAME, "mw-parser-output")
    children = parser.find_elements(By.XPATH, "./*")  # direct children in order

    results = []
    region = None
    type = None

    for i, child in enumerate(children, start=1):
        tag = child.tag_name.lower()
        cls = (child.get_attribute("class") or "").strip()

        # Heading wrappers on this page are divs with classes like 'mw-heading mw-heading2' or 'mw-heading mw-heading3'
        if tag == "div" and "mw-heading" in cls:
            # check for h2 or h3 inside that div
            try:
                h2 = child.find_element(By.TAG_NAME, "h2")
                # set current h2, reset h3
                region = clean_text(h2.text)
                type = None
                # skip irrelevant h2s
                if region in ["See also", "Notes and references", "References", "External links"]:
                    region = None
                # small debug (uncomment if needed)
                # print(f"[H2] {region}")
                continue
            except:

                pass
            try:
                h3 = child.find_element(By.TAG_NAME, "h3")
                type = clean_text(h3.text)
                # skip irrelevant h3s (unlikely)
                if type in ["See also", "Notes and references", "References", "External links"]:
                    type = None
                # small debug
                # print(f"  [H3] {type}")
                continue
            except:
                pass

        # Lists following headings are <ul> elements
        if tag == "ul" and (region is not None or type is not None):
            lis = child.find_elements(By.TAG_NAME, "li")
            for li in lis:
                # Extract first meaningful <a> text as name if present, otherwise full text
                name = None
                link = None
                try:
                    # choose the first <a> that has non-empty text
                    anchors = li.find_elements(By.TAG_NAME, "a")
                    for a in anchors:
                        a_text = a.text.strip()
                        a_href = a.get_attribute("href")
                        if a_text:
                            name = a_text
                            if a_href:
                                link = urljoin(driver.current_url, a_href)
                            break
                except:
                    pass

                if not name:
                    name = li.text.strip().split(" - ")[0].strip()  # fallback

                # Description is remainder of li text after the chosen name (heuristic)
                description = None
                full = li.text.strip()
                if name and full.startswith(name):
                    rest = full[len(name):].strip()
                    if rest.startswith("–") or rest.startswith("-") or rest.startswith(","):
                        rest = rest[1:].strip()
                    description = rest if rest else None

                results.append({
                    "name": name,
                    "region": region,
                    "type": type,
                    "description": description,
                    "link": link
                })

            # polite tiny pause (don't hammer)
            time.sleep(pause_between_sections)

    return results

def save_to_csv(rows, filename):
    keys = ["name", "region", "type", "description", "link"]
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def save_to_json(rows, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)



def main():
    driver = make_driver(headless=headless)
    try:
        rows = scrape_by_sequential_children(url, driver)
        print("FOUND:", len(rows))
        for r in rows[:30]:
            print(r)
        save_to_csv(rows, output_csv)
        print("Saved to", output_csv)
        save_to_json(rows, output_json)
        print("Saved to", output_json)
    finally:
        driver.quit()
        driver.quit()

if __name__ == "__main__":
    main()
