import sqlite3
import os
from graphviz import Digraph

DB_NAME = "monuments_database.db"
OUTPUT_FILENAME = "entity_relationship_diagram"

def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(f"Error connecting: {e}")
        return None

def get_schema(conn):
    """
    Extracts tables, columns, and foreign keys from SQLite.
    Returns a dictionary structure of the schema.
    """
    cursor = conn.cursor()
    schema = {}
    
    # 1. Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        # Get Columns: (cid, name, type, notnull, dflt_value, pk)
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        # Get Foreign Keys: (id, seq, table, from, to, on_update, on_delete, match)
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()
        
        schema[table] = {
            'columns': columns,
            'fks': fks
        }
    return schema

def generate_erd(schema):
    """
    Generates a Graphviz Digraph object from the schema.
    """
    # Initialize Digraph with left-to-right direction for better layout
    dot = Digraph('ERD', comment='Monuments Database Schema')
    dot.attr(rankdir='LR', splines='ortho', nodesep='0.8', ranksep='1.0')
    dot.attr('node', shape='plaintext', fontname='Helvetica')
    
    # Create Nodes (Tables)
    for table, details in schema.items():
        # Build an HTML-like label for the node
        # <TABLE>...</TABLE> syntax allows formatting columns nicely
        
        rows_html = ""
        for col in details['columns']:
            col_name = col[1]
            col_type = col[2]
            is_pk = col[5] > 0
            
            # Styling for PK and Standard columns
            if is_pk:
                # Bold and Golden key icon (using text 🔑)
                rows_html += f'''
                <TR>
                    <TD PORT="{col_name}" ALIGN="LEFT" BGCOLOR="#e1f5fe"><B>{col_name} 🔑</B></TD>
                    <TD ALIGN="RIGHT" BGCOLOR="#e1f5fe"><FONT POINT-SIZE="10" COLOR="gray">{col_type}</FONT></TD>
                </TR>
                '''
            else:
                rows_html += f'''
                <TR>
                    <TD PORT="{col_name}" ALIGN="LEFT">{col_name}</TD>
                    <TD ALIGN="RIGHT"><FONT POINT-SIZE="10" COLOR="gray">{col_type}</FONT></TD>
                </TR>
                '''

        table_label = f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
            <TR><TD COLSPAN="2" BGCOLOR="#2c3e50"><FONT COLOR="white"><B>{table.upper()}</B></FONT></TD></TR>
            {rows_html}
        </TABLE>>'''
        
        dot.node(table, label=table_label)

    # Create Edges (Relationships)
    for table, details in schema.items():
        for fk in details['fks']:
            # fk structure: (id, seq, target_table, source_col, target_col, ...)
            target_table = fk[2]
            source_col = fk[3]
            target_col = fk[4]
            
            # Draw edge from Source Table:Col -> Target Table:Col
            # We use the PORT feature to connect exactly to the column name
            dot.edge(f'{table}:{source_col}', f'{target_table}:{target_col}', 
                     label='', color='#7f8c8d', arrowtail='crow', dir='both')

    return dot

def main():
    conn = create_connection(DB_NAME)
    if not conn:
        return

    print("--- Extracting Schema ---")
    schema = get_schema(conn)
    conn.close()

    print("--- Generating Diagram ---")
    try:
        dot = generate_erd(schema)
        
        # This renders the file to .png
        # 'view=True' opens it automatically
        output_path = dot.render(filename=OUTPUT_FILENAME, format='png', view=False)
        print(f"SUCCESS: Diagram saved to {output_path}")
        
    except Exception as e:
        print("\n[!] Graphviz Executable Not Found or Error Occurred")
        print(f"Error details: {e}")
        print("-" * 50)
        print("fallback instructions:")
        print("1. A file named 'entity_relationship_diagram' (no extension) has been created.")
        print("2. Open this file in a text editor (Notepad).")
        print("3. Copy the content.")
        print("4. Go to: https://edotor.net/ ")
        print("5. Paste the content there to download your image.")

if __name__ == "__main__":
    main()