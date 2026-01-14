# Smart Link Intelligence - Developer Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Database Schema](#database-schema)
5. [Core Modules](#core-modules)
6. [Routes & Blueprints](#routes--blueprints)
7. [Frontend Structure](#frontend-structure)
8. [Libraries & Dependencies](#libraries--dependencies)
9. [Key Features](#key-features)
10. [Setup & Deployment](#setup--deployment)

---

## Project Overview

**Smart Link Intelligence** is a Flask-based intelligent link shortening and management platform with advanced analytics, behavioral tracking, DDoS protection, and advertisement management.

### Key Capabilities
- **Intelligent Link Behavior**: Routes users to different URLs based on their interaction patterns
- **Advanced Analytics**: Comprehensive visitor tracking with geolocation, device detection, and behavioral analysis
- **Membership Tiers**: Free, Elite, and Elite Pro with progressive feature unlocking
- **DDoS Protection**: Automated threat detection and mitigation (Elite Pro)
- **Ad Management**: Custom ads for Elite Pro users, admin-managed system ads
- **Admin Panel**: Complete platform management dashboard

---

## Architecture

### Application Pattern
- **Framework**: Flask (Python web framework)
- **Architecture**: Modular Blueprint-based structure
- **Database**: SQLite with WAL mode for concurrent access
- **Session Management**: Flask sessions with custom cookie handling
- **Authentication**: Password hashing with Werkzeug security

### Request Flow
```
User Request → Flask App → Before Request Handler → Route Handler → Template Rendering → Response
                              ↓
                         Maintenance Check
                         Session Validation
                         User Context Loading
```

---

## File Structure

### Root Directory
```
link shorter/
├── app.py                    # Main application entry point
├── config.py                 # Configuration constants
├── database.py               # Database utilities and schema
├── admin_panel.py            # Admin panel blueprint
├── ddos_protection.py        # DDoS detection and protection
├── decorators.py             # Custom decorators (@login_required)
├── utils.py                  # Utility functions (geolocation, email, etc.)
├── chatbot.py                # AI chatbot functionality
├── requirements.txt          # Python dependencies
├── smart_links.db            # SQLite database
├── .env                      # Environment variables
└── intents.json              # Chatbot training data
```

### Routes Module (`routes/`)
```
routes/
├── __init__.py               # Routes package initializer
├── main.py                   # Landing, dashboard, documentation
├── auth.py                   # Login, signup, logout
├── links.py                  # Link creation, redirection, analytics
├── user.py                   # User settings, notifications, upgrade
└── ads.py                    # Ad creation and management
```

### Templates (`templates/`)
```
templates/
├── base.html                 # Base template with navigation
├── landing.html              # Public landing page
├── index.html                # User dashboard
├── login.html                # Login page
├── signup.html               # Registration page
├── analytics.html            # Link analytics details
├── analytics_overview.html   # Analytics overview
├── create_ad.html            # Ad creation interface
├── settings.html             # User settings
├── notifications.html        # User notifications
├── upgrade.html              # Membership upgrade page
├── behavior_rules.html       # Custom behavior rules
├── documentation.html        # Public documentation
├── maintenance.html          # Maintenance mode page
├── password_protected.html   # Password entry for protected links
├── ads.html                  # Ad display page
├── ddos_protection.html      # DDoS dashboard
├── ddos_link_stats.html      # Link-specific DDoS stats
├── ddos_blocked.html         # DDoS blocked page
└── partials/
    └── chat_widget.html      # AI chat widget
```

### Admin Templates (`templates/admin/`)
```
templates/admin/
├── base.html                 # Admin base template
├── login.html                # Admin login
├── dashboard.html            # Admin dashboard
├── users.html                # User management
├── user_detail.html          # User details
├── ads.html                  # Ad management
├── create_ad_for_user.html   # Create ad for user
├── create_admin_ad.html      # Create system ad
├── display_ad_to_users.html  # Ad assignment
├── analytics.html            # Platform analytics
├── activity.html             # User activity log
├── broadcast.html            # Broadcast notifications
├── feedbacks.html            # User feedback management
└── maintenance.html          # Maintenance mode settings
```

### Static Files (`static/`)
```
static/
├── css/
│   ├── base.css              # Global styles
│   ├── style.css             # Legacy styles
│   ├── landing.css           # Landing page styles
│   ├── analytics_theme.css   # Analytics styling
│   ├── create_ad.css         # Ad creation styles
│   ├── notifications.css     # Notification styles
│   ├── chat.css              # Chat widget styles
│   └── admin/                # Admin-specific styles
│       ├── admin_base.css    # Admin base styles
│       ├── admin_dashboard.css
│       ├── admin_users.css
│       └── ...
├── js/
│   ├── main.js               # Core JavaScript
│   ├── auth.js               # Authentication logic
│   ├── landing.js            # Landing page interactions
│   ├── analytics.js          # Analytics charts
│   ├── analytics_details.js  # Detailed analytics
│   ├── link_management.js    # Link CRUD operations
│   ├── ads.js                # Ad display logic
│   ├── settings.js           # Settings page logic
│   ├── behavior_rules.js     # Behavior rule management
│   ├── chat.js               # Chat widget logic
│   └── admin/                # Admin-specific scripts
│       ├── admin_dashboard.js
│       ├── admin_users.js
│       ├── admin_broadcast.js
│       └── ...
└── uploads/                  # User-uploaded ad images
```

---

## Database Schema

### Core Tables

#### `users`
Stores user account information and membership details.
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TEXT DEFAULT (datetime('now')),
    is_premium INTEGER DEFAULT 0,
    premium_expires_at TEXT,
    membership_tier TEXT DEFAULT 'free'  -- 'free', 'elite', 'elite_pro'
)
```

#### `links`
Stores shortened links with behavior rules and protection settings.
```sql
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,           -- Short code (e.g., 'abc123')
    primary_url TEXT NOT NULL,           -- Default destination
    returning_url TEXT,                  -- URL for returning visitors
    cta_url TEXT,                        -- Call-to-action URL
    behavior_rule TEXT DEFAULT 'standard',
    created_at TEXT NOT NULL,
    state TEXT DEFAULT 'Active',         -- 'Active', 'Dormant', 'Stale'
    user_id INTEGER NOT NULL,
    behavior_rule_id INTEGER,
    password_hash TEXT,                  -- For password-protected links
    protection_level INTEGER DEFAULT 0,  -- DDoS protection level
    auto_disabled INTEGER DEFAULT 0,
    ddos_detected_at TEXT,
    expires_at TEXT,                     -- Link expiration (for free users)
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(behavior_rule_id) REFERENCES behavior_rules(id)
)
```

#### `visits`
Tracks every click/visit to a link with detailed analytics.
```sql
CREATE TABLE visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL,
    session_id TEXT NOT NULL,            -- Unique session identifier
    ip_hash TEXT NOT NULL,               -- Hashed IP for privacy
    user_agent TEXT,
    ts TEXT NOT NULL,                    -- Timestamp
    behavior TEXT,                       -- 'new', 'returning', 'interested', 'engaged'
    is_suspicious INTEGER DEFAULT 0,
    target_url TEXT,                     -- Actual URL redirected to
    region TEXT,                         -- Geographic region
    device TEXT,                         -- 'mobile', 'tablet', 'desktop'
    country TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    timezone TEXT,
    browser TEXT,                        -- Browser name
    os TEXT,                             -- Operating system
    isp TEXT,                            -- Internet Service Provider
    hostname TEXT,
    org TEXT,                            -- Organization
    referrer TEXT,                       -- HTTP referrer
    ip_address TEXT,                     -- Actual IP (for DDoS detection)
    FOREIGN KEY(link_id) REFERENCES links(id)
)
```

#### `behavior_rules`
Custom behavior rules for link routing logic.
```sql
CREATE TABLE behavior_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    rule_name TEXT NOT NULL,
    returning_window_hours INTEGER DEFAULT 48,
    interested_threshold INTEGER DEFAULT 2,
    engaged_threshold INTEGER DEFAULT 3,
    is_default INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
```

#### `personalized_ads`
**Unified advertisement table** for both user-created ads (Elite Pro feature) and admin-created system-wide ads.

**Design Note**: This single table handles all ad types. Admin/system ads have `user_id = NULL`, while user-created ads have `user_id` set to the owner's ID. This unified approach simplifies queries, improves performance, and provides better flexibility than maintaining separate tables.

```sql
CREATE TABLE personalized_ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,                     -- NULL for admin/system ads, user ID for user-created ads
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    cta_text TEXT NOT NULL,
    cta_url TEXT NOT NULL,
    background_color TEXT DEFAULT '#667eea',
    text_color TEXT DEFAULT '#ffffff',
    icon TEXT DEFAULT '🚀',
    grid_position INTEGER DEFAULT 1,     -- 1 (large), 2 (small), 3 (small)
    ad_type TEXT DEFAULT 'custom',       -- 'custom' or 'image'
    image_filename TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
```

**Ad Types**:
- **Admin/System Ads**: `user_id IS NULL` - Created by administrators, can be assigned to specific users via `ad_display_assignments`
- **User Ads**: `user_id = <user_id>` - Created by Elite Pro users, displayed on their links

**Usage Examples**:
```python
# Query admin ads
admin_ads = query_db("SELECT * FROM personalized_ads WHERE user_id IS NULL")

# Query user's ads
user_ads = query_db("SELECT * FROM personalized_ads WHERE user_id = ?", [user_id])

# Query all ads with owner info
all_ads = query_db("""
    SELECT pa.*, COALESCE(u.username, 'System') as owner_name
    FROM personalized_ads pa
    LEFT JOIN users u ON pa.user_id = u.id
""")
```

#### `ad_impressions`
Tracks ad views for revenue calculation and analytics.
```sql
CREATE TABLE ad_impressions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,            -- User who owns the link where ad was shown
    ad_type TEXT NOT NULL,               -- 'large' or 'small'
    ad_position INTEGER NOT NULL,        -- 1, 2, or 3
    revenue REAL NOT NULL,               -- Revenue generated from this impression
    ip_address TEXT,
    ad_id INTEGER,                       -- References personalized_ads(id)
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(link_id) REFERENCES links(id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(ad_id) REFERENCES personalized_ads(id)
)
```

**Revenue Rates**:
- Large ad (position 1): $0.05 per impression
- Small ads (positions 2, 3): $0.02 per impression

#### `ad_display_assignments`
Manages targeted ad distribution - assigns specific ads to specific users.

**Purpose**: Allows admins to control which users see which ads. When an admin creates a system-wide ad (with `user_id = NULL` in `personalized_ads`), they can assign it to specific users through this table.

```sql
CREATE TABLE ad_display_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id INTEGER NOT NULL,              -- References personalized_ads(id)
    target_user_id INTEGER NOT NULL,     -- User who should see this ad
    assigned_by_admin INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(ad_id) REFERENCES personalized_ads(id) ON DELETE CASCADE,
    FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(ad_id, target_user_id)        -- Prevent duplicate assignments
)
```

**Usage**:
- Admin creates an ad with `user_id = NULL` in `personalized_ads`
- Admin assigns the ad to specific users via this table
- When those users' links are visited, the assigned ad is displayed
- Elite Pro users don't see assigned ads (they have ad-free experience)

#### `ddos_events`
Logs DDoS attack events and protection actions.
```sql
CREATE TABLE ddos_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,            -- 'rate_limit', 'suspicious_pattern', etc.
    severity INTEGER NOT NULL,           -- 1-5 severity scale
    ip_address TEXT,
    detected_at TEXT NOT NULL,
    protection_level INTEGER DEFAULT 0,
    FOREIGN KEY(link_id) REFERENCES links(id)
)
```

#### `notifications`
System notifications for users - supports both individual and broadcast notifications.

**Design Note**: Notifications can be targeted to individual users (`target_user_id`), groups (`target_group`), or all users. Since broadcast notifications are shared across multiple users, individual dismissal is tracked in the `notification_dismissals` table rather than using an `is_read` flag.

```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',            -- 'info', 'warning', 'success', 'danger'
    target_user_id INTEGER,              -- NULL for broadcast/group notifications
    target_group TEXT DEFAULT 'all',     -- 'all', 'free', 'elite', 'elite_pro'
    created_at TEXT DEFAULT (datetime('now'))
)
```

**Targeting Options**:
- **Individual**: `target_user_id = <user_id>` - Sent to specific user
- **Group**: `target_group = 'free'` (or 'elite', 'elite_pro') - Sent to all users in that tier
- **Broadcast**: `target_group = 'all'` - Sent to all users

#### `notification_dismissals`
Tracks which users have dismissed which notifications (many-to-many relationship).

**Purpose**: Since broadcast notifications are shared across users, this table tracks individual user dismissals. When a user dismisses a notification, a record is created here, and that notification won't appear for them anymore.

```sql
CREATE TABLE notification_dismissals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_id INTEGER NOT NULL,
    dismissed_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(notification_id) REFERENCES notifications(id)
)
```

**Example Query** (fetch undismissed notifications for a user):
```sql
SELECT n.* FROM notifications n
LEFT JOIN notification_dismissals d ON n.id = d.notification_id AND d.user_id = ?
WHERE (n.target_user_id = ? OR n.target_group = 'all' OR n.target_group = ?)
  AND d.id IS NULL  -- Only show if not dismissed
