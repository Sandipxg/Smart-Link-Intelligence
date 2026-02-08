
import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('smart_links.db')
        cursor = conn.cursor()
        
        # 1. Create security_profiles table
        print("Creating security_profiles table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_name TEXT NOT NULL,
                requests_per_ip_per_minute INTEGER DEFAULT 60,
                requests_per_ip_per_hour INTEGER DEFAULT 1000,
                requests_per_link_per_minute INTEGER DEFAULT 500,
                burst_threshold INTEGER DEFAULT 100,
                suspicious_threshold INTEGER DEFAULT 10,
                ddos_threshold INTEGER DEFAULT 50,
                rapid_click_limit REAL DEFAULT 0.3,
                health_kill_switch INTEGER DEFAULT 5,
                detection_window_minutes INTEGER DEFAULT 5,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 2. Add security_profile_id to links table
        cursor.execute("PRAGMA table_info(links)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'security_profile_id' not in columns:
            print("Adding security_profile_id to links table...")
            cursor.execute("ALTER TABLE links ADD COLUMN security_profile_id INTEGER REFERENCES security_profiles(id)")
            
        # 3. Create default security profiles for existing users if they don't have one
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        for user in users:
            uid = user[0]
            cursor.execute("SELECT id FROM security_profiles WHERE user_id = ? AND is_default = 1", [uid])
            if not cursor.fetchone():
                print(f"Creating default security profile for user {uid}...")
                cursor.execute("""
                    INSERT INTO security_profiles 
                    (user_id, profile_name, is_default)
                    VALUES (?, ?, ?)
                """, [uid, 'Standard Security', 1])
        
        conn.commit()
        print("Separation migration successful!")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
