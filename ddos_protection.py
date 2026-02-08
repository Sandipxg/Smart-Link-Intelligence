# DDoS Protection System
import sqlite3
import time
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from functools import wraps
from database import query_db, execute_db
from config import MEMBERSHIP_TIERS

# Create Blueprint for DDoS protection routes
ddos_bp = Blueprint('ddos', __name__, url_prefix='/ddos-protection')

def ddos_required(f):
    """Decorator to require DDoS protection feature (Elite Pro only)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get("user"):
            flash("Please log in to continue", "warning")
            return redirect(url_for("login"))
            
        # Check Membership safely
        user_dict = dict(g.user)
        user_tier = user_dict.get("membership_tier", "free")
        
        # ddos_protection key in MEMBERSHIP_TIERS defines access
        tier_data = MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])
        if not tier_data.get("ddos_protection", False):
            flash("DDoS Protection is exclusive to Elite Pro members. Please upgrade to access this feature.", "warning")
            return redirect(url_for("index"))
            
        return f(*args, **kwargs)
    return decorated_function

class DDoSProtection:
    def __init__(self, database_path):
        self.db_path = database_path
        self.rate_limits = {
            'requests_per_ip_per_minute': 60,
            'requests_per_ip_per_hour': 1000,
            'requests_per_link_per_minute': 500,
            'burst_threshold': 100,
            'suspicious_threshold': 10,
            'ddos_threshold': 50,
            'rapid_click_limit': 0.3,
            'health_kill_switch': 5,
            'detection_window_minutes': 5,
        }
        
        self.request_cache = defaultdict(list)
        self.blocked_ips = {}
        
    def get_link_rules(self, link_id):
        """Get DDoS rules for a link (custom or default)"""
        # Default rules
        rules = self.rate_limits.copy()
        
        if not link_id:
            return rules
            
        try:
            # Get security_profile_id and user_id for the link
            link = query_db("SELECT security_profile_id, user_id FROM links WHERE id = ?", [link_id], one=True)
            
            profile = None
            if link:
                if link['security_profile_id']:
                    # Get the specific security profile settings
                    profile = query_db("SELECT * FROM security_profiles WHERE id = ?", [link['security_profile_id']], one=True)
                else:
                    # Fallback to user's default security profile
                    profile = query_db("SELECT * FROM security_profiles WHERE user_id = ? AND is_default = 1", [link['user_id']], one=True)
            
            if profile:
                rules.update({
                    'requests_per_ip_per_minute': profile['requests_per_ip_per_minute'],
                    'requests_per_ip_per_hour': profile['requests_per_ip_per_hour'],
                    'requests_per_link_per_minute': profile['requests_per_link_per_minute'],
                    'burst_threshold': profile['burst_threshold'],
                    'suspicious_threshold': profile['suspicious_threshold'],
                    'ddos_threshold': profile['ddos_threshold'],
                    'rapid_click_limit': profile['rapid_click_limit'],
                    'health_kill_switch': profile['health_kill_switch'],
                    'detection_window_minutes': profile['detection_window_minutes'],
                })
        except Exception as e:
            print(f"Error fetching DDoS rules: {e}")
            
        return rules
        
        
    def check_rate_limit(self, ip_address, link_id=None):
        """Check if request should be rate limited"""
        from flask import request
        
        # Check for load testing headers - bypass rate limiting for legitimate tests
        if request and hasattr(request, 'headers'):
            user_agent = request.headers.get("User-Agent", "").lower()
            x_load_test = request.headers.get("X-Load-Test", "").lower()
            
            # Allow if explicitly marked as load test
            if x_load_test == "true":
                return True, 'load_test_allowed'
                
            # Allow common load testing tools
            load_test_agents = [
                "jmeter", "apache-httpclient", "loadrunner", "gatling", 
                "artillery", "k6", "wrk", "siege", "ab/", "curl/",
                "python-requests", "go-http-client"
            ]
            
            if any(agent in user_agent for agent in load_test_agents):
                return True, 'load_test_tool_allowed'
        
        now = datetime.utcnow()
        
        # Get rules for this link
        rules = self.get_link_rules(link_id)
        
        # Clean old entries
        self._cleanup_cache(now)
        
        # Check IP-based rate limits
        ip_requests = self.request_cache[f"ip_{ip_address}"]
        
        # Count requests in last minute
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [req for req in ip_requests if req > minute_ago]
        
        if len(recent_requests) > rules['requests_per_ip_per_minute']:
            self._log_ddos_event(link_id, 'rate_limit', 2, ip_address)
            return False, 'rate_limited'
            
        # Count requests in last hour
        hour_ago = now - timedelta(hours=1)
        hourly_requests = [req for req in ip_requests if req > hour_ago]
        
        if len(hourly_requests) > rules['requests_per_ip_per_hour']:
            self._log_ddos_event(link_id, 'hourly_rate_limit', 2, ip_address)
            return False, 'rate_limited'
        
        # Check for burst attacks (requests in 10 seconds)
        burst_window = now - timedelta(seconds=10)
        burst_requests = [req for req in ip_requests if req > burst_window]
        
        if len(burst_requests) > rules['burst_threshold']:
            self._log_ddos_event(link_id, 'burst_attack', 4, ip_address)
            return False, 'burst_attack'
        
        # Add current request to cache
        self.request_cache[f"ip_{ip_address}"].append(now)
        
        return True, 'allowed'
    
    def detect_ddos_attack(self, link_id):
        """Detect if link is under DDoS attack"""
        from flask import request
        
        # Get rules for this link
        rules = self.get_link_rules(link_id)
        
        # Check for load testing - don't trigger DDoS protection for legitimate tests
        if request and hasattr(request, 'headers'):
            user_agent = request.headers.get("User-Agent", "").lower()
            x_load_test = request.headers.get("X-Load-Test", "").lower()
            
            # Skip DDoS detection for load tests
            if x_load_test == "true":
                return False, 'load_test_bypass', 1
                
            # Skip for common load testing tools
            load_test_agents = [
                "jmeter", "apache-httpclient", "loadrunner", "gatling", 
                "artillery", "k6", "wrk", "siege", "ab/", "curl/",
                "python-requests", "go-http-client"
            ]
            
            if any(agent in user_agent for agent in load_test_agents):
                return False, 'load_test_tool_bypass', 1
        
        # Check recent suspicious activity using CUSTOM WINDOW
        window = rules.get('detection_window_minutes', 5)
        recent_suspicious = query_db(f"""
            SELECT COUNT(*) as count
            FROM visits 
            WHERE link_id = ? 
            AND is_suspicious = 1 
            AND datetime(ts) > datetime('now', '-{window} minutes')
        """, [link_id], one=True)
        
        # Check request rate
        recent_requests = query_db("""
            SELECT COUNT(*) as count
            FROM visits 
            WHERE link_id = ? 
            AND datetime(ts) > datetime('now', '-1 minute')
        """, [link_id], one=True)
        
        suspicious_count = recent_suspicious['count'] if recent_suspicious else 0
        request_count = recent_requests['count'] if recent_requests else 0
        
        # DDoS Detection Logic
        if suspicious_count > rules['ddos_threshold']:
            return True, 'high_suspicious_activity', 5
        elif request_count > rules['requests_per_link_per_minute']:
            return True, 'high_request_rate', 4
        elif suspicious_count > rules['suspicious_threshold']:
            return True, 'moderate_suspicious_activity', 3
        
        return False, 'normal', 1
    
    def apply_protection(self, link_id, protection_level):
        """Apply protection measures based on severity"""
        
        if protection_level >= 5:
            # Level 5: Break the link (disable completely)
            execute_db("""
                UPDATE links 
                SET protection_level = ?, auto_disabled = 1, ddos_detected_at = ?
                WHERE id = ?
            """, [protection_level, datetime.utcnow().isoformat(), link_id])
            
            self._log_ddos_event(link_id, 'link_disabled', 5)
            return 'link_disabled'
            
        elif protection_level >= 4:
            # Level 4: Temporary disable (1 hour)
            execute_db("""
                UPDATE links 
                SET protection_level = ?, ddos_detected_at = ?
                WHERE id = ?
            """, [protection_level, datetime.utcnow().isoformat(), link_id])
            
            self._log_ddos_event(link_id, 'temporary_disable', 4)
            return 'temporary_disabled'
            
        elif protection_level >= 3:
            # Level 3: Captcha required
            execute_db("""
                UPDATE links 
                SET protection_level = ?
                WHERE id = ?
            """, [protection_level, link_id])
            
            self._log_ddos_event(link_id, 'captcha_required', 3)
            return 'captcha_required'
        
        return 'normal'
    
    def is_link_protected(self, link_id):
        """Check if link has active protection"""
        link = query_db("""
            SELECT protection_level, auto_disabled, ddos_detected_at
            FROM links WHERE id = ?
        """, [link_id], one=True)
        
        if not link:
            return False, 'not_found'
        
        if link['auto_disabled']:
            return True, 'disabled'
        elif link['protection_level'] >= 4:
            # Check if temporary disable has expired
            if link['ddos_detected_at']:
                detected_time = datetime.fromisoformat(link['ddos_detected_at'])
                if datetime.utcnow() - detected_time > timedelta(hours=1):
                    # Reset protection level
                    self._reset_protection(link_id)
                    return False, 'normal'
            return True, 'temporary_disabled'
        elif link['protection_level'] >= 3:
            return True, 'captcha_required'
        
        return False, 'normal'
    
    def _cleanup_cache(self, now):
        """Clean old entries from request cache"""
        cutoff = now - timedelta(hours=1)
        for key in list(self.request_cache.keys()):
            self.request_cache[key] = [
                req for req in self.request_cache[key] 
                if req > cutoff
            ]
            if not self.request_cache[key]:
                del self.request_cache[key]
    
    def _log_ddos_event(self, link_id, event_type, severity, ip_address=None):
        """Log DDoS event to database"""
        execute_db("""
            INSERT INTO ddos_events 
            (link_id, event_type, severity, ip_address, detected_at, protection_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [link_id, event_type, severity, ip_address, 
              datetime.utcnow().isoformat(), severity])
    
    def _reset_protection(self, link_id):
        """Reset protection level for a link"""
        execute_db("""
            UPDATE links 
            SET protection_level = 0, ddos_detected_at = NULL
            WHERE id = ?
        """, [link_id])
    
    def get_protection_stats(self, link_id):
        """Get protection statistics for a link"""
        stats = query_db("""
            SELECT 
                event_type,
                COUNT(*) as count,
                MAX(detected_at) as last_event
            FROM ddos_events 
            WHERE link_id = ?
            GROUP BY event_type
            ORDER BY count DESC
        """, [link_id])
        
        if not stats:
            return []
            
        return [dict(row) for row in stats]

