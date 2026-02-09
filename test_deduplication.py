"""
Test to verify deduplication logic is working
"""
import sqlite3
from datetime import datetime, timedelta

def test_deduplication_query():
    """Test the SQL query logic for deduplication"""
    
    # Create in-memory test database
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create visits table
    cursor.execute('''
        CREATE TABLE visits (
            id INTEGER PRIMARY KEY,
            link_id INTEGER,
            ip_hash TEXT,
            ts TEXT
        )
    ''')
    
    # Test scenario: Same IP visiting same link
    now = datetime.utcnow()
    link_id = 1
    ip_hash = "test_hash_12345"
    
    # Insert first visit
    cursor.execute(
        "INSERT INTO visits (link_id, ip_hash, ts) VALUES (?, ?, ?)",
        [link_id, ip_hash, now.isoformat()]
    )
    conn.commit()
    
    print("=" * 80)
    print("DEDUPLICATION LOGIC TEST")
    print("=" * 80)
    
    # Test 1: Check within 5 seconds (should find duplicate)
    test_time_1 = (now + timedelta(seconds=5)).isoformat()
    cursor.execute(
        """
        SELECT id FROM visits
        WHERE link_id = ? AND ip_hash = ?
        AND datetime(ts) > datetime(?, '-10 seconds')
        LIMIT 1
        """,
        [link_id, ip_hash, test_time_1]
    )
    result_1 = cursor.fetchone()
    
    print(f"\nTest 1: Check 5 seconds after first visit")
    print(f"  Expected: Should find recent visit (duplicate)")
    print(f"  Result: {'✅ FOUND (duplicate blocked)' if result_1 else '✗ NOT FOUND (would allow duplicate)'}")
    
    # Test 2: Check within 9 seconds (should still find duplicate)
    test_time_2 = (now + timedelta(seconds=9)).isoformat()
    cursor.execute(
        """
        SELECT id FROM visits
        WHERE link_id = ? AND ip_hash = ?
        AND datetime(ts) > datetime(?, '-10 seconds')
        LIMIT 1
        """,
        [link_id, ip_hash, test_time_2]
    )
    result_2 = cursor.fetchone()
    
    print(f"\nTest 2: Check 9 seconds after first visit")
    print(f"  Expected: Should find recent visit (duplicate)")
    print(f"  Result: {'✅ FOUND (duplicate blocked)' if result_2 else '✗ NOT FOUND (would allow duplicate)'}")
    
    # Test 3: Check after 15 seconds (should NOT find - allow new visit)
    test_time_3 = (now + timedelta(seconds=15)).isoformat()
    cursor.execute(
        """
        SELECT id FROM visits
        WHERE link_id = ? AND ip_hash = ?
        AND datetime(ts) > datetime(?, '-10 seconds')
        LIMIT 1
        """,
        [link_id, ip_hash, test_time_3]
    )
    result_3 = cursor.fetchone()
    
    print(f"\nTest 3: Check 15 seconds after first visit")
    print(f"  Expected: Should NOT find recent visit (allow new visit)")
    print(f"  Result: {'✗ FOUND (would block legitimate visit)' if result_3 else '✅ NOT FOUND (allows new visit)'}")
    
    # Test 4: Different IP (should NOT find - allow new visit)
    different_ip = "different_hash_67890"
    cursor.execute(
        """
        SELECT id FROM visits
        WHERE link_id = ? AND ip_hash = ?
        AND datetime(ts) > datetime(?, '-10 seconds')
        LIMIT 1
        """,
        [link_id, different_ip, test_time_1]
    )
    result_4 = cursor.fetchone()
    
    print(f"\nTest 4: Different IP address (5 seconds later)")
    print(f"  Expected: Should NOT find (different user)")
    print(f"  Result: {'✗ FOUND (would block different user)' if result_4 else '✅ NOT FOUND (allows different user)'}")
    
    # Test 5: Different link (should NOT find - allow new visit)
    different_link = 2
    cursor.execute(
        """
        SELECT id FROM visits
        WHERE link_id = ? AND ip_hash = ?
        AND datetime(ts) > datetime(?, '-10 seconds')
        LIMIT 1
        """,
        [different_link, ip_hash, test_time_1]
    )
    result_5 = cursor.fetchone()
    
    print(f"\nTest 5: Same IP, different link (5 seconds later)")
    print(f"  Expected: Should NOT find (different link)")
    print(f"  Result: {'✗ FOUND (would block different link)' if result_5 else '✅ NOT FOUND (allows different link)'}")
    
    print("\n" + "=" * 80)
    
    # Summary
    all_passed = (
        result_1 is not None and  # Should find duplicate
        result_2 is not None and  # Should find duplicate
        result_3 is None and      # Should allow after 15s
        result_4 is None and      # Should allow different IP
        result_5 is None          # Should allow different link
    )
    
    if all_passed:
        print("✅ ALL TESTS PASSED - Deduplication logic is correct!")
    else:
        print("✗ SOME TESTS FAILED - Check the logic!")
    
    print("=" * 80)
    
    conn.close()
    return all_passed

if __name__ == "__main__":
    success = test_deduplication_query()
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. RESTART your Flask app (Ctrl+C then 'python app.py')")
    print("2. Click a link from WhatsApp")
    print("3. Run 'python debug_visits.py' to verify no duplicates")
    print("=" * 80)
    
    exit(0 if success else 1)
