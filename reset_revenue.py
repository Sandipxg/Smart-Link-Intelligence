import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")

def reset_revenue():
    print(f"Connecting to database at {DATABASE}")
    conn = sqlite3.connect(DATABASE)
    
    try:
        print("Clearing 'ad_impressions' table...")
        current_count = conn.execute("SELECT COUNT(*) FROM ad_impressions").fetchone()[0]
        print(f"Deleting {current_count} rows...")
        
        conn.execute("DELETE FROM ad_impressions")
        # Optional: Reset auto-increment logic? Not strictly necessary for ID but cleaner.
        # conn.execute("DELETE FROM sqlite_sequence WHERE name='ad_impressions'")
        
        conn.commit()
        print("Ad impressions database cleared successfully.")
        
    except Exception as e:
        print(f"Error during reset: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_revenue()
