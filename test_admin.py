#!/usr/bin/env python3
"""
Test script for the Smart Link Intelligence Admin Panel
This script creates sample data to test the admin functionality
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import random

DATABASE = "smart_links.db"

def create_sample_data():
    """Create sample users, links, ads, and activity data for testing"""
    conn = sqlite3.connect(DATABASE)
    
    # Create sample users
    sample_users = [
        ("john_doe", "john@example.com", "free"),
        ("jane_smith", "jane@example.com", "elite"),
        ("premium_user", "premium@example.com", "elite_pro"),
        ("test_user", "test@example.com", "free"),
        ("power_user", "power@example.com", "elite_pro")
    ]
    
    for username, email, tier in sample_users:
        try:
            is_premium = 1 if tier in ['elite', 'elite_pro'] else 0
            expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat() if is_premium else None
            
            conn.execute("""
                INSERT INTO users (username, email, password_hash, is_premium, membership_tier, premium_expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [username, email, generate_password_hash("password123"), is_premium, tier, expires_at, datetime.utcnow().isoformat()])
            print(f"Created user: {username}")
        except sqlite3.IntegrityError:
            print(f"User {username} already exists")
    
    # Get user IDs
    users = conn.execute("SELECT id, username FROM users").fetchall()
    user_dict = {username: user_id for user_id, username in users}
    
    # Create sample links
    sample_links = [
        ("ABC123", "https://example.com", "standard", "john_doe"),
        ("XYZ789", "https://google.com", "progression", "jane_smith"),
        ("TEST01", "https://github.com", "standard", "premium_user"),
        ("DEMO99", "https://stackoverflow.com", "progression", "test_user"),
        ("POWER1", "https://python.org", "standard", "power_user")
    ]
    
    for code, url, behavior, username in sample_links:
        if username in user_dict:
            try:
                conn.execute("""
                    INSERT INTO links (code, primary_url, returning_url, cta_url, behavior_rule, state, created_at, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [code, url, url, url, behavior, "Active", datetime.utcnow().isoformat(), user_dict[username]])
                print(f"Created link: {code}")
            except sqlite3.IntegrityError:
                print(f"Link {code} already exists")
    
    # Get link IDs
    links = conn.execute("SELECT id, code, user_id FROM links").fetchall()
    
    # Create sample ads
    sample_ads = [
        ("Amazing Product!", "Check out our amazing product with great features", "Buy Now", "https://example.com/buy", "premium_user"),
        ("Special Offer", "Limited time offer - 50% off everything!", "Get Discount", "https://example.com/offer", "power_user"),
        ("Free Trial", "Try our service free for 30 days", "Start Trial", "https://example.com/trial", "jane_smith")
    ]
    
    for title, desc, cta, url, username in sample_ads:
        if username in user_dict:
            try:
                conn.execute("""
                    INSERT INTO personalized_ads (user_id, title, description, cta_text, cta_url, grid_position, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [user_dict[username], title, desc, cta, url, random.randint(1, 3), 1])
                print(f"Created ad: {title}")
            except Exception as e:
                print(f"Error creating ad {title}: {e}")
    
    # Create sample visits
    for link_id, code, link_user_id in links:
        for i in range(random.randint(5, 50)):
            try:
                visit_time = datetime.utcnow() - timedelta(days=random.randint(0, 30))
                conn.execute("""
                    INSERT INTO visits (link_id, session_id, ip_hash, user_agent, ts, behavior, is_suspicious, target_url, region, device, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    link_id, 
                    f"session_{random.randint(1000, 9999)}", 
                    hashlib.sha256(f"192.168.1.{random.randint(1, 255)}".encode()).hexdigest(),
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    visit_time.isoformat(),
                    random.choice(["Curious", "Interested", "Highly engaged"]),
                    random.choice([0, 0, 0, 1]),  # 25% suspicious
                    "https://example.com",
                    random.choice(["United States", "Canada", "United Kingdom", "Germany"]),
                    random.choice(["Desktop", "Mobile", "Tablet"]),
                    f"192.168.1.{random.randint(1, 255)}"
                ])
            except Exception as e:
                print(f"Error creating visit: {e}")
    
    # Create sample ad impressions
    ad_ids = [row[0] for row in conn.execute("SELECT id FROM personalized_ads").fetchall()]
    for ad_id in ad_ids:
        for i in range(random.randint(10, 100)):
            try:
                impression_time = datetime.utcnow() - timedelta(days=random.randint(0, 30))
                ad_type = random.choice(["large", "small", "small"])  # More small ads
                revenue = 0.05 if ad_type == "large" else 0.02
                
                # Get a random link and user for this impression
                link_data = random.choice(links)
                link_id, _, link_user_id = link_data
                
                conn.execute("""
                    INSERT INTO ad_impressions (link_id, user_id, ad_type, ad_position, revenue, ip_address, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    link_id,
                    link_user_id,
                    ad_type,
                    1 if ad_type == "large" else random.choice([2, 3]),
                    revenue,
                    f"192.168.1.{random.randint(1, 255)}",
                    impression_time.isoformat()
                ])
            except Exception as e:
                print(f"Error creating ad impression: {e}")
    
    # Create sample user activity
    activities = ["login", "create_link", "view_analytics", "create_ad", "upgrade"]
    for username, user_id in user_dict.items():
        for i in range(random.randint(5, 20)):
            try:
                activity_time = datetime.utcnow() - timedelta(days=random.randint(0, 30))
                activity_type = random.choice(activities)
                
                conn.execute("""
                    INSERT INTO user_activity (user_id, activity_type, details, ip_address, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    user_id,
                    activity_type,
                    f"User {username} performed {activity_type}",
                    f"192.168.1.{random.randint(1, 255)}",
                    activity_time.isoformat()
                ])
            except Exception as e:
                print(f"Error creating user activity: {e}")
    
    conn.commit()
    conn.close()
    print("\nSample data created successfully!")
    print("\nAdmin Panel Access:")
    print("URL: http://localhost:5000/admin/login")
    print("Password: admin123")
    print("\nSample user accounts (password: password123):")
    for username, email, tier in sample_users:
        print(f"  - {username} ({email}) - {tier}")

if __name__ == "__main__":
    create_sample_data()