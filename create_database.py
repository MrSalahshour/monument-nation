import pandas as pd
import sqlite3
import os

# Configuration for file names
FILES = {
    "france_monuments": "merged_datasets\\with_coords\\with_google_map_url_city_opening_hour\\france_monuments.csv",
    "google_maps_data": "merged_datasets\\with_coords\\with_google_map_url_city_opening_hour\\google_maps_data_cleaned.csv",
    "google_reviews": "merged_datasets\\with_coords\\with_google_map_url_city_opening_hour\\google_maps_reviews_cleaned.csv",
    "wiki_data": "paris_monuments_wiki_llm_verified.csv",
    "foursquare_data": "merged_datasets\\Tourpedia_Foursquare_data.csv",
    "foursquare_reviews": "merged_datasets\\Tourpedia_Foursquare_reviews.csv"
}

DB_NAME = "monuments_database.db"

def load_csv(file_key):
    """Helper to load CSV and print info for debugging."""
    file_path = FILES[file_key]
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return None
    print(f"--- Loading {file_key} ---")
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df)} rows.")
    # Standardize ID columns to avoid join issues (optional but recommended)
    return df

def create_connection(db_file):
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"--- Connected to SQLite: {db_file} ---")
    except Exception as e:
        print(e)
    return conn

def main():
    # ---------------------------------------------------------
    # 1. LOAD DATA
    # ---------------------------------------------------------
    df_main = load_csv("france_monuments")
    df_google_data = load_csv("google_maps_data")
    df_google_reviews = load_csv("google_reviews")
    df_wiki = load_csv("wiki_data")
    df_fs_data = load_csv("foursquare_data")
    df_fs_reviews = load_csv("foursquare_reviews")

    if any(df is None for df in [df_main, df_google_data, df_google_reviews, df_wiki, df_fs_data, df_fs_reviews]):
        print("Stopping execution due to missing files.")
        return

    # ---------------------------------------------------------
    # 2. PREPARE MAIN TABLE (attraction) - STEP A (Wiki Merge)
    # ---------------------------------------------------------
    print("\n--- Processing Main Table: Wiki Merge ---")
    
    # Filter wiki data: only correct entries
    df_wiki_clean = df_wiki[df_wiki['is_correct'] == True].copy()
    
    # Prepare columns to merge
    # We rename columns in wiki to avoid overlap before merge, or handle suffixes
    df_wiki_clean = df_wiki_clean[['input_name', 'wiki_description', 'wiki_url', 'category']]
    df_wiki_clean = df_wiki_clean.rename(columns={
        'input_name': 'name_join_key', # Temporary key
        'wiki_description': 'description',
        'category': 'wiki_category'
    })

    # Merge Main with Wiki on 'name'
    # using left merge to keep all monuments even if no wiki data
    df_main_merged = pd.merge(
        df_main, 
        df_wiki_clean, 
        left_on='name', 
        right_on='name_join_key', 
        how='left'
    )

    # 1. Fill category for the first 88 samples (or where missing) using wiki_category
    # Logic: If 'category' is null, use 'wiki_category'
    df_main_merged['category'] = df_main_merged['category'].fillna(df_main_merged['wiki_category'])

    # 2. Ensure 'description' and 'wiki_url' are added (already done via merge)
    
    # Cleanup temporary columns
    df_main_merged.drop(columns=['name_join_key', 'wiki_category'], inplace=True)
    
    print(f"Main table shape after Wiki merge: {df_main_merged.shape}")

    # ---------------------------------------------------------
    # 3. PREPARE MAIN TABLE - STEP B (Google Data Merge)
    # ---------------------------------------------------------
    print("\n--- Processing Main Table: Google Data Merge ---")
    
    # CHANGE: Removed 'price_level' from this list
    cols_to_add = ['monument_id', 'website', 'phone', 'rating', 'votes_count']
    df_google_subset = df_google_data[cols_to_add].copy()
    
    # Rename columns as requested
    df_google_subset = df_google_subset.rename(columns={
        'rating': 'google_rating',
        'votes_count': 'google_votes_count'
    })

    # Merge Main with Google Subset on id == monument_id
    df_main_final = pd.merge(
        df_main_merged,
        df_google_subset,
        left_on='id',
        right_on='monument_id',
        how='left'
    )
    
    df_main_final.drop(columns=['monument_id'], inplace=True)

    # ---------------------------------------------------------
    # 4. PREPARE NATIONAL MONUMENT TABLE
    # ---------------------------------------------------------
    print("\n--- Processing National Monument Table ---")
    
    # Columns to move from Main to National Monument
    nat_cols_map = {
        'id': 'attraction_id',
        'ticket_price': 'ticket_price', 
        'visiting_services': 'visiting_services', 
        'ticket_price_raw': 'ticket_price_raw', 
        'short_description': 'advertising_title', 
        'ticket_price_conditions': 'price_conditions', 
        'payment_methods': 'payment_methods'
    }
    
    df_national = df_main[list(nat_cols_map.keys())].copy()
    df_national = df_national.rename(columns=nat_cols_map)
    
    # Filter: Keep only rows where these specific columns are not null (logic for "first 88 samples")
    # We assume if 'advertising_title' (short_description) is present, it's a national monument
    df_national = df_national.dropna(subset=['advertising_title'])
    print(f"National Monument table rows: {len(df_national)}")

    # ---------------------------------------------------------
    # 5. PREPARE GOOGLE MAPS DETAILS TABLE (Remaining cols)
    # ---------------------------------------------------------
    print("\n--- Processing Google Maps Details Table ---")
    
    # CHANGE: Removed 'price_level' from exclusion so it STAYS here
    cols_exclude = ['website', 'phone', 'rating', 'votes_count']
    
    # Select all columns EXCEPT those excluded
    cols_remaining = [c for c in df_google_data.columns if c not in cols_exclude]
    df_google_details = df_google_data[cols_remaining].copy()
    
    print(f"Google Maps Metadata columns: {list(df_google_details.columns)}")

    # ---------------------------------------------------------
    # 6. PREPARE FOURSQUARE DATA TABLE
    # ---------------------------------------------------------
    print("\n--- Processing Foursquare Data Table ---")
    
    # We need to add 'monument_id' to Foursquare data.
    # Main table has 'Tourpedia_id'. Foursquare data has 'Tourpedia_id'.
    
    # Create a mapping from Tourpedia_id to monument_id using the Main table
    # We must do this BEFORE dropping Tourpedia_id from Main
    id_map = df_main_final[['id', 'Tourpedia_id']].dropna()
    
    df_fs_data_final = pd.merge(
        df_fs_data,
        id_map,
        on='Tourpedia_id',
        how='left'
    )
    
    # Rename 'id' from mapping to 'monument_id'
    df_fs_data_final = df_fs_data_final.rename(columns={'id': 'monument_id'})
    
    # Rearrange columns if desired, ensure monument_id is there
    print(f"Foursquare Data rows matched: {len(df_fs_data_final)}")

    # ---------------------------------------------------------
    # 7. FINAL CLEANUP OF MAIN TABLE
    # ---------------------------------------------------------
    # Remove the columns moved to National Monument
    cols_to_remove_nat = ['short_description', 'ticket_price', 'ticket_price_conditions', 
                          'payment_methods', 'visiting_services', 'ticket_price_raw']
    
    # Remove Tourpedia_id (now that we've linked it)
    cols_to_remove_all = cols_to_remove_nat + ['Tourpedia_id']
    
    # Only drop columns that actually exist
    cols_existing_drop = [c for c in cols_to_remove_all if c in df_main_final.columns]
    df_main_final.drop(columns=cols_existing_drop, inplace=True)
    
    print(f"Final Main Table columns: {list(df_main_final.columns)}")

    # ---------------------------------------------------------
    # 8. SQLITE DATABASE CREATION
    # ---------------------------------------------------------
    print("\n--- Creating Database ---")
    conn = create_connection(DB_NAME)
    
    if conn is not None:
        cursor = conn.cursor()
        
        # Enable Foreign Keys
        cursor.execute("PRAGMA foreign_keys = ON;")

        # A. Create 'attraction' table
        # We use pandas to_sql, but it doesn't support PK/FK definitions well.
        # Best practice: Create table with SQL, then append data.
        
        # Define Schema for Attraction
        create_attraction_sql = """
        CREATE TABLE IF NOT EXISTS attraction (
            id INTEGER PRIMARY KEY,
            name TEXT,
            url TEXT,
            opening_hours TEXT,
            address TEXT,
            city TEXT,
            category TEXT,
            lat REAL,
            lng REAL,
            description TEXT,
            wiki_url TEXT,
            google_rating REAL,
            google_votes_count INTEGER,
            website TEXT,
            phone TEXT
        );
        """
        cursor.execute(create_attraction_sql)
        
        # B. Create 'national_monument' table
        create_national_sql = """
        CREATE TABLE IF NOT EXISTS national_monument (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attraction_id INTEGER,
            ticket_price TEXT,
            visiting_services TEXT,
            ticket_price_raw TEXT,
            advertising_title TEXT,
            price_conditions TEXT,
            payment_methods TEXT,
            FOREIGN KEY (attraction_id) REFERENCES attraction (id)
        );
        """
        cursor.execute(create_national_sql)

        # C. Create 'google_maps_metadata' table
        create_google_meta_sql = """
        CREATE TABLE IF NOT EXISTS google_maps_metadata (
            place_id TEXT PRIMARY KEY,
            monument_id INTEGER,
            name TEXT,
            status TEXT,
            lat REAL,
            lng REAL,
            price_level TEXT,
            address TEXT,
            city TEXT,
            map_url TEXT,
            opening_hours TEXT,
            FOREIGN KEY (monument_id) REFERENCES attraction (id)
        );
        """
        cursor.execute(create_google_meta_sql)

        # D. Create 'google_reviews' table
        create_google_reviews_sql = """
        CREATE TABLE IF NOT EXISTS google_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT,
            author_name TEXT,
            rating INTEGER,
            text TEXT,
            language TEXT,
            original_language TEXT,
            timestamp TEXT,
            author_url TEXT,
            FOREIGN KEY (place_id) REFERENCES google_maps_metadata (place_id)
        );
        """
        cursor.execute(create_google_reviews_sql)

        # E. Create 'foursquare_data' table
        create_fs_data_sql = """
        CREATE TABLE IF NOT EXISTS foursquare_data (
            Tourpedia_id INTEGER PRIMARY KEY,
            monument_id INTEGER,
            original_id TEXT,
            Foursquare_url TEXT,
            Foursquare_users_count INTEGER,
            Foursquare_checkins_count INTEGER,
            Foursquare_tip_count INTEGER,
            Foursquare_likes INTEGER,
            FOREIGN KEY (monument_id) REFERENCES attraction (id)
        );
        """
        cursor.execute(create_fs_data_sql)

        # F. Create 'foursquare_reviews' table
        create_fs_reviews_sql = """
        CREATE TABLE IF NOT EXISTS foursquare_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Tourpedia_id INTEGER,
            language TEXT,
            polarity REAL,
            text TEXT,
            time TEXT,
            words_count INTEGER,
            tokenized_text_url TEXT,
            FOREIGN KEY (Tourpedia_id) REFERENCES foursquare_data (Tourpedia_id)
        );
        """
        cursor.execute(create_fs_reviews_sql)

        # ---------------------------------------------------------
        # 9. INSERT DATA
        # ---------------------------------------------------------
        print("Writing data to SQLite...")
        
        # Use to_sql with 'append'. We need to match column names strictly or manage extra columns.
        
        try:
            df_main_final.to_sql('attraction', conn, if_exists='append', index=False)
            print(" -> attraction table populated.")
            
            df_national.to_sql('national_monument', conn, if_exists='append', index=False)
            print(" -> national_monument table populated.")
            
            # Ensure columns match for google meta
            # We must verify if 'place_id' is unique in the dataframe before insert
            df_google_details = df_google_details.drop_duplicates(subset=['place_id'])
            df_google_details.to_sql('google_maps_metadata', conn, if_exists='append', index=False)
            print(" -> google_maps_metadata table populated.")
            
            # Filter reviews to ensure FK integrity (only reviews where place_id exists in metadata)
            valid_place_ids = df_google_details['place_id'].unique()
            df_google_reviews_clean = df_google_reviews[df_google_reviews['place_id'].isin(valid_place_ids)]
            df_google_reviews_clean.to_sql('google_reviews', conn, if_exists='append', index=False)
            print(f" -> google_reviews table populated ({len(df_google_reviews_clean)} rows).")
            
            # Foursquare Data
            df_fs_data_final.to_sql('foursquare_data', conn, if_exists='append', index=False)
            print(" -> foursquare_data table populated.")
            
            # Foursquare Reviews - Ensure FK integrity
            valid_tour_ids = df_fs_data_final['Tourpedia_id'].unique()
            df_fs_reviews_clean = df_fs_reviews[df_fs_reviews['Tourpedia_id'].isin(valid_tour_ids)]
            df_fs_reviews_clean.to_sql('foursquare_reviews', conn, if_exists='append', index=False)
            print(f" -> foursquare_reviews table populated ({len(df_fs_reviews_clean)} rows).")
            
        except Exception as e:
            print(f"Error during data insertion: {e}")

        conn.commit()
        conn.close()
        print("\nSUCCESS: Database created successfully.")

if __name__ == "__main__":
    main()