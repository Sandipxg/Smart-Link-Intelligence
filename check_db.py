
import sqlite3

try:
    conn = sqlite3.connect('smart_links.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(behavior_rules);")
    columns = cursor.fetchall()
    print("Columns in behavior_rules table:")
    for col in columns:
        print(col)
except Exception as e:
    print(f"Error: {e}")
finally:
    if conn:
        conn.close()