# DDoS Protection Routes
@ddos_bp.route('/')
@ddos_required
def ddos_protection_dashboard():
    """DDoS Protection Dashboard"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Get user's links with protection status
    links_with_protection = query_db(
        """
        SELECT l.*, 
               COALESCE(de.event_count, 0) as ddos_events,
               COALESCE(de.last_event, '') as last_ddos_event
        FROM links l
        LEFT JOIN (
            SELECT link_id, 
                   COUNT(*) as event_count,
                   MAX(detected_at) as last_event
            FROM ddos_events 
            GROUP BY link_id
        ) de ON l.id = de.link_id
        WHERE l.user_id = ?
        ORDER BY l.created_at DESC
        """,
        [g.user["id"]]
    )
    
    # Get recent DDoS events for user's links
    recent_events = query_db(
        """
        SELECT de.*, l.code, l.primary_url
        FROM ddos_events de
        JOIN links l ON de.link_id = l.id
        WHERE l.user_id = ?
        ORDER BY de.detected_at DESC
        LIMIT 20
        """,
        [g.user["id"]]
    )
    
    # Track DDoS dashboard view
    track_user_activity(g.user["id"], "view_ddos_dashboard", "Viewed DDoS protection dashboard")
    
    return render_template("ddos_protection.html", 
                         links=links_with_protection, 
                         recent_events=recent_events)


@ddos_bp.route('/recover/<int:link_id>', methods=["POST"])
@ddos_required
def recover_link(link_id):
    """Manually recover a DDoS-protected link"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check if link belongs to current user
    link = query_db(
        "SELECT * FROM links WHERE id = ? AND user_id = ?",
        [link_id, g.user["id"]], one=True
    )
    
    if not link:
        flash("Link not found", "danger")
        return redirect(url_for("ddos.ddos_protection_dashboard"))
    
    # Reset protection level
    execute_db(
        """
        UPDATE links 
        SET protection_level = 0, auto_disabled = 0, ddos_detected_at = NULL
        WHERE id = ?
        """,
        [link_id]
    )
    
    # Log recovery event
    execute_db(
        """
        INSERT INTO ddos_events 
        (link_id, event_type, severity, detected_at, protection_level)
        VALUES (?, ?, ?, ?, ?)
        """,
        [link_id, 'manual_recovery', 1, datetime.utcnow().isoformat(), 0]
    )
    
    track_user_activity(g.user["id"], "recover_link", f"Manually recovered link: {link['code']}")
    flash(f"Link '{link['code']}' has been recovered and is now active", "success")
    return redirect(url_for("ddos.ddos_protection_dashboard"))


