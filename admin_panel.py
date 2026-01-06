"""
Smart Link Intelligence - Comprehensive Admin Panel
Features:
- Complete user management (CRUD operations)
- Ad management with revenue tracking
- Advanced analytics with ad impression tracking
- Activity monitoring
- Export functionality
- Separate admin authentication
"""

import hashlib
import os
import sqlite3
import csv
import io
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, Response, g
from werkzeug.security import check_password_hash, generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Add custom Jinja2 filters
def get_activity_badge_color(activity_type):
    """Get Bootstrap badge color for activity type"""
    colors = {
        'login': 'primary',
        'create_link': 'success',
        'view_analytics': 'info',
        'create_ad': 'warning',
        'upgrade': 'danger',
        'delete_link': 'dark'
    }
    return colors.get(activity_type, 'secondary')

def get_activity_icon(activity_type):
    """Get FontAwesome icon for activity type"""
    icons = {
        'login': 'sign-in-alt',
        'create_link': 'plus',
        'view_analytics': 'chart-line',
        'create_ad': 'ad',
        'upgrade': 'crown',
        'delete_link': 'trash'
    }
    return icons.get(activity_type, 'circle')

# Register the filters
admin_bp.add_app_template_filter(get_activity_badge_color, 'get_activity_badge_color')
admin_bp.add_app_template_filter(get_activity_icon, 'get_activity_icon')

# Admin configuration
ADMIN_SESSION_KEY = "admin_uid"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")  # Change this in production
AD_REVENUE_RATES = {
    "large": 0.05,  # $0.05 per large ad impression
    "small": 0.02   # $0.02 per small ad impression
}

@admin_bp.before_request
def load_user_context():
    """Load regular user context if logged in (for admin reference)"""
    from flask import session as flask_session
    if 'uid' in flask_session:
        try:
            g.current_user = query_db("SELECT * FROM users WHERE id = ?", [flask_session['uid']], one=True)
        except Exception as e:
            g.current_user = None
            print(f"Error loading user context: {e}")
    else:
        g.current_user = None

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get(ADMIN_SESSION_KEY):
            flash("Admin authentication required", "danger")
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    """Enhanced database connection with pooling and WAL mode"""
    if "db" not in g:
        DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")
        g.db = sqlite3.connect(DATABASE, check_same_thread=False, timeout=10.0)
        g.db.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent access
        try:
            g.db.execute("PRAGMA journal_mode=WAL")
            g.db.execute("PRAGMA synchronous=NORMAL")
            g.db.execute("PRAGMA cache_size=-64000")  # 64MB cache
        except Exception as e:
            print(f"Warning: Could not set PRAGMA settings: {e}")
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

