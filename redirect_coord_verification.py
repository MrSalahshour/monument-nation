import pandas as pd
import numpy as np

# Configuratio
# File paths
WIKI_DATASET_FILE = 'paris_monuments_wiki_with_coordinates.csv'
REFERENCE_DATASET_FILE = 'merged_datasets/france_monuments_merged.csv'
REDIRECT_LOG_FILE = 'redirect_log.txt'
OUTPUT_FILE = 'paris_monuments_wiki_verified.csv'

# Threshold for coordinate verification (in Kilometers)
DISTANCE_THRESHOLD_KM = 2.0 

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers.
    return c * r

def main():
    print("Loading data...")
    
    # Load the Redirect Log
    redirected_names = set()
    try:
        with open(REDIRECT_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '->' in line:
                    # Format: "Input Name -> Wiki Name"
                    # We only care about the input name (left side)
                    input_name = line.split('->')[0].strip()
                    redirected_names.add(input_name)
        print(f"Loaded {len(redirected_names)} redirected entries from log.")
    except FileNotFoundError:
        print(f"Error: {REDIRECT_LOG_FILE} not found.")
        return

    # Load Datasets
    try:
        df_wiki = pd.read_csv(WIKI_DATASET_FILE)
        df_ref = pd.read_csv(REFERENCE_DATASET_FILE)
    except FileNotFoundError as e:
        print(f"Error loading CSV files: {e}")
        return

    # Create a lookup dictionary for the reference dataset for faster access
    # We map 'name' -> {'lat': ..., 'lng': ...}
    # Note: df_ref uses 'lng' while df_wiki uses 'lon'
    if 'name' not in df_ref.columns or 'lat' not in df_ref.columns or 'lng' not in df_ref.columns:
        print("Error: Reference dataset missing required columns (name, lat, lng)")
        return
        
    # Drop duplicates in reference to avoid errors, keeping the first occurrence
    df_ref_unique = df_ref.drop_duplicates(subset=['name'])
    ref_dict = df_ref_unique.set_index('name')[['lat', 'lng']].to_dict('index')

    print("Verifying coordinates...")

    # Validation Logic
    def verify_row(row):
        input_name = row['input_name']
        wiki_lat = row['lat']
        wiki_lon = row['lon']

        # Case 1: Name was NOT in the redirect log
        # Assumption: If it wasn't redirected, the wiki page is likely correct.
        if input_name not in redirected_names:
            return True

        # Case 2: Name WAS in the redirect log
        # We must verify coordinates against the reference dataset
        
        # If we don't have reference data for this place, we cannot verify it.
        # Marking as False 
        if input_name not in ref_dict:
            return False

        # If the scraped wiki data has no coordinates, it's definitely invalid
        if pd.isna(wiki_lat) or pd.isna(wiki_lon):
            return False

        # Get reference coordinates
        ref_lat = ref_dict[input_name]['lat']
        ref_lon = ref_dict[input_name]['lng']

        # Calculate distance
        try:
            dist = haversine_distance(wiki_lat, wiki_lon, ref_lat, ref_lon)
            
            # Check threshold
            if dist <= DISTANCE_THRESHOLD_KM:
                return True
            else:
                return False
        except Exception:
            return False

    # Apply the verification function
    df_wiki['is_correct'] = df_wiki.apply(verify_row, axis=1)

    # Save and Print Stats
    df_wiki.to_csv(OUTPUT_FILE, index=False)
    
    print("-" * 30)
    print("Processing Complete.")
    print(f"Saved to: {OUTPUT_FILE}")
    print("-" * 30)
    
    total = len(df_wiki)
    correct = df_wiki['is_correct'].sum()
    incorrect = total - correct
    
    print(f"Total Samples: {total}")
    print(f"Marked Correct (True): {correct} ({correct/total*100:.2f}%)")
    print(f"Marked Incorrect (False): {incorrect} ({incorrect/total*100:.2f}%)")
    
    # Detail on Redirects
    redirected_subset = df_wiki[df_wiki['input_name'].isin(redirected_names)]
    if not redirected_subset.empty:
        red_total = len(redirected_subset)
        red_correct = redirected_subset['is_correct'].sum()
        print(f"\nOf the {red_total} redirected samples:")
        print(f"  - Verified Correct via Coordinates: {red_correct}")
        print(f"  - Failed Verification: {red_total - red_correct}")

if __name__ == "__main__":
    main()