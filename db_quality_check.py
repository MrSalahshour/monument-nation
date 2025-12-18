import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Configuration
DB_NAME = "monuments_database.db"
OUTPUT_FOLDER = "qa_reports"

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def save_df_as_png(df, filename, title, col_width=3.0, row_height=0.6, font_size=10):
    """
    Renders a Pandas DataFrame as a PNG image using Matplotlib.
    """
    if df.empty:
        print(f"Skipping {filename}: DataFrame is empty.")
        return

    # Calculate figure size based on rows and columns
    n_cols = len(df.columns)
    n_rows = len(df)
    
    fig_width = max(n_cols * col_width, 8) 
    fig_height = max(n_rows * row_height + 1, 2)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('tight')
    ax.axis('off')
    
    # Create the table
    the_table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc='center',
        cellLoc='center'
    )
    
    # Styling
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(font_size)
    the_table.scale(1, 1.5) # Add some padding to cells

    # Add Title
    plt.title(title, fontsize=14, pad=20, fontweight='bold')
    
    # Save
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    plt.savefig(filepath, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved: {filepath}")

def analyze_completeness(df, table_name):
    """Analyzes missing values and saves as PNG."""
    total_rows = len(df)
    missing = df.isnull().sum()
    missing_pct = (df.isnull().sum() / total_rows) * 100
    
    report_df = pd.DataFrame({
        'Column': df.columns,
        'Missing Count': missing.values,
        'Missing (%)': missing_pct.values.round(2),
        'Total Rows': total_rows
    })
    
    # Sort by missing % to highlight issues
    report_df = report_df.sort_values(by='Missing (%)', ascending=False)
    
    save_df_as_png(report_df, f"completeness_{table_name}.png", f"Completeness: {table_name}")

def check_referential_integrity(conn, relationships):
    """Checks orphan records and saves a single summary PNG."""
    results = []
    cursor = conn.cursor()
    
    for child, fk, parent, pk in relationships:
        # FIX: Assign variables BEFORE using them in the query string
        child_table, fk_col, parent_table, pk_col = child, fk, parent, pk
        
        query = f"""
            SELECT COUNT(*) 
            FROM {child_table} c 
            LEFT JOIN {parent_table} p ON c.{fk_col} = p.{pk_col} 
            WHERE p.{pk_col} IS NULL
        """
        
        cursor.execute(query)
        orphan_count = cursor.fetchone()[0]
        status = "PASS" if orphan_count == 0 else "FAIL"
        
        results.append({
            "Relationship": f"{child_table} -> {parent_table}",
            "Keys": f"({fk_col} = {pk_col})",
            "Orphan Count": orphan_count,
            "Status": status
        })
        
    df_res = pd.DataFrame(results)
    save_df_as_png(df_res, "integrity_check.png", "Referential Integrity Check", col_width=4.0)

def analyze_numeric_distribution(df, table_name, columns):
    """Saves numeric stats as PNG."""
    existing_cols = [c for c in columns if c in df.columns]
    
    if not existing_cols:
        return

    stats = df[existing_cols].describe().transpose().reset_index()
    stats = stats.rename(columns={'index': 'Column'})
    
    # Add Negative Value Check
    neg_counts = df[existing_cols].apply(lambda x: (x < 0).sum()).values
    stats['Negative Values'] = neg_counts
    
    # Select and round columns for clean display
    cols_to_show = ['Column', 'count', 'mean', 'min', '50%', 'max', 'std', 'Negative Values']
    stats = stats[cols_to_show].round(2)
    
    save_df_as_png(stats, f"stats_{table_name}.png", f"Statistics: {table_name}")

def main():
    conn = create_connection(DB_NAME)
    if not conn:
        return

    tables = [
        "attraction", 
        "national_monument", 
        "google_maps_metadata", 
        "google_reviews", 
        "foursquare_data", 
        "foursquare_reviews"
    ]
    
    dataframes = {}
    summary_data = []

    # 1. LOAD DATA & SUMMARY
    print("--- Loading Data ---")
    for t in tables:
        try:
            df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
            dataframes[t] = df
            summary_data.append({"Table Name": t, "Row Count": len(df), "Columns": len(df.columns)})
        except Exception as e:
            print(f"Error reading table {t}: {e}")
    
    save_df_as_png(pd.DataFrame(summary_data), "00_db_overview.png", "Database Overview")

    # 2. COMPLETENESS (Missing Data)
    print("--- Generating Completeness Reports ---")
    for t in tables:
        if t in dataframes:
            analyze_completeness(dataframes[t], t)

    # 3. REFERENTIAL INTEGRITY
    print("--- Generating Integrity Report ---")
    relationships = [
        ("national_monument", "attraction_id", "attraction", "id"),
        ("google_maps_metadata", "monument_id", "attraction", "id"),
        ("google_reviews", "place_id", "google_maps_metadata", "place_id"),
        ("foursquare_data", "monument_id", "attraction", "id"),
        ("foursquare_reviews", "Tourpedia_id", "foursquare_data", "Tourpedia_id")
    ]
    check_referential_integrity(conn, relationships)

    # 4. STATISTICAL VALIDITY
    print("--- Generating Statistical Reports ---")
    
    if 'attraction' in dataframes:
        analyze_numeric_distribution(dataframes['attraction'], 'attraction', 
                                     ['google_rating', 'google_votes_count', 'lat', 'lng'])
    
    if 'foursquare_data' in dataframes:
        analyze_numeric_distribution(dataframes['foursquare_data'], 'foursquare_data', 
                                     ['Foursquare_users_count', 'Foursquare_checkins_count', 'Foursquare_likes'])
    
    if 'google_reviews' in dataframes:
        analyze_numeric_distribution(dataframes['google_reviews'], 'google_reviews', ['rating'])
    
    # 5. CATEGORICAL CHECKS
    print("--- Generating Categorical Reports ---")
    
    if 'attraction' in dataframes:
        df_main = dataframes['attraction']
        cat_counts = df_main['category'].value_counts().head(15).reset_index()
        cat_counts.columns = ['Category', 'Count']
        save_df_as_png(cat_counts, "category_distribution.png", "Top 15 Categories (Attraction)", col_width=4.0)

    if 'google_maps_metadata' in dataframes:
        df_meta = dataframes['google_maps_metadata']
        if 'price_level' in df_meta.columns:
            price_counts = df_meta['price_level'].value_counts(dropna=False).reset_index()
            price_counts.columns = ['Price Level', 'Count']
            save_df_as_png(price_counts, "price_level_distribution.png", "Price Level Distribution")

    conn.close()
    print(f"\nAll reports saved in '{OUTPUT_FOLDER}/'")

if __name__ == "__main__":
    main()