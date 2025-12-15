import json
import csv
import re

INPUT_FILE = "paris_monuments_data.json"
OUTPUT_JSON = "paris_monuments_cleaned.json"
OUTPUT_CSV = "paris_monuments_cleaned.csv"

def clean_price(price_str):
    """Extracts the first float/int found in the price string."""
    if not price_str or price_str.lower() in ["not found", "none", "gratuit"]:
        if price_str and "gratuit" in price_str.lower():
            return 0.0
        return None
    
    # Regex to find numbers like 16, 16.50, 16,50
    match = re.search(r'(\d+[.,]?\d*)', price_str)
    if match:
        return float(match.group(1).replace(',', '.'))
    return None

def clean_text(text):
    """Standardizes empty strings, 'Not found', and whitespace."""
    if not text:
        return None
    if isinstance(text, str):
        cleaned = text.strip()
        # List of placeholders that indicate missing data
        invalid_strings = [
            "not found", "name not found", "address not found", 
            "section not found", "none", ""
        ]
        if cleaned.lower() in invalid_strings:
            return None
        return cleaned
    return text

def analyze_data(data):
    """Generates a quality report on the FINAL dataset."""
    total_records = len(data)
    stats = {key: 0 for key in data[0].keys()}

    print(f"\n--- FINAL DATASET ANALYSIS REPORT ---")
    print(f"Total Valid Records: {total_records}")
    print("-" * 65)
    print(f"{'Field':<25} | {'Filled':<10} | {'Missing':<10} | {'Fill Rate'}")
    print("-" * 65)

    for entry in data:
        for key, value in entry.items():
            if value is not None and value != []:
                stats[key] += 1

    for key, count in stats.items():
        missing = total_records - count
        fill_rate = (count / total_records) * 100 if total_records > 0 else 0
        print(f"{key:<25} | {count:<10} | {missing:<10} | {fill_rate:.1f}%")
    print("-" * 65)

def main():
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Run the scraper first.")
        return

    cleaned_data = []
    removed_count = 0

    print("--- Cleaning Data ---")

    for row in raw_data:
        new_row = row.copy()
        
        # Clean Text Fields
        new_row['name'] = clean_text(row.get('name'))
        new_row['short_description'] = clean_text(row.get('short_description'))
        new_row['address'] = clean_text(row.get('address'))
        new_row['opening_hours'] = clean_text(row.get('opening_hours'))
        
        # Clean Ticket Conditions (Keep only first line)
        conditions = clean_text(row.get('ticket_price_conditions'))
        if conditions:
            # split by newline and take the first part
            new_row['ticket_price_conditions'] = conditions.split('\n')[0].strip()
        else:
            new_row['ticket_price_conditions'] = None
        
        # Clean Price
        new_row['ticket_price_raw'] = row.get('ticket_price')
        extracted_price = clean_price(row.get('ticket_price'))
        
        # If extraction failed (None), assume it is Free (0.0)
        new_row['ticket_price'] = extracted_price if extracted_price is not None else 0.0

        # Handle Lists
        if isinstance(row.get('payment_methods'), list):
             new_row['payment_methods'] = [x for x in row['payment_methods'] if x]
        
        if isinstance(row.get('visiting_services'), list):
             new_row['visiting_services'] = [x for x in row['visiting_services'] if x]

        # FILTERING LOGIC
        # If Address or Name is missing after cleaning, SKIP this record.
        if not new_row['address'] or not new_row['name']:
            removed_count += 1
            # Print which ones are being removed
            # print(f"Removing incomplete record: {new_row['url']}")
            continue

        cleaned_data.append(new_row)

    print(f"-> Removed {removed_count} incomplete records (missing Name or Address).")

    # Run Analysis
    if cleaned_data:
        analyze_data(cleaned_data)

        # Save JSON
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
        print(f"-> Saved cleaned JSON to {OUTPUT_JSON}")

        # Save CSV
        # Prepare data for CSV (flatten lists)
        csv_data = []
        headers = cleaned_data[0].keys()
        
        for row in cleaned_data:
            csv_row = row.copy()
            if isinstance(csv_row['payment_methods'], list):
                csv_row['payment_methods'] = " | ".join(csv_row['payment_methods'])
            if isinstance(csv_row['visiting_services'], list):
                csv_row['visiting_services'] = " | ".join(csv_row['visiting_services'])
            csv_data.append(csv_row)

        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_data)
        print(f"-> Saved cleaned CSV to {OUTPUT_CSV}")
    else:
        print("Error: No valid data remained after cleaning.")

if __name__ == "__main__":
    main()