def ensure_admin_tables():
    """Ensure admin-specific tables exist"""
    DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    
    # Admin users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # Ad impressions tracking table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ad_impressions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            ad_type TEXT NOT NULL,  -- 'large' or 'small'
            ad_position INTEGER NOT NULL,  -- 1, 2, or 3
            revenue REAL NOT NULL,
            ip_address TEXT,
            ad_id INTEGER,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(link_id) REFERENCES links(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(ad_id) REFERENCES personalized_ads(id)
        )
    """)
    
    # Personalized Ads table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS personalized_ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,  -- Made nullable
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            cta_text TEXT NOT NULL,
            cta_url TEXT NOT NULL,
            background_color TEXT DEFAULT '#667eea',
            text_color TEXT DEFAULT '#ffffff',
            icon TEXT DEFAULT '🚀',
            is_active INTEGER DEFAULT 1,
            grid_position INTEGER DEFAULT 1,
            ad_type TEXT DEFAULT 'custom',
            image_filename TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    # Admin activity log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT NOT NULL,
            target_type TEXT,  -- 'user', 'ad', 'link', etc.
            target_id INTEGER,
            details TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            ip_address TEXT
        )
    """)
    
    # User activity tracking (enhanced)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,  -- 'login', 'create_link', 'view_analytics', etc.
            details TEXT,
            ip_address TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    # Ad display assignments table - for targeted ad distribution
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ad_display_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_id INTEGER NOT NULL,
            target_user_id INTEGER NOT NULL,
            assigned_by_admin INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(ad_id) REFERENCES personalized_ads(id) ON DELETE CASCADE,
            FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(ad_id, target_user_id)
        )
    """)

    # Notifications table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            target_user_id INTEGER, -- NULL for group-based or site-wide
            target_group TEXT DEFAULT 'all', -- 'all', 'free', 'elite', 'elite_pro'
            created_at TEXT DEFAULT (datetime('now')),
            is_read INTEGER DEFAULT 0
        )
    """)
    
    # Create default admin user if none exists
    admin_exists = conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
    if admin_exists == 0:
        conn.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
            ["admin", ADMIN_PASSWORD_HASH]
        )
    
    conn.commit()
    conn.close()

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page - requires password every time"""
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        
        if not password:
            flash("Password is required", "danger")
            return render_template('admin/login.html')
        
        # Check against hardcoded admin password (always require password)
        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            session[ADMIN_SESSION_KEY] = True
            session.permanent = False  # Session expires when browser closes
            
            # Log admin login
            log_admin_activity("admin_login", details="Admin logged in")
            
            flash("Welcome to Admin Panel", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid password", "danger")
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    """Admin logout"""
    session.pop(ADMIN_SESSION_KEY, None)
    flash("Logged out from admin panel", "info")
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with overview statistics"""
    # Get overview statistics
    stats = {
        'total_users': query_db("SELECT COUNT(*) as count FROM users", one=True)['count'],
        'total_links': query_db("SELECT COUNT(*) as count FROM links", one=True)['count'],
        'total_visits': query_db("SELECT COUNT(*) as count FROM visits", one=True)['count'],
        'total_ads': query_db("SELECT COUNT(*) as count FROM personalized_ads", one=True)['count'],
        'active_ads': query_db("SELECT COUNT(*) as count FROM personalized_ads WHERE is_active = 1", one=True)['count'],
        'premium_users': query_db("SELECT COUNT(*) as count FROM users WHERE is_premium = 1", one=True)['count'],
    }
    
    # Calculate total revenue from ad impressions
    revenue_data = query_db("SELECT SUM(revenue) as total FROM ad_impressions", one=True)
    stats['total_revenue'] = revenue_data['total'] if revenue_data['total'] else 0.0
    
    # Get recent user registrations (last 7 days)
    recent_users = query_db("""
        SELECT COUNT(*) as count FROM users 
        WHERE created_at >= datetime('now', '-7 days')
    """, one=True)['count']
    stats['recent_users'] = recent_users
    
    # Get top performing links by clicks
    top_links = query_db("""
        SELECT l.code, l.primary_url, u.username, u.id as user_id, COUNT(v.id) as clicks
        FROM links l
        JOIN users u ON l.user_id = u.id
        LEFT JOIN visits v ON l.id = v.link_id
        GROUP BY l.id
        ORDER BY clicks DESC
        LIMIT 5
    """)
    
    # Get recent admin activities
    recent_activities = query_db("""
        SELECT * FROM admin_activity_log 
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         top_links=[dict(row) for row in top_links],
                         recent_activities=[dict(row) for row in recent_activities])

@admin_bp.route('/api/stats/live')
@admin_required
def live_stats():
    """Return current statistics in JSON for AJAX polling"""
    try:
        stats = {
            'total_users': query_db("SELECT COUNT(*) as count FROM users", one=True)['count'],
            'total_links': query_db("SELECT COUNT(*) as count FROM links", one=True)['count'],
            'total_visits': query_db("SELECT COUNT(*) as count FROM visits", one=True)['count'],
            'total_ads': query_db("SELECT COUNT(*) as count FROM personalized_ads", one=True)['count'],
            'active_ads': query_db("SELECT COUNT(*) as count FROM personalized_ads WHERE is_active = 1", one=True)['count'],
            'premium_users': query_db("SELECT COUNT(*) as count FROM users WHERE is_premium = 1", one=True)['count'],
        }
        
        # Calculate total revenue
        revenue_data = query_db("SELECT SUM(revenue) as total FROM ad_impressions", one=True)
        stats['total_revenue'] = float(revenue_data['total']) if revenue_data['total'] else 0.0
        
        # Get recent user registrations (last 7 days)
        recent_users = query_db("""
            SELECT COUNT(*) as count FROM users 
            WHERE created_at >= datetime('now', '-7 days')
        """, one=True)['count']
        stats['recent_users'] = recent_users
        
        # Get recent activity count (last hour)
        recent_activity_count = query_db("""
            SELECT COUNT(*) as count FROM user_activity 
            WHERE timestamp >= datetime('now', '-1 hour')
        """, one=True)['count']
        stats['recent_activity_count'] = recent_activity_count
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/activities/recent')
@admin_required
def recent_activities_api():
    """Get recent user activities for live feed"""
    try:
        limit = int(request.args.get('limit', 10))
        
        activities = query_db("""
            SELECT ua.*, u.username
            FROM user_activity ua
            JOIN users u ON ua.user_id = u.id
            ORDER BY ua.timestamp DESC
            LIMIT ?
        """, [limit])
        
        return jsonify({
            'success': True,
            'activities': [dict(row) for row in activities],
            'count': len(activities)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/revenue/live')
@admin_required
def live_revenue():
    """Get live revenue statistics"""
    try:
        # Total revenue
        total_revenue = query_db("SELECT SUM(revenue) as total FROM ad_impressions", one=True)
        total = float(total_revenue['total']) if total_revenue['total'] else 0.0
        
        # Today's revenue
        today_revenue = query_db("""
            SELECT SUM(revenue) as total FROM ad_impressions 
            WHERE DATE(timestamp) = DATE('now')
        """, one=True)
        today = float(today_revenue['total']) if today_revenue['total'] else 0.0
        
        # This week's revenue
        week_revenue = query_db("""
            SELECT SUM(revenue) as total FROM ad_impressions 
            WHERE timestamp >= datetime('now', '-7 days')
        """, one=True)
        week = float(week_revenue['total']) if week_revenue['total'] else 0.0
        
        # Impression count today
        impressions_today = query_db("""
            SELECT COUNT(*) as count FROM ad_impressions 
            WHERE DATE(timestamp) = DATE('now')
        """, one=True)['count']
        
        return jsonify({
            'success': True,
            'revenue': {
                'total': round(total, 2),
                'today': round(today, 2),
                'week': round(week, 2),
                'impressions_today': impressions_today
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/users')
@admin_required
def users():
    """User management page"""
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 20
    
    # Build query based on search
    if search:
        users_query = """
            SELECT u.*,
                   (SELECT COUNT(*) FROM links l WHERE l.user_id = u.id) as link_count,
                   (SELECT COUNT(*) FROM visits v JOIN links l ON v.link_id = l.id WHERE l.user_id = u.id) as total_clicks,
                   (SELECT COALESCE(SUM(revenue), 0) FROM ad_impressions ai WHERE ai.user_id = u.id) as total_revenue
            FROM users u
            WHERE u.username LIKE ? OR u.email LIKE ?
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
        """
        search_param = f"%{search}%"
        users_list = query_db(users_query, [search_param, search_param, per_page, (page-1)*per_page])
        
        total_users = query_db("""
            SELECT COUNT(*) as count FROM users 
            WHERE username LIKE ? OR email LIKE ?
        """, [search_param, search_param], one=True)['count']
    else:
        users_query = """
            SELECT u.*,
                   (SELECT COUNT(*) FROM links l WHERE l.user_id = u.id) as link_count,
                   (SELECT COUNT(*) FROM visits v JOIN links l ON v.link_id = l.id WHERE l.user_id = u.id) as total_clicks,
                   (SELECT COALESCE(SUM(revenue), 0) FROM ad_impressions ai WHERE ai.user_id = u.id) as total_revenue
            FROM users u
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
        """
        users_list = query_db(users_query, [per_page, (page-1)*per_page])
        total_users = query_db("SELECT COUNT(*) as count FROM users", one=True)['count']
    
    total_pages = (total_users + per_page - 1) // per_page
    
    return render_template('admin/users.html', 
                         users=[dict(row) for row in users_list], 
                         search=search,
                         page=page,
                         total_pages=total_pages,
                         total_users=total_users)

@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """Detailed user view"""
    user = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)
    if not user:
        flash("User not found", "danger")
        return redirect(url_for('admin.users'))
    
    # Get user's links
    links = query_db("""
        SELECT l.*, COUNT(v.id) as clicks
        FROM links l
        LEFT JOIN visits v ON l.id = v.link_id
        WHERE l.user_id = ?
        GROUP BY l.id
        ORDER BY l.created_at DESC
    """, [user_id])
    
    # Get ads based on membership tier
    if user['membership_tier'] == 'elite_pro':
        # Elite Pro: Only show ads created by the user
        ads = query_db("""
            SELECT * FROM personalized_ads 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, [user_id])
    else:
        # Free/Elite: Show ads created for them + ads assigned to them
        ads = query_db("""
            SELECT DISTINCT pa.* 
            FROM personalized_ads pa 
            LEFT JOIN ad_display_assignments ada ON pa.id = ada.ad_id
            WHERE pa.user_id = ? OR ada.target_user_id = ?
            ORDER BY pa.created_at DESC
        """, [user_id, user_id])
    
    # Get user activity
    activities = query_db("""
        SELECT * FROM user_activity 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 20
    """, [user_id])
    
    # Calculate revenue generated by this user
    revenue_data = query_db("""
        SELECT SUM(revenue) as total FROM ad_impressions 
        WHERE user_id = ?
    """, [user_id], one=True)
    total_revenue = revenue_data['total'] if revenue_data['total'] else 0.0
    
    return render_template('admin/user_detail.html', 
                         user=dict(user), 
                         links=[dict(row) for row in links], 
                         ads=[dict(row) for row in ads],
                         activities=[dict(row) for row in activities],
                         total_revenue=total_revenue)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user and all associated data"""
    user = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    try:
        # Delete in correct order due to foreign key constraints
        execute_db("DELETE FROM ad_impressions WHERE user_id = ?", [user_id])
        execute_db("DELETE FROM user_activity WHERE user_id = ?", [user_id])
        execute_db("DELETE FROM visits WHERE link_id IN (SELECT id FROM links WHERE user_id = ?)", [user_id])
        execute_db("DELETE FROM ddos_events WHERE link_id IN (SELECT id FROM links WHERE user_id = ?)", [user_id])
        execute_db("DELETE FROM personalized_ads WHERE user_id = ?", [user_id])
        execute_db("DELETE FROM behavior_rules WHERE user_id = ?", [user_id])
        execute_db("DELETE FROM links WHERE user_id = ?", [user_id])
        execute_db("DELETE FROM users WHERE id = ?", [user_id])
        
        # Log admin activity
        log_admin_activity("delete_user", "user", user_id, f"Deleted user: {user['username']}")
        
        return jsonify({"success": True, "message": f"User '{user['username']}' deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error deleting user: {str(e)}"}), 500

@admin_bp.route('/users/<int:user_id>/toggle-premium', methods=['POST'])
@admin_required
def toggle_user_premium(user_id):
    """Toggle user premium status"""
    user = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    new_status = 0 if user['is_premium'] else 1
    expires_at = None
    new_tier = 'free'
    
    if new_status == 1:
        # Get tier from request, default to elite
        data = request.get_json() or {}
        requested_tier = data.get('tier', 'elite')
        
        # Validate tier
        if requested_tier in ['elite', 'elite_pro']:
            new_tier = requested_tier
        else:
            new_tier = 'elite'
            
        # Set premium expiry to 30 days from now
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    execute_db("""
        UPDATE users 
        SET is_premium = ?, premium_expires_at = ?, membership_tier = ?
        WHERE id = ?
    """, [new_status, expires_at, new_tier, user_id])
    
    status_text = f"activated ({new_tier})" if new_status else "deactivated"
    log_admin_activity("toggle_premium", "user", user_id, 
                      f"Premium {status_text} for user: {user['username']}")
    
    return jsonify({
        "success": True, 
        "message": f"Premium {status_text} for {user['username']}",
        "new_status": new_status,
        "new_tier": new_tier
    })

@admin_bp.route('/ads')
@admin_required
def ads():
    """Ad management page"""
    search = request.args.get('search', '').strip()
    
    if search:
        ads_query = """
            SELECT pa.*, COALESCE(u.username, 'System') as username
            FROM personalized_ads pa
            LEFT JOIN users u ON pa.user_id = u.id
            WHERE pa.title LIKE ? OR u.username LIKE ? OR (u.username IS NULL AND 'System' LIKE ?)
            ORDER BY pa.created_at DESC
        """
        search_param = f"%{search}%"
        ads_list = query_db(ads_query, [search_param, search_param, search_param])
    else:
        ads_list = query_db("""
            SELECT pa.*, COALESCE(u.username, 'System') as username
            FROM personalized_ads pa
            LEFT JOIN users u ON pa.user_id = u.id
            ORDER BY pa.created_at DESC
        """)
    
    # Get ad statistics
    ad_stats = {
        'total_ads': len(ads_list),
        'active_ads': len([ad for ad in ads_list if ad['is_active']]),
        'inactive_ads': len([ad for ad in ads_list if not ad['is_active']]),
    }
    
    # Calculate total impressions and revenue
    impression_data = query_db("""
        SELECT COUNT(*) as impressions, SUM(revenue) as revenue
        FROM ad_impressions
    """, one=True)
    
    ad_stats['total_impressions'] = impression_data['impressions'] if impression_data['impressions'] else 0
    ad_stats['total_revenue'] = impression_data['revenue'] if impression_data['revenue'] else 0.0
    
    return render_template('admin/ads.html', 
                         ads=[dict(row) for row in ads_list], 
                         search=search,
                         ad_stats=ad_stats)

@admin_bp.route('/ads/create-for-user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def create_ad_for_user(user_id):
    """Create ad for any user (including free users)"""
    user = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)
    if not user:
        flash("User not found", "danger")
        return redirect(url_for('admin.users'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        cta_text = request.form.get('cta_text', '').strip()
        cta_url = request.form.get('cta_url', '').strip()
        grid_position = int(request.form.get('grid_position', 1))
        background_color = request.form.get('background_color', '#667eea')
        text_color = request.form.get('text_color', '#ffffff')
        icon = request.form.get('icon', '🚀')
        
        if not all([title, description, cta_text, cta_url]):
            flash("All fields are required", "danger")
            return render_template('admin/create_ad_for_user.html', user=user)
        
        execute_db("""
            INSERT INTO personalized_ads 
            (user_id, title, description, cta_text, cta_url, background_color, text_color, icon, grid_position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [user_id, title, description, cta_text, cta_url, background_color, text_color, icon, grid_position])
        
        log_admin_activity("create_ad", "ad", None, 
                          f"Created ad '{title}' for user: {user['username']}")
        
        flash(f"Ad created successfully for {user['username']}", "success")
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    return render_template('admin/create_ad_for_user.html', user=user)

