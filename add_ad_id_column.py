import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")

def migrate():
    print(f"Connecting to database at {DATABASE}")
    conn = sqlite3.connect(DATABASE)
    
    try:
        # Check if column already exists
        cursor = conn.execute("PRAGMA table_info(ad_impressions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'ad_id' in columns:
            print("Column 'ad_id' already exists in 'ad_impressions'. Skipping.")
        else:
            print("Adding 'ad_id' column to 'ad_impressions' table...")
            conn.execute("ALTER TABLE ad_impressions ADD COLUMN ad_id INTEGER REFERENCES personalized_ads(id)")
            print("Column added successfully.")
            
        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
