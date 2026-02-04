"""
Smart Link Intelligence - Database Utilities
Database connection, queries, and setup functions
"""

import os
import sqlite3
from flask import g
from config import DATABASE


def get_db():
    """Get database connection"""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, timeout=10) # 10 seconds timeout
        g.db.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


def query_db(query: str, args=None, one=False):
    """Execute database query"""
    cur = get_db().execute(query, args or [])
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query: str, args=None):
    """Execute database command"""
    db = get_db()
    db.execute(query, args or [])
    db.commit()


def close_db(error):
    """Close database connection"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_column(table_name, column_name, column_definition):
    """Ensure a column exists in a table"""
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
        conn.commit()
        print(f"Added column {column_name} to {table_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            print(f"Error adding column {column_name} to {table_name}: {e}")
    finally:
        conn.close()


def ensure_db():
    """Ensure database and tables exist"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TEXT DEFAULT (datetime('now')),
            is_premium INTEGER DEFAULT 0,
            premium_expires_at TEXT,
            membership_tier TEXT DEFAULT 'free'
        )
    """)

    # Links table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            primary_url TEXT NOT NULL,
            returning_url TEXT,
            cta_url TEXT,
            behavior_rule TEXT DEFAULT 'standard',
            created_at TEXT NOT NULL,
            state TEXT DEFAULT 'Active',
            user_id INTEGER NOT NULL,
            behavior_rule_id INTEGER,
            password_hash TEXT,
            protection_level INTEGER DEFAULT 0,
            auto_disabled INTEGER DEFAULT 0,
            ddos_detected_at TEXT,
            expires_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(behavior_rule_id) REFERENCES behavior_rules(id)
        )
    """)

    # Visits table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            ip_hash TEXT NOT NULL,
            user_agent TEXT,
            ts TEXT NOT NULL,
            behavior TEXT,
            is_suspicious INTEGER DEFAULT 0,
            target_url TEXT,
            region TEXT,
            device TEXT,
            country TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            timezone TEXT,
            browser TEXT,
            os TEXT,
            isp TEXT,
            hostname TEXT,
            org TEXT,
            referrer TEXT,
            ip_address TEXT,
            FOREIGN KEY(link_id) REFERENCES links(id)
        )
    """)

    # Behavior rules table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS behavior_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            rule_name TEXT NOT NULL,
            returning_window_hours INTEGER DEFAULT 48,
            interested_threshold INTEGER DEFAULT 2,
            engaged_threshold INTEGER DEFAULT 3,
            requests_per_ip_per_minute INTEGER DEFAULT 60,
            requests_per_ip_per_hour INTEGER DEFAULT 1000,
            requests_per_link_per_minute INTEGER DEFAULT 500,
            burst_threshold INTEGER DEFAULT 100,
            suspicious_threshold INTEGER DEFAULT 10,
            ddos_threshold INTEGER DEFAULT 50,
            is_default INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # DDoS Events table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ddos_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            severity INTEGER NOT NULL,
            ip_address TEXT,
            detected_at TEXT NOT NULL,
            protection_level INTEGER DEFAULT 0,
            FOREIGN KEY(link_id) REFERENCES links(id)
        )
    """)

    # System settings table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Ensure additional columns exist
    ensure_column("links", "protection_level", "protection_level INTEGER DEFAULT 0")
    ensure_column("links", "auto_disabled", "auto_disabled INTEGER DEFAULT 0")
    ensure_column("links", "ddos_detected_at", "ddos_detected_at TEXT")
    ensure_column("links", "password_hash", "password_hash TEXT")
    ensure_column("users", "membership_tier", "membership_tier TEXT DEFAULT 'free'")
    ensure_column("users", "premium_expires_at", "premium_expires_at TEXT")
    ensure_column("users", "premium_expires_at", "premium_expires_at TEXT")
    ensure_column("links", "expires_at", "expires_at TEXT")

    # Ensure behavior_rules columns
    ensure_column("behavior_rules", "requests_per_ip_per_minute", "requests_per_ip_per_minute INTEGER DEFAULT 60")
    ensure_column("behavior_rules", "requests_per_ip_per_hour", "requests_per_ip_per_hour INTEGER DEFAULT 1000")
    ensure_column("behavior_rules", "requests_per_link_per_minute", "requests_per_link_per_minute INTEGER DEFAULT 500")
    ensure_column("behavior_rules", "burst_threshold", "burst_threshold INTEGER DEFAULT 100")
    ensure_column("behavior_rules", "suspicious_threshold", "suspicious_threshold INTEGER DEFAULT 10")
    ensure_column("behavior_rules", "ddos_threshold", "ddos_threshold INTEGER DEFAULT 50")
    
    # Notification dismissals table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_dismissals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notification_id INTEGER NOT NULL,
            dismissed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(notification_id) REFERENCES notifications(id)
        )
    """)
    
    # Feedbacks table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            admin_response TEXT,
            responded_at TEXT,
            responded_by TEXT
        )
    """)
    
    conn.commit()
    conn.close()