@ddos_bp.route('/stats/<int:link_id>')
@ddos_required
def ddos_link_stats(link_id):
    """Get detailed DDoS statistics for a specific link"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check if link belongs to current user
    link = query_db(
        "SELECT * FROM links WHERE id = ? AND user_id = ?",
        [link_id, g.user["id"]], one=True
    )
    
    if not link:
        abort(404)
    
    # Get protection statistics
    ddos_protection = DDoSProtection("smart_links.db")  # Use relative path
    stats = ddos_protection.get_protection_stats(link_id)
    
    # Get detailed events
    events = query_db(
        """
        SELECT * FROM ddos_events 
        WHERE link_id = ?
        ORDER BY detected_at DESC
        LIMIT 50
        """,
        [link_id]
    )
    
    track_user_activity(g.user["id"], "view_ddos_stats", f"Viewed DDoS stats for link: {link['code']}")
    
    return render_template("ddos_link_stats.html", 
                         link=link, 
                         stats=stats, 
                         events=events)


@ddos_bp.route('/security-profiles')
@ddos_required
def security_profiles():
    """Manage security profiles"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    profiles = query_db(
        "SELECT * FROM security_profiles WHERE user_id = ? ORDER BY is_default DESC, profile_name ASC",
        [g.user["id"]]
    )
    
    track_user_activity(g.user["id"], "view_security_profiles", "Viewed security profiles")
    return render_template("security_profiles.html", profiles=profiles)


