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
            
        # Check Membership
        user_dict = dict(g.user) if g.user else {}
        user_tier = user_dict.get("membership_tier", "free")
        if not user_tier: 
            user_tier = "free"
        
        if not MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])["ddos_protection"]:
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
            'burst_threshold': 100,  # requests in 10 seconds
            'suspicious_threshold': 10,
            'ddos_threshold': 50,  # suspicious requests to trigger DDoS
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
            # Get behavior_rule_id for the link
            link = query_db("SELECT behavior_rule_id FROM links WHERE id = ?", [link_id], one=True)
            
            if link and link['behavior_rule_id']:
                # Get the rule settings
                rule = query_db("SELECT * FROM behavior_rules WHERE id = ?", [link['behavior_rule_id']], one=True)
                if rule and 'requests_per_ip_per_minute' in rule.keys(): # Check if columns exist
                    rules.update({
                        'requests_per_ip_per_minute': rule['requests_per_ip_per_minute'],
                        'requests_per_ip_per_hour': rule['requests_per_ip_per_hour'],
                        'requests_per_link_per_minute': rule['requests_per_link_per_minute'],
                        'burst_threshold': rule['burst_threshold'],
                        'suspicious_threshold': rule['suspicious_threshold'],
                        'ddos_threshold': rule['ddos_threshold'],
                    })
        except Exception as e:
            print(f"Error fetching DDoS rules: {e}")
            
        return rules
        
    def check_rate_limit(self, ip_address, link_id=None):
        """Check if request should be rate limited"""
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
        
        # Check for burst attacks (100+ requests in 10 seconds)
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
        # Check recent suspicious activity
        recent_suspicious = query_db("""
            SELECT COUNT(*) as count
            FROM visits 
            WHERE link_id = ? 
            AND is_suspicious = 1 
            AND datetime(ts) > datetime('now', '-5 minutes')
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
        
        # Get rules for this link
        rules = self.get_link_rules(link_id)
        
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