"""
Database Migration Script for Admin Panel
Adds performance indexes and optimizations for real-time data access
"""

import sqlite3
import os

def migrate_admin_database():
    """Add indexes and optimize admin panel database"""
    DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")
    
    print("=" * 60)
    print("ADMIN PANEL DATABASE MIGRATION")
    print("=" * 60)
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Add performance indexes
    print("\n[1/4] Creating performance indexes...")
    indexes = [
        ("idx_visits_link_id", "CREATE INDEX IF NOT EXISTS idx_visits_link_id ON visits(link_id)"),
        ("idx_visits_timestamp", "CREATE INDEX IF NOT EXISTS idx_visits_timestamp ON visits(ts)"),
        ("idx_ad_impressions_user_id", "CREATE INDEX IF NOT EXISTS idx_ad_impressions_user_id ON ad_impressions(user_id)"),
        ("idx_ad_impressions_link_id", "CREATE INDEX IF NOT EXISTS idx_ad_impressions_link_id ON ad_impressions(link_id)"),
        ("idx_ad_impressions_timestamp", "CREATE INDEX IF NOT EXISTS idx_ad_impressions_timestamp ON ad_impressions(timestamp)"),
        ("idx_user_activity_user_id", "CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity(user_id)"),
        ("idx_user_activity_timestamp", "CREATE INDEX IF NOT EXISTS idx_user_activity_timestamp ON user_activity(timestamp)"),
        ("idx_links_user_id", "CREATE INDEX IF NOT EXISTS idx_links_user_id ON links(user_id)"),
        ("idx_links_created_at", "CREATE INDEX IF NOT EXISTS idx_links_created_at ON links(created_at)"),
        ("idx_personalized_ads_user_id", "CREATE INDEX IF NOT EXISTS idx_personalized_ads_user_id ON personalized_ads(user_id)"),
        ("idx_personalized_ads_active", "CREATE INDEX IF NOT EXISTS idx_personalized_ads_active ON personalized_ads(is_active)"),
        ("idx_admin_activity_timestamp", "CREATE INDEX IF NOT EXISTS idx_admin_activity_timestamp ON admin_activity_log(timestamp)"),
    ]
    
    for index_name, index_sql in indexes:
        try:
            cursor.execute(index_sql)
            print(f"  [OK] Created index: {index_name}")
        except Exception as e:
            print(f"  [FAIL] Failed to create {index_name}: {e}")
    
    # Enable WAL mode for better concurrent access
    print("\n[2/4] Enabling WAL mode for concurrent access...")
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        result = cursor.fetchone()
        print(f"  [OK] Journal mode set to: {result[0]}")
    except Exception as e:
        print(f"  [FAIL] Failed to enable WAL mode: {e}")
    
    # Optimize database
    print("\n[3/4] Optimizing database...")
    try:
        cursor.execute("PRAGMA optimize")
        print("  [OK] Database optimized")
    except Exception as e:
        print(f"  [FAIL] Failed to optimize: {e}")
    
    # Verify admin tables
    print("\n[4/4] Verifying admin tables...")
    admin_tables = ['admin_users', 'ad_impressions', 'admin_activity_log', 'user_activity', 'ad_display_assignments']
    
    for table in admin_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  [OK] {table}: {count} records")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart your Flask application")
    print("2. Test admin panel at /admin/login")
    print("3. Verify real-time updates are working")
    print()

if __name__ == "__main__":
    migrate_admin_database()
