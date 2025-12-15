import time
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
    
    monument_urls = []

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

        # EXTRACT LINKS
        # We target the specific class we found : 'card-tour'
        cards = driver.find_elements(By.CLASS_NAME, "card-tour")
        
        print(f" -> Found {len(cards)} monument cards.")
        
        for card in cards:
            try:
                # Find the 'a' tag (link) inside the card
                link_element = card.find_element(By.TAG_NAME, "a")
                link_url = link_element.get_attribute("href")
                
                # Basic cleanup
                if link_url and "http" in link_url:
                    monument_urls.append(link_url)
            except:
                continue

        # Remove duplicates
        monument_urls = list(set(monument_urls))
        print(f" -> Successfully extracted {len(monument_urls)} unique monument URLs.")

        # SAVE TO FILE
        with open("monument_urls.txt", "w", encoding="utf-8") as f:
            for link in monument_urls:
                f.write(link + "\n")
        print(" -> Saved links to 'monument_urls.txt'")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    get_links()