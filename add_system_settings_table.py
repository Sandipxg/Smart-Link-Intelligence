import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")

def migrate():
    print(f"Connecting to database at {DATABASE}")
    conn = sqlite3.connect(DATABASE)
    
    try:
        print("Creating 'system_settings' table...")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT
            )
        """)
        print("Table created successfully.")
        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