@admin_bp.route('/ads/create', methods=['GET', 'POST'])
@admin_required
def create_admin_ad():
    """Create ads as admin (can assign to any user)"""
    if request.method == 'POST':
        # Get form data
        user_id = request.form.get('user_id')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        cta_text = request.form.get('cta_text', '').strip()
        cta_url = request.form.get('cta_url', '').strip()
        ad_type = request.form.get('ad_type', 'custom')
        grid_position = int(request.form.get('grid_position', 1))
        
        # If user_id is not provided, try to find a default user
        if not user_id:
            # Try to find 'System' user, then 'admin', or just the first user
            default_user = query_db("SELECT id FROM users WHERE username = 'System' OR username = 'admin' OR username = 'Admin' ORDER BY (CASE WHEN username = 'System' THEN 0 WHEN username LIKE 'admin%' THEN 1 ELSE 2 END) ASC LIMIT 1", one=True)
            
            if default_user:
                user_id = default_user['id']
            else:
                # If truly no users exist, allow user_id to be NULL (Global Ad)
                user_id = None

        # Validation (user_id is now optional for admin)
        if not all([title, description, cta_text, cta_url]):
            flash("All fields except user assignment are required", "danger")
            return render_template('admin/create_admin_ad.html')
        
        # Validate URL
        if not cta_url.startswith(('http://', 'https://')):
            flash("Please enter a valid URL starting with http:// or https://", "danger")
            return render_template('admin/create_admin_ad.html')
        
        # Validate user exists if provided
        user_name = "System"
        if user_id:
            user = query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)
            if not user:
                flash("Selected user not found", "danger")
                return render_template('admin/create_admin_ad.html')
            user_name = user['username']
        
        image_filename = None
        background_color = "#667eea"
        text_color = "#ffffff"
        icon = "🚀"
        
        if ad_type == 'image':
            # Handle image upload
            if 'ad_image' in request.files and request.files['ad_image'].filename != '':
                file = request.files['ad_image']
                # Process and save image (simplified version)
                from werkzeug.utils import secure_filename
                import uuid
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                
                # Get upload folder from app config (we need to import this)
                upload_folder = os.path.join(os.path.dirname(__file__), "static", "uploads")
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, unique_filename))
                image_filename = unique_filename
        else:
            # Handle custom ad
            background_color = request.form.get('background_color', '#667eea')
            text_color = request.form.get('text_color', '#ffffff')
            icon = request.form.get('icon', '🚀')
        
        # Create the ad
        execute_db("""
            INSERT INTO personalized_ads 
            (user_id, title, description, cta_text, cta_url, background_color, text_color, icon, grid_position, ad_type, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [user_id, title, description, cta_text, cta_url, background_color, text_color, icon, grid_position, ad_type, image_filename])
        
        log_admin_activity("create_ad", "ad", None, 
                          f"Admin created ad '{title}' for owner: {user_name}")
        
        flash(f"Ad created successfully for {user_name}", "success")
        return redirect(url_for('admin.ads'))
    
    return render_template('admin/create_admin_ad.html')

@admin_bp.route('/ads/<int:ad_id>/toggle', methods=['POST'])
@admin_required
def toggle_ad(ad_id):
    """Toggle ad active status"""
    ad = query_db("SELECT * FROM personalized_ads WHERE id = ?", [ad_id], one=True)
    if not ad:
        return jsonify({"success": False, "message": "Ad not found"}), 404
    
    new_status = 0 if ad['is_active'] else 1
    execute_db("UPDATE personalized_ads SET is_active = ? WHERE id = ?", [new_status, ad_id])
    
    status_text = "activated" if new_status else "deactivated"
    log_admin_activity("toggle_ad", "ad", ad_id, f"Ad {status_text}: {ad['title']}")
    
    return jsonify({
        "success": True,
        "message": f"Ad {status_text} successfully",
        "new_status": new_status
    })

@admin_bp.route('/ads/<int:ad_id>/delete', methods=['POST'])
@admin_required
def delete_ad(ad_id):
    """Delete an ad"""
    ad = query_db("SELECT * FROM personalized_ads WHERE id = ?", [ad_id], one=True)
    if not ad:
        return jsonify({"success": False, "message": "Ad not found"}), 404
    
    # Delete ad impressions first
    execute_db("DELETE FROM ad_impressions WHERE ad_id = ?", [ad_id])
    execute_db("DELETE FROM personalized_ads WHERE id = ?", [ad_id])
    
    log_admin_activity("delete_ad", "ad", ad_id, f"Deleted ad: {ad['title']}")
    
    return jsonify({"success": True, "message": "Ad deleted successfully"})

@admin_bp.route('/ads/<int:ad_id>/assignment-count')
@admin_required
def get_ad_assignment_count(ad_id):
    """Returns the number of users assigned to an ad"""
    count = query_db("SELECT COUNT(*) as count FROM ad_display_assignments WHERE ad_id = ?", [ad_id], one=True)['count']
    return jsonify({"success": True, "count": count})

@admin_bp.route('/ads/<int:ad_id>/display-to-users', methods=['GET', 'POST'])
@admin_required
def display_ad_to_users(ad_id):
    """Manage which users see this ad"""
    ad = query_db("SELECT * FROM personalized_ads WHERE id = ?", [ad_id], one=True)
    if not ad:
        flash("Ad not found", "danger")
        return redirect(url_for('admin.ads'))
    
    if request.method == 'POST':
        # Get selected user IDs from form
        selected_user_ids = request.form.getlist('user_ids')
        
        # Clear existing assignments for this ad
        execute_db("DELETE FROM ad_display_assignments WHERE ad_id = ?", [ad_id])
        
        # Add new assignments
        for user_id in selected_user_ids:
            try:
                execute_db("""
                    INSERT INTO ad_display_assignments (ad_id, target_user_id)
                    VALUES (?, ?)
                """, [ad_id, user_id])
            except:
                pass
        
        flash("Ad display assignments updated", "success")
        return redirect(url_for('admin.ads'))
    
    # Get all users for the selection list
    users_list = query_db("SELECT id, username, email, membership_tier FROM users ORDER BY username ASC")
    
    # Get currently assigned users
    assigned_users = query_db("SELECT target_user_id FROM ad_display_assignments WHERE ad_id = ?", [ad_id])
    assigned_user_ids = [row['target_user_id'] for row in assigned_users]

    # Process users into tiers for the template
    free_users = []
    elite_users = []
    
    for u in users_list:
        user_dict = dict(u)
        user_dict['is_assigned'] = user_dict['id'] in assigned_user_ids
        
        tier = (user_dict.get('membership_tier') or 'free').lower()
        if tier == 'elite':
            elite_users.append(user_dict)
        else:
            free_users.append(user_dict)
            
    return render_template('admin/display_ad_to_users.html', 
                         ad=dict(ad), 
                         free_users=free_users,
                         elite_users=elite_users,
                         assigned_count=len(assigned_user_ids))

@admin_bp.route('/broadcast', methods=['GET', 'POST'])
@admin_required
def broadcast():
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        msg_type = request.form.get('type', 'info')
        audience = request.form.get('audience', 'all')
        selected_user_ids = request.form.getlist('user_ids')
        
        target_group = 'all'
        target_user_ids = []
        
        if audience == 'selected':
            target_user_ids = [int(uid) for uid in selected_user_ids if uid.isdigit()]
            target_group = None
        elif audience == 'all':
            target_group = 'all'
        else:
            target_group = audience # 'free', 'elite', 'elite_pro'
        
        if not message:
            flash("Message is required", "danger")
            return redirect(url_for('admin.broadcast'))
            
        if audience == 'selected' and not target_user_ids:
            flash("Please select at least one user", "danger")
            return redirect(url_for('admin.broadcast'))

        # Prepare for logging
        target_name = "All Users"
        
        if target_user_ids:
            # Send to multiple specific users
            for uid in target_user_ids:
                execute_db("""
                    INSERT INTO notifications (message, type, target_user_id, target_group)
                    VALUES (?, ?, ?, ?)
                """, [message, msg_type, uid, None])
            
            if len(target_user_ids) == 1:
                user = query_db("SELECT username FROM users WHERE id = ?", [target_user_ids[0]], one=True)
                target_name = f"User: {user['username']}" if user else "Unknown User"
            else:
                target_name = f"{len(target_user_ids)} selected users"
        else:
            # Send to group or all
            execute_db("""
                INSERT INTO notifications (message, type, target_user_id, target_group)
                VALUES (?, ?, ?, ?)
            """, [message, msg_type, None, target_group])
            
            if target_group != 'all':
                target_name = f"Group: {target_group.replace('_', ' ').title()}"
            
        log_admin_activity("broadcast", "notification", None, f"Sent '{msg_type}' notification to {target_name}: {message[:50]}...")
        
        flash(f"Broadcast sent successfully to {target_name}", "success")
        return redirect(url_for('admin.broadcast'))
        
    users_list = query_db("SELECT id, username, membership_tier FROM users ORDER BY username ASC")
    recent_notifications = query_db("""
        SELECT n.*, u.username as target_name
        FROM notifications n
        LEFT JOIN users u ON n.target_user_id = u.id
        ORDER BY n.created_at DESC
        LIMIT 10
    """)
    
    return render_template('admin/broadcast.html', 
                         users=[dict(row) for row in users_list],
                         notifications=[dict(row) for row in recent_notifications])
@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Advanced analytics dashboard"""
    # Date range filter
    days = int(request.args.get('days', 30))
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Revenue analytics
    revenue_by_day = query_db("""
        SELECT DATE(timestamp) as date, 
               SUM(revenue) as daily_revenue,
               COUNT(*) as impressions
        FROM ad_impressions 
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
    """, [start_date.isoformat()])
    
    # Top revenue generating users
    top_revenue_users = query_db("""
        SELECT u.id, u.username, u.email, 
               SUM(ai.revenue) as total_revenue,
               COUNT(ai.id) as impressions
        FROM users u
        JOIN ad_impressions ai ON u.id = ai.user_id
        WHERE ai.timestamp >= ?
        GROUP BY u.id
        ORDER BY total_revenue DESC
        LIMIT 10
    """, [start_date.isoformat()])
    
    # Ad performance by type
    ad_performance = query_db("""
        SELECT ad_type, 
               COUNT(*) as impressions,
               SUM(revenue) as revenue,
               AVG(revenue) as avg_revenue
        FROM ad_impressions
        WHERE timestamp >= ?
        GROUP BY ad_type
    """, [start_date.isoformat()])
    
    # User growth over time
    user_growth = query_db("""
        SELECT DATE(created_at) as date, COUNT(*) as new_users
        FROM users
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """, [start_date.isoformat()])
    
    # Link creation trends
    link_trends = query_db("""
        SELECT DATE(created_at) as date, COUNT(*) as new_links
        FROM links
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """, [start_date.isoformat()])
    
    # Calculate totals
    total_revenue = sum(row['daily_revenue'] for row in revenue_by_day)
    total_impressions = sum(row['impressions'] for row in revenue_by_day)
    
    # Clean data (explicit conversion to dicts to avoid serialization errors)
    revenue_by_day_data = [
        {
            "date": row["date"],
            "daily_revenue": row["daily_revenue"],
            "impressions": row["impressions"]
        } 
        for row in revenue_by_day
    ]
    
    top_revenue_users_data = [
        {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "total_revenue": row["total_revenue"],
            "impressions": row["impressions"]
        }
        for row in top_revenue_users
    ]
    
    ad_performance_data = [
        {
            "ad_type": row["ad_type"],
            "impressions": row["impressions"],
            "revenue": row["revenue"],
            "avg_revenue": row["avg_revenue"]
        }
        for row in ad_performance
    ]
    
    user_growth_data = [{"date": row["date"], "new_users": row["new_users"]} for row in user_growth]
    link_trends_data = [{"date": row["date"], "new_links": row["new_links"]} for row in link_trends]
    
    return render_template('admin/analytics.html',
                         revenue_by_day=revenue_by_day_data,
                         top_revenue_users=top_revenue_users_data,
                         ad_performance=ad_performance_data,
                         user_growth=user_growth_data,
                         link_trends=link_trends_data,
                         total_revenue=total_revenue,
                         total_impressions=total_impressions,
                         days=days)

@admin_bp.route('/activity')
@admin_required
def activity():
    """User activity monitoring"""
    page = int(request.args.get('page', 1))
    per_page = 50
    user_filter = request.args.get('user', '').strip()
    activity_filter = request.args.get('activity', '').strip()
    
    # Build query
    where_conditions = []
    params = []
    
    if user_filter:
        where_conditions.append("u.username LIKE ?")
        params.append(f"%{user_filter}%")
    
    if activity_filter:
        where_conditions.append("ua.activity_type LIKE ?")
        params.append(f"%{activity_filter}%")
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    activities = query_db(f"""
        SELECT ua.*, u.username, ua.user_id
        FROM user_activity ua
        JOIN users u ON ua.user_id = u.id
        {where_clause}
        ORDER BY ua.timestamp DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, (page-1)*per_page])
    
    # Get total count for pagination
    total_activities = query_db(f"""
        SELECT COUNT(*) as count
        FROM user_activity ua
        JOIN users u ON ua.user_id = u.id
        {where_clause}
    """, params, one=True)['count']
    
    total_pages = (total_activities + per_page - 1) // per_page
    
    return render_template('admin/activity.html',
                         activities=[dict(row) for row in activities],
                         page=page,
                         total_pages=total_pages,
                         user_filter=user_filter,
                         activity_filter=activity_filter)

@admin_bp.route('/export/users')
@admin_required
def export_users():
    """Export users data to CSV"""
    users_data = query_db("""
        SELECT u.username, u.email, u.membership_tier, u.created_at,
               (SELECT COUNT(*) FROM links l WHERE l.user_id = u.id) as link_count,
               (SELECT COUNT(*) FROM visits v JOIN links l ON v.link_id = l.id WHERE l.user_id = u.id) as total_clicks,
               (SELECT COALESCE(SUM(revenue), 0) FROM ad_impressions ai WHERE ai.user_id = u.id) as total_revenue
        FROM users u
        ORDER BY u.created_at DESC
    """)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'User', 'Email', 'Membership', 'Links', 'Clicks', 'Revenue', 'Joined'
    ])
    
    # Write data
    for user in users_data:
        writer.writerow([
            user['username'], 
            user['email'], 
            user['membership_tier'] or 'free', 
            user['link_count'], 
            user['total_clicks'], 
            f"${user['total_revenue']:.2f}",
            user['created_at'][:10] if user['created_at'] else '-'
        ])
    
    log_admin_activity("export_users", details="Exported users data to CSV")
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=users_export.csv"}
    )

@admin_bp.route('/export/revenue')
@admin_required
def export_revenue():
    """Export revenue data to CSV (Ad Summary)"""
    # Get all ads with their total revenue and impressions
    revenue_data = query_db("""
        SELECT pa.title, u.username, pa.is_active,
               COALESCE(COUNT(ai.id), 0) as impressions,
               COALESCE(SUM(ai.revenue), 0) as total_revenue
        FROM personalized_ads pa
        JOIN users u ON pa.user_id = u.id
        LEFT JOIN ad_impressions ai ON pa.id = ai.ad_id
        GROUP BY pa.id
        ORDER BY total_revenue DESC
    """)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'SrNo', 'Title', 'Created By', 'Status', 'Impressions', 'Revenue'
    ])
    
    # Write data
    for i, ad in enumerate(revenue_data, 1):
        status = 'Active' if ad['is_active'] else 'Not Active'
        writer.writerow([
            i,
            ad['title'],
            ad['username'],
            status,
            ad['impressions'],
            f"${ad['total_revenue']:.2f}"
        ])
    
    log_admin_activity("export_revenue", details="Exported revenue summary to CSV")
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=ad_revenue_report.csv"}
    )

@admin_bp.route('/maintenance', methods=['GET', 'POST'])
@admin_required
def maintenance():
    """Site Maintenance Settings"""
    if request.method == 'POST':
        maintenance_mode = request.form.get('maintenance_mode') == 'on'
        message = request.form.get('maintenance_message', '').strip()
        
        # Save settings
        execute_db("INSERT OR REPLACE INTO system_settings (setting_key, setting_value) VALUES (?, ?)", 
                  ['maintenance_mode', '1' if maintenance_mode else '0'])
        execute_db("INSERT OR REPLACE INTO system_settings (setting_key, setting_value) VALUES (?, ?)", 
                  ['maintenance_message', message])
        
        status = "enabled" if maintenance_mode else "disabled"
        log_admin_activity("maintenance_update", details=f"Maintenance mode {status}")
        flash(f"Maintenance mode {status} successfully", "success")
        return redirect(url_for('admin.maintenance'))
    
    # Get current settings
    mode_setting = query_db("SELECT setting_value FROM system_settings WHERE setting_key = 'maintenance_mode'", one=True)
    msg_setting = query_db("SELECT setting_value FROM system_settings WHERE setting_key = 'maintenance_message'", one=True)
    
    is_maintenance_on = mode_setting['setting_value'] == '1' if mode_setting else False
    maintenance_message = msg_setting['setting_value'] if msg_setting else "We are currently performing scheduled maintenance. We should be back shortly."
    
    return render_template('admin/maintenance.html', 
                         is_maintenance_on=is_maintenance_on,
                         maintenance_message=maintenance_message)

@admin_bp.route('/revenue', methods=['GET'])
@admin_required
def get_revenue_api():
    """
    Revenue API for admin dashboard
    Returns:
    - total revenue
    - daily revenue breakdown
    """
    
    # ---- Total Revenue ----
    total_row = query_db(
        "SELECT SUM(revenue) AS total FROM ad_impressions", 
        one=True
    )

    total_revenue = total_row["total"] if total_row and total_row["total"] else 0.0

    # ---- Revenue By Day (for charts) ----
    daily_rows = query_db("""
        SELECT 
            DATE(timestamp) AS date,
            SUM(revenue) AS amount
        FROM ad_impressions
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp)
    """)

    # Clean data (explicit conversion to dicts to avoid serialization errors)
    daily_revenue = [
        {
            "date": row["date"],
            "amount": row["amount"]
        }
        for row in daily_rows
    ]

    # FINAL JSON RESPONSE (SAFE)
    return jsonify({
        "total_revenue": round(total_revenue, 2),
        "daily_revenue": daily_revenue
    })

def log_admin_activity(action, target_type=None, target_id=None, details=None):
    """Log admin activity"""
    try:
        ip_address = request.remote_addr if request else "system"
        execute_db("""
            INSERT INTO admin_activity_log 
            (admin_id, action, target_type, target_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [1, action, target_type, target_id, details, ip_address])  # admin_id = 1 for simplicity
    except Exception as e:
        print(f"Error logging admin activity: {e}")

def track_user_activity(user_id, activity_type, details=None, ip_address=None):
    """Track user activity for admin monitoring"""
    try:
        if not ip_address:
            ip_address = request.remote_addr if request else "system"
        
        execute_db("""
            INSERT INTO user_activity 
            (user_id, activity_type, details, ip_address)
            VALUES (?, ?, ?, ?)
        """, [user_id, activity_type, details, ip_address])
    except Exception as e:
        print(f"Error tracking user activity: {e}")

def track_ad_impression(link_id, user_id, ad_type, ad_position, ip_address=None, ad_id=None):
    """Track ad impression and calculate revenue"""
    revenue = AD_REVENUE_RATES.get(ad_type, 0.0)
    
    execute_db("""
        INSERT INTO ad_impressions 
        (link_id, user_id, ad_type, ad_position, revenue, ip_address, ad_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [link_id, user_id, ad_type, ad_position, revenue, ip_address, ad_id])
    
    return revenue

# Initialize admin tables when module is imported
try:
    ensure_admin_tables()
except Exception as e:
    print(f"Error initializing admin tables: {e}")