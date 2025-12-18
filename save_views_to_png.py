import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os

# Configuration
DB_NAME = "monuments_database.db"
OUTPUT_FOLDER = "view_visualizations"
CHAR_LIMIT = 30  # Maximum characters allowed per cell

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def smart_truncate(val):
    """
    Truncates a string to CHAR_LIMIT and adds '...' if it's too long.
    Leaves numbers and short strings alone.
    """
    str_val = str(val)
    if len(str_val) > CHAR_LIMIT:
        return str_val[:CHAR_LIMIT] + "..."
    return val

def save_df_as_png(df, filename, title, col_width=3.0, row_height=0.6, font_size=10):
    if df.empty:
        print(f"Skipping {filename}: DataFrame is empty.")
        return

    # --- KEY FIX: Truncate ALL data before plotting ---
    # Apply truncation to every single cell in the DataFrame
    df_clean = df.copy()
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].apply(smart_truncate)

    # Calculate figure size
    n_cols = len(df_clean.columns)
    n_rows = len(df_clean)
    
    # Dynamic sizing
    fig_width = max(n_cols * col_width, 10) 
    fig_height = max(n_rows * row_height + 1.5, 3)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('tight')
    ax.axis('off')
    
    # Create the table
    the_table = ax.table(
        cellText=df_clean.values,
        colLabels=df_clean.columns,
        loc='center',
        cellLoc='center' # Center align text
    )
    
    # Styling
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(font_size)
    the_table.scale(1, 1.8) # Increased padding for better readability
    
    # Color styling
    for i, key in enumerate(the_table.get_celld().keys()):
        cell = the_table.get_celld()[key]
        row_idx = key[0]
        if row_idx == 0: # Header
            cell.set_facecolor('#40466e')
            cell.set_text_props(color='w', weight='bold')
        elif row_idx > 0 and row_idx % 2 == 0: # Even rows
            cell.set_facecolor('#f1f1f2')

    # Add Title
    plt.title(title, fontsize=16, pad=20, fontweight='bold', color='#333333')
    
    # Save
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    plt.savefig(filepath, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved: {filepath}")

def main():
    conn = create_connection(DB_NAME)
    if not conn:
        return

    print("--- Generating Visualizations (Truncated for Safety) ---")

    # 1. Comprehensive Popularity (Top 10)
    query_pop = "SELECT * FROM view_comprehensive_popularity LIMIT 10"
    df_pop = pd.read_sql_query(query_pop, conn)
    save_df_as_png(df_pop, "view_01_popularity_top10.png", "Top 10 Most Popular Monuments")

    # 2. Hidden Gems (Top 10)
    query_gems = "SELECT * FROM view_hidden_gems LIMIT 10"
    df_gems = pd.read_sql_query(query_gems, conn)
    save_df_as_png(df_gems, "view_02_hidden_gems_top10.png", "Top 10 Hidden Gems")

    # 3. Category Performance (All)
    query_cat = "SELECT * FROM view_category_performance"
    df_cat = pd.read_sql_query(query_cat, conn)
    save_df_as_png(df_cat, "view_03_category_performance.png", "Category Performance")

    # 4. Price vs Quality (Top 10)
    query_price = "SELECT * FROM view_price_vs_quality LIMIT 10"
    df_price = pd.read_sql_query(query_price, conn)
    save_df_as_png(df_price, "view_04_price_vs_quality_top10.png", "Price vs Quality (Top 10)")

    # 5. National Monument Prestige (Top 10)
    query_nat = "SELECT * FROM view_national_monument_prestige LIMIT 10"
    df_nat = pd.read_sql_query(query_nat, conn)
    save_df_as_png(df_nat, "view_05_national_monuments_top10.png", "National Monuments Prestige (Top 10)")

    conn.close()
    print(f"\nSuccess! All images saved in '{OUTPUT_FOLDER}/' with max {CHAR_LIMIT} chars per cell.")

if __name__ == "__main__":
    main()