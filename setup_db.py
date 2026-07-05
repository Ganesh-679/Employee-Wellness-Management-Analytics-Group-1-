# =========================================================================
# setup_db.py
# -------------------------------------------------------------------------
# Automates the creation of the database and setup of database tables.
# Usage:
#   python setup_db.py --password your_postgres_password
# Or fill in `.env` and run:
#   python setup_db.py
# =========================================================================

import os
import sys
import argparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Set up WellSpring Analytics PostgreSQL Database")
    parser.add_argument("--host", default=os.getenv("DB_HOST", "localhost"), help="PostgreSQL host (default: localhost)")
    parser.add_argument("--port", default=os.getenv("DB_PORT", "5432"), help="PostgreSQL port (default: 5432)")
    parser.add_argument("--user", default=os.getenv("DB_USER", "postgres"), help="PostgreSQL user (default: postgres)")
    parser.add_argument("--password", default=os.getenv("DB_PASSWORD", ""), help="PostgreSQL password")
    parser.add_argument("--dbname", default=os.getenv("DB_NAME", "wellness_db"), help="Target database name (default: wellness_db)")
    parser.add_argument("--schema", default="schema.sql", help="Path to schema.sql file")
    
    args = parser.parse_args()

    password = args.password
    if not password:
        # Fallback to check environment variable directly
        password = os.getenv("DB_PASSWORD", "")
    
    if not password:
        print("Warning: Database password is not set in .env or passed as --password.")
        print("Attempting to connect with an empty password...")

    print(f"Connecting to PostgreSQL server at {args.host}:{args.port} as user '{args.user}'...")
    
    # 1. Connect to the default 'postgres' database to check if the target database exists
    conn = None
    try:
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=password,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if the database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (args.dbname,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{args.dbname}' does not exist. Creating database '{args.dbname}'...")
            cursor.execute(f'CREATE DATABASE "{args.dbname}";')
            print(f"Database '{args.dbname}' created successfully.")
        else:
            print(f"Database '{args.dbname}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("Please check your PostgreSQL settings in `.env` or pass the password using `--password`.")
        sys.exit(1)

    # 2. Connect to the target database and execute schema.sql
    print(f"\nConnecting to target database '{args.dbname}'...")
    try:
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=password,
            database=args.dbname
        )
        cursor = conn.cursor()
        
        # Read and execute schema.sql
        print(f"Reading schema file '{args.schema}'...")
        if not os.path.exists(args.schema):
            print(f"[ERROR] Schema file '{args.schema}' not found.")
            sys.exit(1)
            
        with open(args.schema, 'r') as f:
            schema_sql = f.read()
            
        print("Executing schema queries...")
        cursor.execute(schema_sql)
        conn.commit()
        print("Database schema initialized successfully! Tables and indexes are ready.")
        
        # Verify the created tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print("\nCreated tables in public schema:")
        for t in tables:
            print(f" - {t[0]}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"\n[ERROR] Failed to run database schema: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
