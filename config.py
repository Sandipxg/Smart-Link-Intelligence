"""
Smart Link Intelligence - Configuration
All configuration constants and settings
"""

import os
from datetime import timedelta

# Database Configuration
DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")

# Session Configuration
SESSION_COOKIE_NAME = "smartlink_session"
USER_SESSION_KEY = "uid"

# Link Behavior Configuration
RETURNING_WINDOW_HOURS = 48
MULTI_CLICK_THRESHOLD = 3
SUSPICIOUS_INTERVAL_SECONDS = 1.0
ATTENTION_DECAY_DAYS = 14
STATE_DECAY_DAYS = 21

# File Upload Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = (800, 600)  # Max width, height in pixels

# Membership Configuration
MEMBERSHIP_TIERS = {
    "free": {
        "max_links": 10, 
        "validity_days": 7, 
        "name": "Free User", 
        "custom_ads": False, 
        "ddos_protection": False, 
        "ad_free": False
    },
    "elite": {
        "max_links": 35, 
        "validity_days": None, 
        "name": "Elite User", 
        "custom_ads": False, 
        "ddos_protection": False, 
        "ad_free": False
    },
    "elite_pro": {
        "max_links": float('inf'), 
        "validity_days": None, 
        "name": "Elite Pro User", 
        "custom_ads": True, 
        "ddos_protection": True, 
        "ad_free": True
    },
}

# Flask Configuration
FLASK_CONFIG = {
    "SECRET_KEY": os.environ.get("FLASK_SECRET", "dev-secret-change-me"),
    "SESSION_COOKIE_NAME": SESSION_COOKIE_NAME,
    "UPLOAD_FOLDER": UPLOAD_FOLDER,
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB max file size
}