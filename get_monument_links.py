import time
import json
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_links():
    # Setup Driver
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    monument_data = []

    try:
        url = "https://www.monuments-nationaux.fr/trouver-un-monument"
        driver.get(url)

        # HANDLE COOKIES 
        try:
            # We use the EXACT ID you found
            accept_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "tarteaucitronPersonalize2"))
            )
            accept_btn.click()
            time.sleep(2) # Wait for banner to disappear
        except Exception as e:
            print(f" Warning: Could not click cookie button. Error: {e}")

        # LOAD ALL CONTENT
        # We scroll down in increments to ensure all 'cards' load
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) # Wait for new cards to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            print(f" Scrolled batch {i+1}")

        # EXTRACT LINKS WITH COORDINATES
        # We target the specific class we found : 'card-tour'
        cards = driver.find_elements(By.CLASS_NAME, "card-tour")
        
        print(f" -> Found {len(cards)} monument cards.")
        
        for card in cards:
            try:
                # Find the 'a' tag (link) inside the card
                link_element = card.find_element(By.TAG_NAME, "a")
                link_url = link_element.get_attribute("href")
                
                # Extract latitude and longitude from the card div's data attributes
                latitude = card.get_attribute("data-latitude")
                longitude = card.get_attribute("data-longitude")
                monument_name = card.get_attribute("data-name")
                
                # Basic cleanup
                if link_url and "http" in link_url:
                    monument_data.append({
                        "name": monument_name if monument_name else "Unknown",
                        "url": link_url,
                        "latitude": float(latitude) if latitude else None,
                        "longitude": float(longitude) if longitude else None
                    })
            except Exception as e:
                print(f" -> Warning: Could not extract data from card: {e}")
                continue

        # Remove duplicates based on URL
        seen_urls = set()
        unique_monuments = []
        for monument in monument_data:
            if monument["url"] not in seen_urls:
                seen_urls.add(monument["url"])
                unique_monuments.append(monument)
        
        monument_data = unique_monuments
        print(f" -> Successfully extracted {len(monument_data)} unique monuments with coordinates.")

        # SAVE TO TEXT FILE (for backward compatibility)
        with open("monument_urls.txt", "w", encoding="utf-8") as f:
            for monument in monument_data:
                f.write(monument["url"] + "\n")
        print(" -> Saved URLs to 'monument_urls.txt'")

        # SAVE TO JSON FILE
        with open("monument_urls_with_coords.json", "w", encoding="utf-8") as f:
            json.dump(monument_data, f, ensure_ascii=False, indent=4)
        print(" -> Saved data to 'monument_urls_with_coords.json'")

        # SAVE TO CSV FILE
        with open("monument_urls_with_coords.csv", "w", newline='', encoding="utf-8") as f:
            fieldnames = ["name", "url", "latitude", "longitude"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(monument_data)
        print(" -> Saved data to 'monument_urls_with_coords.csv'")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    get_links()