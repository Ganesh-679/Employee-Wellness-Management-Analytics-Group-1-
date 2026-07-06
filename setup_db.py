# =========================================================================
# setup_db.py (SQLite version)
# -------------------------------------------------------------------------
# Automates the creation of the SQLite database and schema setup.
# Usage:
#   python setup_db.py
# =========================================================================

import os
import sys
import sqlite3
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Get target database file name
    db_file = os.getenv("DB_FILE", "wellness.db")
    schema_file = "schema.sql"

    print(f"Initializing SQLite database at: {os.path.abspath(db_file)}")

    # Connect to SQLite (creates the file if it doesn't exist)
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Read and execute schema.sql
        print(f"Reading schema file '{schema_file}'...")
        if not os.path.exists(schema_file):
            print(f"[ERROR] Schema file '{schema_file}' not found.")
            sys.exit(1)
            
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
            
        print("Executing schema queries...")
        cursor.executescript(schema_sql)
        conn.commit()
        print("Database schema initialized successfully! SQLite database is ready.")
        
        # Verify the created tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = cursor.fetchall()
        print("\nCreated tables:")
        for t in tables:
            print(f" - {t[0]}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] Failed to run database setup: {e}")
        if conn:
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    main()
