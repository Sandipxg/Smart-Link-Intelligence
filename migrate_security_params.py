
import sqlite3

try:
    conn = sqlite3.connect('smart_links.db')
    cursor = conn.cursor()
    
    # Check current columns to avoid duplicate errors
    cursor.execute("PRAGMA table_info(behavior_rules)")
    columns = [col[1] for col in cursor.fetchall()]
    
    new_columns = [
        ("rapid_click_limit", "REAL DEFAULT 0.3"),
        ("health_kill_switch", "INTEGER DEFAULT 5"),
        ("detection_window_minutes", "INTEGER DEFAULT 5")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE behavior_rules ADD COLUMN {col_name} {col_type}")
    
    conn.commit()
    print("Database migration successful!")
except Exception as e:
    print(f"Error migrating database: {e}")
finally:
    if conn:
        conn.close()