ORDER BY n.created_at DESC
```

#### `feedbacks`
User feedback submissions.
```sql
CREATE TABLE feedbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    status TEXT DEFAULT 'new',           -- 'new', 'in_progress', 'resolved'
    admin_response TEXT,
    responded_at TEXT,
    responded_by TEXT
)
```

#### `user_activities`
Tracks user actions for admin monitoring.
```sql
CREATE TABLE user_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
```

#### `system_settings`
Global system configuration.
```sql
CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
)
```

---

## Core Modules

### 1. `app.py` - Application Entry Point

**Purpose**: Initializes Flask app, registers blueprints, sets up middleware.

**Key Functions**:
- `create_app()`: Factory function that creates and configures Flask app
- `_before_request()`: Runs before each request to:
  - Load user session
  - Check maintenance mode
  - Populate `g.user` context

**Blueprints Registered**:
1. `admin_bp` - Admin panel (`/admin/*`)
2. `ddos_bp` - DDoS protection (`/ddos-protection/*`)
3. `main_bp` - Main routes (`/`, `/dashboard`, etc.)
4. `auth_bp` - Authentication (`/login`, `/signup`, `/logout`)
5. `links_bp` - Link management (`/create`, `/<code>`, etc.)
6. `user_bp` - User management (`/settings`, `/notifications`, etc.)
7. `ads_bp` - Advertisement routes (`/create-ad`, etc.)

**Configuration**:
- Loads config from `config.py`
- Sets up upload folder for ad images
- Initializes database tables
- Configures session cookies

---

### 2. `config.py` - Configuration Constants

**Purpose**: Centralized configuration for the entire application.

**Key Constants**:

```python
# Database
DATABASE = "smart_links.db"

# Session
SESSION_COOKIE_NAME = "smartlink_session"
USER_SESSION_KEY = "uid"

# Link Behavior
RETURNING_WINDOW_HOURS = 48          # Time window to identify returning users
MULTI_CLICK_THRESHOLD = 3            # Clicks to be considered "engaged"
SUSPICIOUS_INTERVAL_SECONDS = 1.0    # Min time between clicks
ATTENTION_DECAY_DAYS = 14            # Days before link becomes "Dormant"
STATE_DECAY_DAYS = 21                # Days before link becomes "Stale"

# File Uploads
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = (800, 600)

# Membership Tiers
MEMBERSHIP_TIERS = {
    "free": {
        "max_links": 10,
        "validity_days": 7,
        "custom_ads": False,
        "ddos_protection": False,
        "ad_free": False
    },
    "elite": {
        "max_links": 35,
        "validity_days": None,
        "custom_ads": False,
        "ddos_protection": False,
        "ad_free": False
    },
    "elite_pro": {
        "max_links": float('inf'),
        "validity_days": None,
        "custom_ads": True,
        "ddos_protection": True,
        "ad_free": True
    }
}
```

---

### 3. `database.py` - Database Utilities

**Purpose**: Database connection management and schema initialization.

**Key Functions**:

- `get_db()`: Returns database connection from Flask's `g` object
- `query_db(query, args, one)`: Execute SELECT queries
- `execute_db(query, args)`: Execute INSERT/UPDATE/DELETE queries
- `close_db(error)`: Close database connection (teardown handler)
- `ensure_db()`: Create all tables if they don't exist
- `ensure_column(table, column, definition)`: Add column if missing (migrations)

**Usage Example**:
```python
# Query single row
user = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)

# Query multiple rows
links = query_db("SELECT * FROM links WHERE user_id = ?", [user_id])

# Execute insert/update
execute_db("INSERT INTO visits (...) VALUES (...)", [values])
```

---

### 4. `utils.py` - Utility Functions

**Purpose**: Reusable helper functions for various tasks.

**Categories**:

#### Date/Time Utilities
- `utcnow()`: Get current UTC datetime

#### Security
- `hash_value(value)`: SHA256 hash for IP addresses
- `generate_code(length)`: Generate random alphanumeric codes

#### Session Management
- `ensure_session()`: Create session ID if not exists
- `get_link_password_hash(link)`: Safely extract password hash

#### Email
- `send_email(to_email, subject, html_content)`: Send emails via SMTP

#### Behavioral Analysis
- `classify_behavior(link_id, session_id, visits, now, behavior_rule)`: 
  - Classifies visitor as: new, returning, interested, engaged
  - Uses custom behavior rules or defaults
- `detect_suspicious(visits, now)`: Detect rapid clicking patterns
- `decide_target(link, behavior, session_count)`: Choose which URL to redirect to
- `evaluate_state(link_id, now)`: Update link state (Active/Dormant/Stale)
- `trust_score(link_id)`: Calculate link trustworthiness (0-100)
- `attention_decay(visits)`: Calculate engagement decay over time

#### Device Detection
- `detect_device(user_agent)`: Parse device type (mobile/tablet/desktop)
- `parse_browser(user_agent)`: Extract browser name and version
- `parse_os(user_agent)`: Extract operating system

#### Geolocation
- `get_client_ip()`: Get real client IP (handles proxies)
- `get_api_location(ip)`: Fetch location data from ip-api.com (cached)
- `detect_region(ip)`: Get region/continent
- `get_detailed_location(ip)`: Get country, city, coordinates, timezone
- `country_to_continent(country)`: Map country to continent

#### ISP Detection
- `get_isp_info(ip)`: Get ISP name, hostname, organization
- `normalize_isp(isp_name)`: Normalize ISP names for consistency

---

### 5. `admin_panel.py` - Admin Dashboard

**Purpose**: Complete administrative control panel.

**Key Features**:
- User management (view, edit, delete, grant premium)
- Ad management (create, assign, track revenue)
- Platform analytics
- Activity monitoring
- Feedback management
- Maintenance mode control
- Broadcast notifications

**Key Functions**:

- `admin_required(f)`: Decorator for admin-only routes
- `dashboard()`: Admin dashboard with live stats
- `users()`: User management page
- `user_detail(user_id)`: Detailed user view
- `toggle_user_premium(user_id)`: Grant/revoke premium access
- `ads()`: Ad management interface
- `create_admin_ad()`: Create system-wide ads (stored in `personalized_ads` with `user_id = NULL`)
- `display_ad_to_users(ad_id)`: Assign ads to specific users
- `analytics()`: Platform-wide analytics
- `activity()`: User activity log
- `broadcast()`: Send notifications to users
- `feedbacks()`: Manage user feedback
- `maintenance()`: Toggle maintenance mode

**Admin Authentication**:
- Password: `admin123` (change in production!)
- Session key: `admin_uid`
- Separate from user authentication

---

### 6. `ddos_protection.py` - DDoS Protection System

**Purpose**: Detect and mitigate DDoS attacks on links (Elite Pro feature).

**Key Components**:

#### `DDoSProtection` Class
- `check_rate_limit(ip, link_id)`: Check if IP exceeds rate limits
- `detect_ddos_attack(link_id)`: Analyze traffic patterns
- `apply_protection(link_id, level)`: Apply protection measures
- `is_link_protected(link_id)`: Check protection status
- `get_protection_stats(link_id)`: Get attack statistics

**Protection Levels**:
1. **Level 0**: No protection
2. **Level 1**: Rate limiting (60 req/min per IP)
3. **Level 2**: Stricter limits + CAPTCHA
4. **Level 3**: Temporary link disable
5. **Level 4**: Full lockdown

**Routes**:
- `/ddos-protection/dashboard`: DDoS dashboard
- `/ddos-protection/recover/<link_id>`: Manually recover link
- `/ddos-protection/stats/<link_id>`: Link-specific stats

---

### 7. `decorators.py` - Custom Decorators

**Purpose**: Reusable route decorators.

**Decorators**:

```python
@login_required
def protected_route():
    # Only accessible to logged-in users
    pass
```

Implementation checks `g.user` and redirects to login if not authenticated.

---

### 8. `chatbot.py` - AI Chatbot

**Purpose**: Provide automated support via chat widget.

**Key Components**:
- `get_chat_response(message)`: Process user message and return response
- Uses `intents.json` for pattern matching
- Provides help with:
  - Link creation
  - Analytics
  - Membership features
  - Troubleshooting

---

## Routes & Blueprints

### Main Routes (`routes/main.py`)

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing page (redirects to dashboard if logged in) |
| `/dashboard` | GET | User dashboard with links and stats |
| `/maintenance` | GET | Maintenance mode page |
| `/documentation` | GET | Public documentation |
| `/contact` | POST | Submit feedback form |
| `/chat` | POST | AI chatbot endpoint |

---

### Auth Routes (`routes/auth.py`)

| Route | Method | Description |
|-------|--------|-------------|
| `/signup` | GET, POST | User registration |
| `/check-availability` | POST | AJAX username/email validation |
| `/login` | GET, POST | User login |
| `/logout` | GET | User logout |

**Signup Validation**:
- Username: 3-20 chars, alphanumeric + underscore
- Email: Valid format
- Password: Min 6 chars
- Checks for existing username/email

**Login**:
- Accepts username or email
- Password verification with Werkzeug
- Creates session with `USER_SESSION_KEY`

---

### Link Routes (`routes/links.py`)

| Route | Method | Description |
|-------|--------|-------------|
| `/create` | POST | Create new short link |
| `/<code>` | GET | Redirect to target URL |
| `/ads/<code>` | GET | Show ads before redirect |
| `/password/<code>` | GET, POST | Password-protected link entry |
| `/delete/<link_id>` | POST | Delete link |
| `/analytics/<code>` | GET | Detailed link analytics |
| `/analytics-overview` | GET | All links analytics overview |
| `/export-csv/<code>` | GET | Export analytics as CSV |
| `/export-excel/<code>` | GET | Export analytics as Excel |

**Link Creation Flow**:
1. Validate user tier and link limits
2. Generate unique 6-character code
3. Set expiration for free users (7 days)
4. Store in database
5. Return short URL

**Redirection Logic**:
1. Check if link exists and is active
2. Check password protection
3. Check DDoS protection
4. Classify visitor behavior (new/returning/interested/engaged)
5. Decide target URL based on behavior
6. Track visit with full analytics
7. Show ads (if not Elite Pro)
8. Redirect to target

**Analytics Tracking**:
- IP address (hashed for privacy)
- Geolocation (country, city, coordinates)
- Device type and OS
- Browser
- ISP
- Referrer
- Timestamp
- Behavior classification

---

### User Routes (`routes/user.py`)

| Route | Method | Description |
|-------|--------|-------------|
| `/settings` | GET | User settings page |
| `/settings/update` | POST | Update account settings |
| `/settings/preferences` | POST | Update preferences |
| `/settings/delete-account` | POST | Delete user account |
| `/notifications` | GET | View notifications |
| `/notifications/delete/<id>` | POST | Dismiss notification |
| `/upgrade` | GET | Membership upgrade page |
| `/upgrade/process` | POST | Process upgrade (demo) |
| `/behavior-rules` | GET | Manage behavior rules |
| `/behavior-rules/create` | POST | Create custom rule |
| `/behavior-rules/delete/<id>` | POST | Delete rule |
| `/behavior-rules/set-default/<id>` | POST | Set default rule |

**Behavior Rules**:
Allow users to customize link routing logic:
- Returning window (hours)
- Interested threshold (clicks)
- Engaged threshold (clicks)

---

### Ad Routes (`routes/ads.py`)

| Route | Method | Description |
|-------|--------|-------------|
| `/create-ad` | GET | Ad creation page (Elite Pro only) |
| `/create-ad/submit` | POST | Submit new ad |
| `/toggle-ad/<ad_id>` | POST | Activate/deactivate ad |
| `/delete-ad/<ad_id>` | POST | Delete ad |
| `/uploads/<filename>` | GET | Serve uploaded ad images |

**Ad Types**:
1. **Custom**: Gradient background, emoji icon, text
2. **Image**: User-uploaded image with CTA overlay

**Grid Positions**:
- Position 1: Large ad (full width)
- Position 2: Small ad (left)
- Position 3: Small ad (right)

---

### Admin Routes (`admin_panel.py`)

| Route | Method | Description |
|-------|--------|-------------|
| `/admin/login` | GET, POST | Admin login |
| `/admin/logout` | GET | Admin logout |
| `/admin/dashboard` | GET | Admin dashboard |
| `/admin/live-stats` | GET | Live stats API |
| `/admin/recent-activities` | GET | Recent activities API |
| `/admin/live-revenue` | GET | Live revenue API |
| `/admin/users` | GET | User management |
| `/admin/users/<id>` | GET | User details |
| `/admin/users/<id>/delete` | POST | Delete user |
| `/admin/users/<id>/toggle-premium` | POST | Toggle premium |
| `/admin/ads` | GET | Ad management |
| `/admin/ads/create` | POST | Create admin ad |
| `/admin/ads/<id>/toggle` | POST | Toggle ad status |
| `/admin/ads/<id>/delete` | POST | Delete ad |
| `/admin/ads/<id>/assign` | GET, POST | Assign ad to users |
| `/admin/broadcast` | GET, POST | Broadcast notifications |
| `/admin/analytics` | GET | Platform analytics |
| `/admin/activity` | GET | User activity log |
| `/admin/feedbacks` | GET | View feedbacks |
| `/admin/feedbacks/<id>/respond` | POST | Respond to feedback |
| `/admin/feedbacks/<id>/status` | POST | Update status |
| `/admin/feedbacks/<id>/delete` | POST | Delete feedback |
| `/admin/maintenance` | GET, POST | Maintenance mode |
| `/admin/revenue-api` | GET | Revenue data API |

---

## Frontend Structure

### Template Inheritance

**Base Template** (`templates/base.html`):
- Navigation bar
- User menu
- Flash messages
- Footer
- Includes CSS/JS

**Admin Base** (`templates/admin/base.html`):
- Admin sidebar
- Admin navigation
- Dark theme
- Glassmorphism design

### JavaScript Architecture

**Module Pattern**:
Each page has dedicated JS file with event delegation:

```javascript
// Example: static/js/link_management.js
document.addEventListener('DOMContentLoaded', function() {
    // Event delegation for dynamic elements
    document.addEventListener('click', function(e) {
        if (e.target.matches('.delete-link-btn')) {
            handleDeleteLink(e);
        }
    });
});
```

**Key Scripts**:
- `main.js`: Core functionality, link creation
- `analytics.js`: Chart.js integration for analytics
- `auth.js`: Real-time validation on signup
- `chat.js`: Chat widget interactions
- `admin_dashboard.js`: Live stats polling

### CSS Architecture

**Utility-First Approach**:
- `admin_base.css`: Utility classes for admin panel
- Component-specific styles in separate files
- Responsive design with media queries
- Dark mode support

**Design System**:
- Glassmorphism effects
- Gradient backgrounds
- Smooth animations
- Modern typography (Inter, Roboto)

---

## Libraries & Dependencies

### Backend (`requirements.txt`)

```
Flask==3.0.3              # Web framework
itsdangerous==2.2.0       # Session security
Jinja2==3.1.4             # Template engine
Werkzeug==3.0.3           # WSGI utilities, password hashing
python-dotenv==1.0.1      # Environment variables
requests==2.31.0          # HTTP requests (geolocation API)
```

### Frontend (CDN)

**CSS Frameworks**:
- None (custom CSS for full control)

**JavaScript Libraries**:
- **Chart.js**: Analytics charts and graphs
- **Leaflet.js**: Interactive maps for geolocation
- **Font Awesome**: Icons

**Fonts**:
- Google Fonts (Inter, Roboto, Outfit)

---

## Key Features

### 1. Intelligent Link Behavior

**How It Works**:
1. User creates link with multiple URLs:
   - Primary URL (default)
   - Returning URL (for repeat visitors)
   - CTA URL (for highly engaged users)

2. On each visit:
   - System identifies visitor by session ID
   - Counts previous visits within time window
   - Classifies behavior:
     - **New**: First visit
     - **Returning**: 2+ visits within 48 hours
     - **Interested**: 2+ clicks (custom threshold)
     - **Engaged**: 3+ clicks (custom threshold)

3. Routes to appropriate URL based on behavior

**Custom Behavior Rules**:
Users can create rules to customize:
- Returning window (hours)
- Interested threshold (clicks)
- Engaged threshold (clicks)

### 2. Advanced Analytics

**Metrics Tracked**:
- Total clicks
- Unique visitors
- Geographic distribution (map + charts)
- Device breakdown (mobile/tablet/desktop)
- Browser statistics
- Operating system distribution
- ISP analysis
- Hourly click patterns
- Referrer sources
- Behavior classification distribution

**Visualizations**:
- Interactive world map (Leaflet.js)
- Pie charts (device, browser, OS)
- Bar charts (hourly patterns, countries)
- Time series (clicks over time)

**Export Options**:
- CSV: Summary statistics
- Excel: Detailed visitor log

### 3. Membership Tiers

| Feature | Free | Elite | Elite Pro |
|---------|------|-------|-----------|
| Max Links | 10 | 35 | Unlimited |
| Link Validity | 7 days | Permanent | Permanent |
| Custom Ads | ❌ | ❌ | ✅ |
| DDoS Protection | ❌ | ❌ | ✅ |
| Ad-Free Experience | ❌ | ❌ | ✅ |
| Analytics | ✅ | ✅ | ✅ |
| Behavior Rules | ✅ | ✅ | ✅ |
| Password Protection | ✅ | ✅ | ✅ |

### 4. DDoS Protection (Elite Pro)

**Detection Methods**:
- Rate limiting (requests per IP)
- Suspicious click patterns
- Rapid session creation
- Geographic anomalies

**Protection Measures**:
- Automatic rate limiting
- IP blocking
- Link auto-disable
- Real-time alerts

**Dashboard**:
- Protected links overview
- Attack event log
- Recovery options

### 5. Advertisement System

**User Ads (Elite Pro)**:
- Create custom ads with gradients or images
- Choose grid position (1 large, 2 small)
- Track impressions
- Enable/disable anytime

**Admin Ads**:
- System-wide ads
- Assign to specific users or all users
- Revenue tracking ($0.05/large, $0.02/small impression)
- Pause/resume functionality

**Ad Display Logic**:
1. Check if user is Elite Pro (ad-free)
2. Check for user's personal ads
3. Check for admin ads assigned to user
4. Show default "Want your ads here?" placeholders

### 6. Admin Panel

**Capabilities**:
- **User Management**: View, edit, delete, grant premium
- **Ad Management**: Create, assign, track revenue
- **Analytics**: Platform-wide statistics
- **Activity Monitoring**: Real-time user actions
- **Feedback Management**: Respond to user inquiries
- **Maintenance Mode**: Site-wide maintenance with custom message
- **Broadcast**: Send notifications to all users

**Live Features**:
- Auto-refreshing stats
- Real-time activity feed
- Live revenue tracking

### 7. AI Chatbot

**Functionality**:
- Intent-based pattern matching
- Helps with:
  - Link creation
  - Analytics interpretation
  - Feature explanations
  - Troubleshooting

**Integration**:
- Chat widget on all pages
- Tracks usage in activity log

---

## Setup & Deployment

### Local Development

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure Environment**:
Create `.env` file:
```
FLASK_SECRET=your-secret-key-here
```

3. **Initialize Database**:
```bash
python app.py
# Database tables created automatically on first run
```

4. **Run Development Server**:
```bash
python app.py
# Server runs on http://localhost:5000
```

5. **Access Admin Panel**:
- URL: `http://localhost:5000/admin/login`
- Password: `admin123`

### Production Deployment

1. **Change Admin Password**:
Edit `admin_panel.py`:
```python
ADMIN_PASSWORD_HASH = generate_password_hash("your-secure-password")
```

2. **Set Secret Key**:
Use strong random secret in `.env`

3. **Use Production WSGI Server**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

4. **Configure Reverse Proxy** (Nginx):
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/app/static;
    }
}
```

5. **Enable HTTPS** (Let's Encrypt):
```bash
certbot --nginx -d yourdomain.com
```

6. **Database Backups**:
```bash
# Automated daily backups
0 2 * * * cp /path/to/smart_links.db /backups/smart_links_$(date +\%Y\%m\%d).db
```

### Environment Variables

```bash
FLASK_SECRET=<random-secret-key>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## File Connectivity & Data Flow

### Link Creation Flow
```
User (Dashboard) 
  → POST /create (routes/links.py)
  → Validate tier limits (config.py)
  → Generate code (utils.py)
  → Insert into database (database.py)
  → Track activity (admin_panel.py)
  → Redirect to dashboard
```

### Link Redirection Flow
```
Visitor clicks /<code>
  → GET /<code> (routes/links.py)
  → Query link (database.py)
  → Check password protection
  → Check DDoS protection (ddos_protection.py)
  → Get visitor info (utils.py: geolocation, device, ISP)
  → Classify behavior (utils.py)
  → Decide target URL (utils.py)
  → Track visit (database.py)
  → Show ads (if not Elite Pro)
  → Redirect to target
```

### Analytics Display Flow
```
User views /analytics/<code>
  → GET /analytics/<code> (routes/links.py)
  → Query visits (database.py)
  → Aggregate data (Python)
  → Render template (templates/analytics.html)
  → Load Chart.js (static/js/analytics.js)
  → Display visualizations
```

### Admin Dashboard Flow
```
Admin accesses /admin/dashboard
  → Check admin session (admin_panel.py)
  → Query platform stats (database.py)
  → Render dashboard (templates/admin/dashboard.html)
  → Auto-refresh via AJAX (static/js/admin_dashboard.js)
  → Poll /admin/live-stats every 5 seconds
```

---

## API Endpoints (Internal)

### Live Stats API
**Endpoint**: `/admin/live-stats`  
**Method**: GET  
**Auth**: Admin required  
**Returns**:
```json
{
  "total_users": 150,
  "total_links": 1250,
  "total_clicks": 45000,
  "active_links": 980,
  "premium_users": 25
}
```

### Recent Activities API
**Endpoint**: `/admin/recent-activities`  
**Method**: GET  
**Auth**: Admin required  
**Returns**:
```json
{
  "activities": [
    {
      "username": "john_doe",
      "activity_type": "create_link",
      "description": "Created link: abc123",
      "created_at": "2026-01-13T06:00:00"
    }
  ]
}
```

### Revenue API
**Endpoint**: `/admin/revenue-api`  
**Method**: GET  
**Auth**: Admin required  
**Returns**:
```json
{
  "total_revenue": 1250.50,
  "daily_revenue": [
    {"date": "2026-01-13", "revenue": 45.20}
  ]
}
```

### Chat API
**Endpoint**: `/chat`  
**Method**: POST  
**Auth**: Optional  
**Request**:
```json
{
  "message": "How do I create a link?"
}
```
**Response**:
```json
{
  "response": "To create a link, go to your dashboard and click 'Create New Link'..."
}
```

---

## Security Considerations

### Password Security
- All passwords hashed with Werkzeug (PBKDF2)
- No plaintext passwords stored
- Session-based authentication

### SQL Injection Prevention
- Parameterized queries throughout
- No string concatenation in SQL

### XSS Prevention
- Jinja2 auto-escaping enabled
- User input sanitized

### CSRF Protection
- Flask session cookies with secure flags
- Consider adding Flask-WTF for forms

### IP Privacy
- IP addresses hashed before storage (SHA256)
- Raw IPs only stored temporarily for DDoS detection

### Rate Limiting
- DDoS protection system limits requests
- Admin can configure thresholds

---

## Troubleshooting

### Common Issues

**Database Locked Error**:
- Solution: Enable WAL mode (already implemented in `admin_panel.py`)

**Geolocation Not Working**:
- Check internet connection
- Verify ip-api.com is accessible
- Check rate limits (45 req/min for free tier)

**Admin Login Fails**:
- Verify password in `admin_panel.py`
- Check session configuration
- Clear browser cookies

**Links Expire Too Soon**:
- Free users: 7-day limit (by design)
- Upgrade to Elite for permanent links

**Ads Not Showing**:
- Check user tier (Elite Pro = ad-free)
- Verify ad is active
- Check ad assignment

---

## Future Enhancements

### Planned Features
1. **API Access**: RESTful API for link management
2. **Webhooks**: Real-time notifications for link events
3. **A/B Testing**: Test multiple URLs automatically
4. **QR Codes**: Generate QR codes for links
5. **Custom Domains**: Allow users to use their own domains
6. **Team Collaboration**: Multi-user workspaces
7. **Advanced Targeting**: Device/location-based routing
8. **Integration**: Zapier, Slack, Discord webhooks

### Scalability Improvements
1. **Redis Caching**: Cache geolocation and analytics
2. **PostgreSQL Migration**: For better concurrency
3. **CDN Integration**: Serve static assets faster
4. **Load Balancing**: Multiple app instances
5. **Async Tasks**: Celery for background jobs

---

## Contributing

### Code Style
- Follow PEP 8 for Python
- Use meaningful variable names
- Add docstrings to functions
- Comment complex logic

### Git Workflow
1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

### Testing
- Test all user flows
- Verify tier restrictions
- Check edge cases
- Test on multiple browsers

---

## Support

### Documentation
- This file: Complete developer reference
- `/documentation`: User-facing documentation
- Code comments: Inline explanations

### Contact
- Feedback form: `/contact`
- Admin panel: Feedback management

---

## License

**Proprietary Software**  
© 2026 Smart Link Intelligence  
All rights reserved.

---

## Changelog

### Version 1.0.0 (Current)
- Initial release
- Core link management
- Advanced analytics
- Membership tiers
- DDoS protection
- Admin panel
- Advertisement system
- AI chatbot

---

**Last Updated**: January 13, 2026  
**Maintained By**: Development Team  
**Version**: 1.0.0
