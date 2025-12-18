import sqlite3
import pandas as pd

DB_NAME = "monuments_database.db"

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def create_views(conn):
    cursor = conn.cursor()
    print("--- Creating Views ---")

    # 1. VIEW: Comprehensive Popularity (Google + Foursquare)
    # Why: Determine the "Megastars" by combining data from two different social platforms.
    sql_popularity = """
    DROP VIEW IF EXISTS view_comprehensive_popularity;
    CREATE VIEW view_comprehensive_popularity AS
    SELECT 
        a.name,
        a.category,
        a.city,
        a.google_rating,
        a.google_votes_count,
        f.Foursquare_checkins_count,
        f.Foursquare_likes,
        (IFNULL(a.google_votes_count, 0) + IFNULL(f.Foursquare_checkins_count, 0)) as total_engagement
    FROM attraction a
    LEFT JOIN foursquare_data f ON a.id = f.monument_id
    ORDER BY total_engagement DESC;
    """
    cursor.executescript(sql_popularity)
    print(" -> Created 'view_comprehensive_popularity'")

    # 2. VIEW: Hidden Gems
    # Why: High Quality (Rating > 4.5) but Low Volume (Votes < 100). 
    # Great for "Secret spots" recommendations.
    sql_hidden_gems = """
    DROP VIEW IF EXISTS view_hidden_gems;
    CREATE VIEW view_hidden_gems AS
    SELECT 
        a.name,
        a.category,
        a.city,
        a.google_rating,
        a.google_votes_count,
        a.description
    FROM attraction a
    WHERE a.google_rating >= 4.5 
      AND a.google_votes_count < 500
      AND a.google_votes_count > 10  -- Filter out zero-vote places
    ORDER BY a.google_rating DESC, a.google_votes_count DESC;
    """
    cursor.executescript(sql_hidden_gems)
    print(" -> Created 'view_hidden_gems'")

    # 3. VIEW: Category Analytics
    # Why: Strategic view to see which types of monuments perform best.
    sql_category = """
    DROP VIEW IF EXISTS view_category_performance;
    CREATE VIEW view_category_performance AS
    SELECT 
        category,
        COUNT(*) as monument_count,
        ROUND(AVG(google_rating), 2) as avg_rating,
        SUM(google_votes_count) as total_google_votes,
        ROUND(AVG(f.Foursquare_checkins_count), 0) as avg_checkins
    FROM attraction a
    LEFT JOIN foursquare_data f ON a.id = f.monument_id
    WHERE category IS NOT NULL
    GROUP BY category
    ORDER BY total_google_votes DESC;
    """
    cursor.executescript(sql_category)
    print(" -> Created 'view_category_performance'")

    # 4. VIEW: Price vs Quality
    # Why: Joins the Google Metadata price_level with ratings.
    sql_price = """
    DROP VIEW IF EXISTS view_price_vs_quality;
    CREATE VIEW view_price_vs_quality AS
    SELECT 
        a.name,
        gm.price_level,
        a.google_rating,
        a.google_votes_count
    FROM attraction a
    JOIN google_maps_metadata gm ON a.id = gm.monument_id
    WHERE gm.price_level IS NOT NULL
    ORDER BY gm.price_level DESC, a.google_rating DESC;
    """
    cursor.executescript(sql_price)
    print(" -> Created 'view_price_vs_quality'")

    # 5. VIEW: National Monument Prestige
    # Why: Focuses purely on the official "National Monuments" to see their stats.
    sql_national = """
    DROP VIEW IF EXISTS view_national_monument_prestige;
    CREATE VIEW view_national_monument_prestige AS
    SELECT 
        a.name,
        n.ticket_price,
        n.visiting_services,
        a.google_rating,
        f.Foursquare_likes
    FROM national_monument n
    JOIN attraction a ON n.attraction_id = a.id
    LEFT JOIN foursquare_data f ON a.id = f.monument_id
    ORDER BY a.google_rating DESC;
    """
    cursor.executescript(sql_national)
    print(" -> Created 'view_national_monument_prestige'")

    conn.commit()

def preview_views(conn):
    """Prints a sneak peek of the new views using Pandas."""
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    views = [
        "view_comprehensive_popularity", 
        "view_hidden_gems", 
        "view_category_performance",
        "view_price_vs_quality",
        "view_national_monument_prestige"
    ]

    print("\n" + "="*50)
    print("   PREVIEW OF GENERATED VIEWS")
    print("="*50)

    for v in views:
        print(f"\n--- Top 5 rows from: {v} ---")
        try:
            df = pd.read_sql_query(f"SELECT * FROM {v} LIMIT 5", conn)
            if df.empty:
                print("[No data returned - view might be empty based on current data]")
            else:
                print(df.to_string(index=False))
        except Exception as e:
            print(f"Error querying view {v}: {e}")

def main():
    conn = create_connection(DB_NAME)
    if conn:
        create_views(conn)
        preview_views(conn)
        conn.close()
        print("\nViews created successfully. You can now use these View names like tables in SQL.")

if __name__ == "__main__":
    main()