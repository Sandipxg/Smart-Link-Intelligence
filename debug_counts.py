
import sqlite3
import os

DATABASE = 'smart_links.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def check_counts():
    db = get_db()
    with open("debug_counts.txt", "w", encoding="utf-8") as f:
        # Get all links
        links = db.execute("SELECT id, code FROM links").fetchall()
        
        f.write(f"Found {len(links)} links.\n")
        
        for link in links:
            link_id = link["id"]
            code = link["code"]
            
            # Get actual counts
            total_count = db.execute("SELECT COUNT(*) as c FROM visits WHERE link_id = ?", [link_id]).fetchone()["c"]
            unique_count_query = db.execute("SELECT DISTINCT ip_hash FROM visits WHERE link_id = ?", [link_id]).fetchall()
            unique_count = len(unique_count_query)
            
            f.write(f"Link {code} (ID: {link_id}): Total={total_count}, Unique={unique_count}\n")

    db.close()
    print("Done writing to debug_counts.txt")

if __name__ == "__main__":
    check_counts()
