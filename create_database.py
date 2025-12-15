import sqlite3
import json
import os

INPUT_JSON = "paris_monuments_translated.json"
DB_NAME = "paris_monuments.db"

# CONFIGURATION: Payment Normalization
# We use a list of tuples (keyword, standard_name).
# The order matters! We check specific phrases before general ones.
PAYMENT_RULES = [
    # Credit Cards
    ("american express", "Credit Card (Amex)"),
    ("bank card", "Credit Card"),
    ("credit card", "Credit Card"),
    ("cards", "Credit Card"),
    
    # 2. Cash
    ("cash", "Cash"),
    ("coins", "Cash"),
    ("espèces", "Cash"),
    
    # 3. Holiday Vouchers (ANCV) - Catch "vacation", "holiday", "ancv"
    ("ancv", "Holiday Vouchers"),
    ("vacation", "Holiday Vouchers"),
    ("holiday", "Holiday Vouchers"),
    ("cheque-vacances", "Holiday Vouchers"),
    
    # 4. Culture & Reading Cheques
    ("lire", "Lire Cheque"),  # Covers "Lire Cheques", "Chèque Lire"
    ("read", "Lire Cheque"),  # Covers bad translation "Read Cheques"
    ("culture", "Culture Cheque"), # Covers "Culture Cheques", "Pass Culture"
    ("shop cheques", "Lire Cheque"),
    
    # 5. Standard Cheques (Must come after specific cheques above)
    ("cheque", "Cheque"),
    ("check", "Cheque"),
    
    # 6. Specific Passes
    ("passion monuments", "Passion Monuments Pass"),
    ("administrative mandate", "Administrative Mandate"),
]

def normalize_payment_method(method_raw):
    """
    Standardizes payment method strings using keyword matching.
    """
    if not method_raw:
        return None
    
    clean_str = method_raw.strip()
    lower_str = clean_str.lower()
    
    # Iterate through our rules. If a keyword is found, return the standard name.
    for keyword, standard_name in PAYMENT_RULES:
        if keyword in lower_str:
            # Special handling: If it mentions "shop" or "store" explicitly, 
            # we might want to flag it or just map it to the main type.
            # For now, we stick to the main category.
            return standard_name
            
    # Fallback: Just Capitalize First Letters if no rule matches
    return clean_str.title()

def create_schema(cursor):
    """Defines the relational schema."""
    
    # Main Monuments Table (Now includes visiting_services)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS monuments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT UNIQUE,
        short_description TEXT,
        address TEXT,
        opening_hours TEXT,
        ticket_price REAL DEFAULT 0.0,
        ticket_price_conditions TEXT,
        visiting_services TEXT,  -- Moved back to main table
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Payment Methods Table (Normalized)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        monument_id INTEGER NOT NULL,
        method TEXT NOT NULL,
        FOREIGN KEY (monument_id) REFERENCES monuments(id) ON DELETE CASCADE
    )
    ''')
    
    # Unique constraint to prevent duplicate (monument + method) pairs at DB level
    cursor.execute('''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_monument_method 
    ON payment_methods (monument_id, method)
    ''')

def insert_data(conn, data):
    cursor = conn.cursor()
    print(f"--- Inserting {len(data)} records ---")
    
    for entry in data:
        try:
            # PREPARE SERVICES (Flatten list to string) 
            services_str = None
            if entry.get('visiting_services'):
                raw_services = entry['visiting_services']
                # If it's a list, join it. If it's already a string, keep it.
                if isinstance(raw_services, list):
                    services_str = " | ".join([s.strip() for s in raw_services if s])
                else:
                    services_str = raw_services

            # INSERT MONUMENT
            cursor.execute('''
            INSERT INTO monuments (
                name, url, short_description, address, 
                opening_hours, ticket_price, ticket_price_conditions, 
                visiting_services
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.get('name'),
                entry.get('url'),
                entry.get('short_description'),
                entry.get('address'),
                entry.get('opening_hours'),
                entry.get('ticket_price'),
                entry.get('ticket_price_conditions'),
                services_str
            ))
            
            monument_id = cursor.lastrowid
            
            # INSERT PAYMENT METHODS (Normalized & Deduplicated)
            if entry.get('payment_methods'):
                raw_methods = entry['payment_methods']
                if isinstance(raw_methods, str):
                    raw_methods = raw_methods.split('|')
                
                # Use a set to handle duplicates within this specific record
                unique_methods_for_this_monument = set()
                
                for m in raw_methods:
                    normalized = normalize_payment_method(m)
                    if normalized:
                        unique_methods_for_this_monument.add(normalized)
                
                # Insert unique normalized values
                for method in unique_methods_for_this_monument:
                    try:
                        cursor.execute('''
                        INSERT INTO payment_methods (monument_id, method) 
                        VALUES (?, ?)
                        ''', (monument_id, method))
                    except sqlite3.IntegrityError:
                        # This catches duplicates if the DB constraint is triggered
                        pass

        except sqlite3.IntegrityError as e:
            print(f" -> Skipping duplicate URL: {entry.get('url')}")
        except Exception as e:
            print(f" -> Error inserting {entry.get('name')}: {e}")

    conn.commit()

def main():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"--- Removed old {DB_NAME} ---")

    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_JSON} not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON") 
    
    create_schema(conn.cursor())
    insert_data(conn, data)
    
    # Verification
    print(f"\n--- Success! Database created at '{DB_NAME}' ---")
    print("\n[Sample Data Check] Top 3 Monuments:")
    cursor = conn.cursor()
    for row in cursor.execute("SELECT name, visiting_services FROM monuments LIMIT 3"):
        print(row)
        
    print("\n[Sample Data Check] Unique Payment Methods in DB:")
    for row in cursor.execute("SELECT DISTINCT method FROM payment_methods ORDER BY method"):
        print(f"- {row[0]}")
        
    conn.close()

if __name__ == "__main__":
    main()