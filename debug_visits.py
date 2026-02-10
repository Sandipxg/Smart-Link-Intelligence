"""
Debug script to see what's happening with visits
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('smart_links.db')
cursor = conn.cursor()

print("=" * 100)
print("RECENT VISITS - Last 20 entries")
print("=" * 100)

cursor.execute("""
    SELECT 
        id,
        link_id,
        datetime(ts) as timestamp,
        ip_hash,
        referrer,
        SUBSTR(user_agent, 1, 60) as user_agent_preview
    FROM visits 
    ORDER BY ts DESC 
    LIMIT 20
""")

rows = cursor.fetchall()

if not rows:
    print("No visits found in database yet.")
else:
    for row in rows:
        visit_id, link_id, timestamp, ip_hash, referrer, ua = row
        print(f"\nID: {visit_id} | Link: {link_id} | Time: {timestamp}")
        print(f"  IP Hash: {ip_hash[:16]}...")
        print(f"  Referrer: {referrer}")
        print(f"  User-Agent: {ua}...")

print("\n" + "=" * 100)
print("DUPLICATE DETECTION TEST")
print("=" * 100)

# Group by link_id and ip_hash to find potential duplicates
cursor.execute("""
    SELECT 
        link_id,
        ip_hash,
        COUNT(*) as visit_count,
        GROUP_CONCAT(datetime(ts), ' | ') as timestamps
    FROM visits
    GROUP BY link_id, ip_hash
    HAVING COUNT(*) > 1
    ORDER BY visit_count DESC
    LIMIT 10
""")

dup_rows = cursor.fetchall()

if not dup_rows:
    print("No duplicate visits found (same IP + same link).")
else:
    print("Found potential duplicates (same IP visiting same link multiple times):\n")
    for link_id, ip_hash, count, timestamps in dup_rows:
        print(f"Link ID: {link_id} | IP: {ip_hash[:16]}... | Visits: {count}")
        print(f"  Timestamps: {timestamps}")
        
        # Check time difference between visits
        cursor.execute("""
            SELECT datetime(ts) as ts
            FROM visits
            WHERE link_id = ? AND ip_hash = ?
            ORDER BY ts
        """, [link_id, ip_hash])
        
        times = [row[0] for row in cursor.fetchall()]
        if len(times) >= 2:
            # Calculate time difference between first two visits
            t1 = datetime.fromisoformat(times[0])
            t2 = datetime.fromisoformat(times[1])
            diff_seconds = (t2 - t1).total_seconds()
            print(f"  Time between first 2 visits: {diff_seconds:.1f} seconds")
            if diff_seconds < 10:
                print(f"  ⚠️  DUPLICATE DETECTED (< 10 seconds) - Should have been prevented!")
        print()

print("=" * 100)
print("VISITS PER LINK")
print("=" * 100)

cursor.execute("""
    SELECT 
        l.code,
        l.primary_url,
        COUNT(v.id) as total_visits,
        COUNT(DISTINCT v.ip_hash) as unique_visitors
    FROM links l
    LEFT JOIN visits v ON l.id = v.link_id
    GROUP BY l.id
    ORDER BY total_visits DESC
""")

link_rows = cursor.fetchall()
for code, url, total, unique in link_rows:
    print(f"\nLink: {code}")
    print(f"  URL: {url[:60]}...")
    print(f"  Total Visits: {total}")
    print(f"  Unique Visitors: {unique}")
    if total > unique:
        print(f"  ⚠️  {total - unique} duplicate visits detected!")

conn.close()
