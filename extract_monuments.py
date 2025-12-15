import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_monument_details():
    # SETUP
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") # Uncomment to run invisible
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    monuments_data = []

    # Read URLs from the file created in step 1
    try:
        with open("monument_urls.txt", "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print("Error: 'monument_urls.txt' not found. Please run get_monument_links.py first.")
        return

    print(f"--- Loaded {len(urls)} URLs to process ---")

    for index, url in enumerate(urls):
        print(f"\nProcessing [{index+1}/{len(urls)}]: {url}")
        
        monument_info = {
            "name": None,
            "url": url,
            "short_description": None,
            "ticket_price": None,
            "ticket_price_conditions": None,
            "opening_hours": None,
            "payment_methods": None,
            "address": None,
            "visiting_services": None
        }

        try:

            # PHASE 1: MAIN PAGE (Description, Prices, Link to Practical Info)
           
            driver.get(url)
            handle_cookie_banner(driver)

            # Short Description
            # Target: <div class="col-md-6 block-info__left"> -> <p class="text">
            try:
                desc_element = driver.find_element(By.CSS_SELECTOR, ".block-info__left .text")
                monument_info["short_description"] = desc_element.text.strip()
            except:
                monument_info["short_description"] = "Not found"

            # Ticket Price
            # Target: <div class="col-sm-6 block-info__right__right"> -> .title .text
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, ".block-info__right__right .title .text")
                monument_info["ticket_price"] = price_element.text.strip()
            except:
                monument_info["ticket_price"] = "Not found"

            # Ticket Price Special Conditions
            # Target: <div class="col-sm-6 block-info__right__right"> -> .ezrichtext-field p
            try:
                cond_element = driver.find_element(By.CSS_SELECTOR, ".block-info__right__right .ezrichtext-field")
                monument_info["ticket_price_conditions"] = cond_element.text.strip()
            except:
                monument_info["ticket_price_conditions"] = "None"

            # Find "Practical Info" Link
            # Target: <div class="block-info__right__left"> -> <a>
            practical_url = None
            try:
                link_element = driver.find_element(By.CSS_SELECTOR, ".block-info__right__left a")
                practical_url = link_element.get_attribute("href")
            except:
                print(" -> Warning: Could not find link to practical info page.")

            # PHASE 2: PRACTICAL INFO PAGE (Hours, Address, Payment, Services)
            if practical_url:
                # print(f" -> Navigating to Practical Info: {practical_url}")
                driver.get(practical_url)
                # Handle cookie again in case it reappears on new page
                handle_cookie_banner(driver) 
                
                # HELPER FOR "NEXT BLOCK" LOGIC
                # Based on the structure: 
                # <div class="landing-page__block"> ... <h2 id="target"> ... </div>
                # The content is in the *next sibling* div with class "landing-page__block"
                def get_content_block_by_id(target_id):
                    xpath = (
                        f"//h2[@id='{target_id}']"
                        "/ancestor::div[contains(@class, 'landing-page__block')]"
                        "/following-sibling::div[contains(@class, 'landing-page__block')][1]"
                    )
                    return driver.find_element(By.XPATH, xpath)

                # Opening Hours (ID: horaires-d-ouverture)
                try:
                    block = get_content_block_by_id("horaires-d-ouverture")
                    # Extract text from the ezrichtext-field inside that block
                    text_area = block.find_element(By.CLASS_NAME, "ezrichtext-field")
                    monument_info["opening_hours"] = text_area.text.strip()
                except:
                    monument_info["opening_hours"] = "Not found"

                # Payment Methods (ID: mode-de-paiement)
                try:
                    block = get_content_block_by_id("mode-de-paiement")
                    items = block.find_elements(By.CSS_SELECTOR, ".ezrichtext-field ul li")
                    monument_info["payment_methods"] = [item.text.strip() for item in items]
                except:
                    monument_info["payment_methods"] = []

                # Name & Address (ID: acces-et-transports)
                try:
                    block = get_content_block_by_id("acces-et-transports")
                    
                    # Name (h3.card-title)
                    try:
                        name_el = block.find_element(By.CLASS_NAME, "card-title")
                        monument_info["name"] = name_el.text.strip()
                    except:
                        monument_info["name"] = "Name Not Found"
                        
                    # Address (address.card-text)
                    try:
                        addr_el = block.find_element(By.CLASS_NAME, "card-text")
                        monument_info["address"] = addr_el.text.strip().replace("\n", ", ")
                    except:
                        monument_info["address"] = "Address Not Found"
                except:
                    monument_info["address"] = "Section Not Found"

                # Visiting Services (ID: services-et-conditions-de-visite)
                try:
                    block = get_content_block_by_id("services-et-conditions-de-visite")
                    items = block.find_elements(By.CSS_SELECTOR, ".ezrichtext-field ul li")
                    monument_info["visiting_services"] = [item.text.strip() for item in items]
                except:
                    monument_info["visiting_services"] = []

            # If name wasn't found in Phase 2, fallback to main page title or URL
            if not monument_info["name"]:
                 monument_info["name"] = driver.title.split("|")[0].strip()

            print(f" -> Extracted: {monument_info['name']}")
            monuments_data.append(monument_info)
            
            # Be polite to the server
            time.sleep(1)

        except Exception as e:
            print(f" -> Error processing {url}: {e}")
            continue

    # SAVE TO JSON
    with open("paris_monuments_data.json", "w", encoding="utf-8") as f:
        json.dump(monuments_data, f, ensure_ascii=False, indent=4)
    
    print("\n--- Success! Data saved to 'paris_monuments_data.json' ---")
    driver.quit()

def handle_cookie_banner(driver):
    """
    Handles the 'tarteaucitron' cookie banner if it appears.
    Strategically looks for the 'Tout accepter' button.
    """
    try:
        # Wait briefly for banner - it might not always appear if session persists
        WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.ID, "tarteaucitronAlertBig"))
        )
        
        # Try specific ID first
        accept_btn = driver.find_element(By.ID, "tarteaucitronPersonalize2")
        accept_btn.click()
        time.sleep(1) # Allow animation to clear
    except TimeoutException:
        pass # No banner, that's fine
    except NoSuchElementException:
        # Fallback: Try finding by text
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "Tout accepter" in btn.text:
                    btn.click()
                    time.sleep(1)
                    break
        except:
            pass
    except Exception as e:
        # Don't let cookie failure stop the scraping
        print(f"Cookie warning: {e}")

if __name__ == "__main__":
    get_monument_details()