@ddos_bp.route('/security-profiles/create', methods=["POST"])
@ddos_required
def create_security_profile():
    """Create a new security profile"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    profile_name = request.form.get("profile_name", "").strip()
    
    # Rate Limits
    ip_min = int(request.form.get("requests_per_ip_per_minute", 60))
    ip_hour = int(request.form.get("requests_per_ip_per_hour", 1000))
    link_min = int(request.form.get("requests_per_link_per_minute", 500))
    burst = int(request.form.get("burst_threshold", 100))
    
    # Thresholds
    suspicious = int(request.form.get("suspicious_threshold", 10))
    ddos = int(request.form.get("ddos_threshold", 50))
    
    # Behavioral
    rapid = float(request.form.get("rapid_click_limit", 0.3))
    kill = int(request.form.get("health_kill_switch", 5))
    window = int(request.form.get("detection_window_minutes", 5))
    
    if not profile_name:
        flash("Profile name is required", "danger")
        return redirect(url_for("ddos.security_profiles"))
        
    # Validation
    if ddos <= suspicious:
        flash("DDoS threshold must be higher than suspicious threshold", "danger")
        return redirect(url_for("ddos.security_profiles"))
        
    # Limit to 5 profiles
    count = query_db("SELECT COUNT(*) as count FROM security_profiles WHERE user_id = ?", [g.user["id"]], one=True)["count"]
    if count >= 6: # 1 default + 5 custom
        flash("You can only have up to 5 custom security profiles", "warning")
        return redirect(url_for("ddos.security_profiles"))

    execute_db(
        """
        INSERT INTO security_profiles 
        (user_id, profile_name, requests_per_ip_per_minute, requests_per_ip_per_hour, 
         requests_per_link_per_minute, burst_threshold, suspicious_threshold, ddos_threshold,
         rapid_click_limit, health_kill_switch, detection_window_minutes, is_default)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        [g.user["id"], profile_name, ip_min, ip_hour, link_min, burst, suspicious, ddos, rapid, kill, window]
    )
    
    track_user_activity(g.user["id"], "create_security_profile", f"Created security profile: {profile_name}")
    flash(f"Security profile '{profile_name}' created successfully", "success")
    return redirect(url_for("ddos.security_profiles"))


