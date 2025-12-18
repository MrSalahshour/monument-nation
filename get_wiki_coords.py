import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

def get_coordinates(url):
    """
    Fetches the Wikipedia URL and extracts latitude and longitude 
    from the mw-kartographer-maplink anchor tag.
    """
    if pd.isna(url) or url == "":
        return None, None

    # Wikipedia requires a User-Agent to avoid blocking scripts
    headers = {
        'User-Agent': 'CoordinateScraper/1.0 (contact@example.com)'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # If the page loads successfully
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the span with id="coordinates"
            coord_span = soup.find('span', id='coordinates')
            
            if coord_span:
                # Find the anchor tag inside that span that contains the map data
                link = coord_span.find('a', class_='mw-kartographer-maplink')
                
                if link and link.has_attr('data-lat') and link.has_attr('data-lon'):
                    return link['data-lat'], link['data-lon']
        
        return None, None

    except Exception as e:
        # In case of connection errors, timeouts, etc.
        # print(f"Error fetching {url}: {e}") 
        return None, None

def process_csv(input_file, output_file):
    print(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)

    # Check if column exists
    if 'wiki_url' not in df.columns:
        print("Error: The column 'wiki_url' was not found in the CSV.")
        return

    # Initialize new columns
    df['lat'] = None
    df['lon'] = None

    total_samples = len(df)
    crawled_count = 0
    
    print("Starting crawl... (This may take time depending on file size)")

    for index, row in df.iterrows():
        url = row['wiki_url']
        
        # Fetch coordinates
        lat, lon = get_coordinates(url)
        
        if lat and lon:
            df.at[index, 'lat'] = lat
            df.at[index, 'lon'] = lon
            crawled_count += 1
        
        # Simple progress indicator every 10 rows
        if (index + 1) % 10 == 0:
            print(f"Processed {index + 1}/{total_samples} rows...")

        # Sleep briefly to be polite to Wikipedia servers and avoid rate limits
        time.sleep(0.5) 

    # Save the new dataset
    df.to_csv(output_file, index=False)
    print(f"\n--- Processing Complete ---")
    print(f"File saved to: {output_file}")
    
    # Statistics
    print("\n--- Statistics ---")
    print(f"Total samples: {total_samples}")
    print(f"Coordinates found: {crawled_count}")
    print(f"Success rate: {(crawled_count / total_samples) * 100:.2f}%")

# EXECUTION
input_csv = 'paris_monuments_wiki.csv' 
output_csv = 'paris_monuments_wiki_with_coordinates.csv'

process_csv(input_csv, output_csv)