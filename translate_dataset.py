import json
import time
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions

# Load environment variables from .env file
load_dotenv()

# CONFIGURATION
API_KEY = os.getenv("GEMINI_API_KEY") 
INPUT_FILE = "paris_monuments_cleaned.json"
OUTPUT_FILE = "paris_monuments_translated.json"
OUTPUT_CSV = "paris_monuments_translated.csv"
BATCH_SIZE = 1

# Configure the Gemini API
genai.configure(api_key=API_KEY)


model = genai.GenerativeModel('gemma-3-4b-it')

def translate_batch_with_retry(batch_data, max_retries=3):
    prompt = """
    You are a professional translator for a tourism dataset. 
    Translate the French values in the provided JSON to English.
    
    Rules:
    1. Translate 'short_description', 'ticket_price_conditions', 'opening_hours'.
    2. For lists like 'payment_methods' and 'visiting_services', translate every item.
    3. DO NOT translate 'name', 'url', 'address', or 'ticket_price'. Keep them exactly as they are.
    4. Ensure the output is valid, raw JSON.
    
    Here is the JSON batch to translate:
    """
    
    delay = 5 # Start with 5 seconds wait
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt + json.dumps(batch_data))
            # Clean up potential markdown formatting
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
            
        except exceptions.ResourceExhausted:
            print(f"    [!] Rate limit hit. Waiting {delay}s before retry...")
            time.sleep(delay)
            delay *= 2 # Wait longer next time
            
        except Exception as e:
            print(f"    [!] Error (Attempt {attempt+1}): {e}")
            time.sleep(2)
            
    print("    [!] Max retries reached. Skipping this batch.")
    return None

def main():
    # Load Data
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: Cleaned JSON file not found.")
        return

    print(f"--- Starting Translation of {len(data)} records ---")
    translated_data = []

    # Process in Batches
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i : i + BATCH_SIZE]
        print(f" -> Processing batch {i//BATCH_SIZE + 1}...")
        
        result = translate_batch_with_retry(batch)
        
        if result:
            translated_data.extend(result)
        else:
            print("    [!] Batch failed. Keeping original French.")
            translated_data.extend(batch) 
            
        time.sleep(2) 

    # Save JSON Result
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, ensure_ascii=False, indent=4)
    print(f"\n--- Success! Translated JSON saved to '{OUTPUT_FILE}' ---")

    # Save CSV Result
    csv_data = []
    if translated_data:
        headers = translated_data[0].keys()
        for row in translated_data:
            csv_row = row.copy()
            if isinstance(csv_row.get('payment_methods'), list):
                csv_row['payment_methods'] = " | ".join(csv_row['payment_methods'])
            if isinstance(csv_row.get('visiting_services'), list):
                csv_row['visiting_services'] = " | ".join(csv_row['visiting_services'])
            csv_data.append(csv_row)

        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            import csv
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_data)
        print(f"--- Success! Translated CSV saved to '{OUTPUT_CSV}' ---")

if __name__ == "__main__":
    main()