@ddos_bp.route('/security-profiles/update/<int:profile_id>', methods=["POST"])
@ddos_required
def update_security_profile(profile_id):
    """Update a security profile"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check ownership
    profile = query_db("SELECT * FROM security_profiles WHERE id = ? AND user_id = ?", [profile_id, g.user["id"]], one=True)
    if not profile:
        flash("Profile not found", "danger")
        return redirect(url_for("ddos.security_profiles"))
        
    profile_name = request.form.get("profile_name", "").strip()
    
    # Get values
    ip_min = int(request.form.get("requests_per_ip_per_minute", 60))
    ip_hour = int(request.form.get("requests_per_ip_per_hour", 1000))
    link_min = int(request.form.get("requests_per_link_per_minute", 500))
    burst = int(request.form.get("burst_threshold", 100))
    suspicious = int(request.form.get("suspicious_threshold", 10))
    ddos = int(request.form.get("ddos_threshold", 50))
    rapid = float(request.form.get("rapid_click_limit", 0.3))
    kill = int(request.form.get("health_kill_switch", 5))
    window = int(request.form.get("detection_window_minutes", 5))
    
    if not profile_name:
        flash("Profile name is required", "danger")
        return redirect(url_for("ddos.security_profiles"))

    execute_db(
        """
        UPDATE security_profiles 
        SET profile_name = ?, requests_per_ip_per_minute = ?, requests_per_ip_per_hour = ?,
            requests_per_link_per_minute = ?, burst_threshold = ?, suspicious_threshold = ?,
            ddos_threshold = ?, rapid_click_limit = ?, health_kill_switch = ?,
            detection_window_minutes = ?
        WHERE id = ?
        """,
        [profile_name, ip_min, ip_hour, link_min, burst, suspicious, ddos, rapid, kill, window, profile_id]
    )
    
    track_user_activity(g.user["id"], "update_security_profile", f"Updated security profile: {profile_name}")
    flash(f"Security profile '{profile_name}' updated successfully", "success")
    return redirect(url_for("ddos.security_profiles"))


@ddos_bp.route('/security-profiles/delete/<int:profile_id>', methods=["POST"])
@ddos_required
def delete_security_profile(profile_id):
    """Delete a security profile"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check ownership and not default
    profile = query_db("SELECT * FROM security_profiles WHERE id = ? AND user_id = ?", [profile_id, g.user["id"]], one=True)
    if not profile:
        flash("Profile not found", "danger")
    elif profile['is_default']:
        flash("Cannot delete the default profile", "danger")
    else:
        # Update links using this profile to use the default profile
        default_profile = query_db("SELECT id FROM security_profiles WHERE user_id = ? AND is_default = 1", [g.user["id"]], one=True)
        if default_profile:
            execute_db("UPDATE links SET security_profile_id = ? WHERE security_profile_id = ?", [default_profile['id'], profile_id])
            
        execute_db("DELETE FROM security_profiles WHERE id = ?", [profile_id])
        track_user_activity(g.user["id"], "delete_security_profile", f"Deleted security profile: {profile['profile_name']}")
        flash(f"Security profile '{profile['profile_name']}' deleted", "info")
        
    return redirect(url_for("ddos.security_profiles"))


@ddos_bp.route('/security-profiles/set-default/<int:profile_id>', methods=["POST"])
@ddos_required
def set_default_security_profile(profile_id):
    """Set a security profile as default"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check ownership
    profile = query_db("SELECT * FROM security_profiles WHERE id = ? AND user_id = ?", [profile_id, g.user["id"]], one=True)
    if not profile:
        flash("Profile not found", "danger")
    else:
        # Reset all
        execute_db("UPDATE security_profiles SET is_default = 0 WHERE user_id = ?", [g.user["id"]])
        # Set new default
        execute_db("UPDATE security_profiles SET is_default = 1 WHERE id = ?", [profile_id])
        track_user_activity(g.user["id"], "set_default_security_profile", f"Set default security profile: {profile['profile_name']}")
        flash(f"Security profile '{profile['profile_name']}' is now the default", "success")
        
    return redirect(url_for("ddos.security_profiles"))