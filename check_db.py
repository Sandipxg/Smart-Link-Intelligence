import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

print("=" * 60)
print("DATABASE SCHEMA INSPECTION")
print("=" * 60)

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"\nTotal Tables: {len(tables)}\n")

for table in tables:
    table_name = table[0]
    print(f"\n{'='*60}")
    print(f"TABLE: {table_name}")
    print(f"{'='*60}")
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print("\nColumns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''} {'NOT NULL' if col[3] else ''}")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"\nRow Count: {count}")

print("\n" + "=" * 60)
print("CHECKING ADMIN PANEL SPECIFIC TABLES")
print("=" * 60)

admin_tables = ['admin_users', 'ad_impressions', 'admin_activity_log', 'user_activity', 'ad_display_assignments']

for table in admin_tables:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    exists = cursor.fetchone()
    status = "✓ EXISTS" if exists else "✗ MISSING"
    print(f"{table}: {status}")

conn.close()
print("\n" + "=" * 60)
