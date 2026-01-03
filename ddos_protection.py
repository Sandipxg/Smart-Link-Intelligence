# DDoS Protection System
import sqlite3
import time
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

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
        
        # In-memory cache for fast lookups
        self.request_cache = defaultdict(list)
        self.blocked_ips = {}
        
    def check_rate_limit(self, ip_address, link_id=None):
        """Check if request should be rate limited"""
        now = datetime.utcnow()
        
        # Clean old entries
        self._cleanup_cache(now)
        
        # Check IP-based rate limits
        ip_requests = self.request_cache[f"ip_{ip_address}"]
        
        # Count requests in last minute
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [req for req in ip_requests if req > minute_ago]
        
        if len(recent_requests) > self.rate_limits['requests_per_ip_per_minute']:
            self._log_ddos_event(link_id, 'rate_limit', 2, ip_address)
            return False, 'rate_limited'
        
        # Check for burst attacks (100+ requests in 10 seconds)
        burst_window = now - timedelta(seconds=10)
        burst_requests = [req for req in ip_requests if req > burst_window]
        
        if len(burst_requests) > self.rate_limits['burst_threshold']:
            self._log_ddos_event(link_id, 'burst_attack', 4, ip_address)
            return False, 'burst_attack'
        
        # Add current request to cache
        self.request_cache[f"ip_{ip_address}"].append(now)
        
        return True, 'allowed'
    
    def detect_ddos_attack(self, link_id):
        """Detect if link is under DDoS attack"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Check recent suspicious activity
        recent_suspicious = conn.execute("""
            SELECT COUNT(*) as count
            FROM visits 
            WHERE link_id = ? 
            AND is_suspicious = 1 
            AND datetime(ts) > datetime('now', '-5 minutes')
        """, [link_id]).fetchone()
        
        # Check request rate
        recent_requests = conn.execute("""
            SELECT COUNT(*) as count
            FROM visits 
            WHERE link_id = ? 
            AND datetime(ts) > datetime('now', '-1 minute')
        """, [link_id]).fetchone()
        
        conn.close()
        
        suspicious_count = recent_suspicious['count'] if recent_suspicious else 0
        request_count = recent_requests['count'] if recent_requests else 0
        
        # DDoS Detection Logic
        if suspicious_count > self.rate_limits['ddos_threshold']:
            return True, 'high_suspicious_activity', 5
        elif request_count > self.rate_limits['requests_per_link_per_minute']:
            return True, 'high_request_rate', 4
        elif suspicious_count > self.rate_limits['suspicious_threshold']:
            return True, 'moderate_suspicious_activity', 3
        
        return False, 'normal', 1
    
    def apply_protection(self, link_id, protection_level):
        """Apply protection measures based on severity"""
        conn = sqlite3.connect(self.db_path)
        
        if protection_level >= 5:
            # Level 5: Break the link (disable completely)
            conn.execute("""
                UPDATE links 
                SET protection_level = ?, auto_disabled = 1, ddos_detected_at = ?
                WHERE id = ?
            """, [protection_level, datetime.utcnow().isoformat(), link_id])
            
            self._log_ddos_event(link_id, 'link_disabled', 5)
            conn.commit()
            conn.close()
            return 'link_disabled'
            
        elif protection_level >= 4:
            # Level 4: Temporary disable (1 hour)
            conn.execute("""
                UPDATE links 
                SET protection_level = ?, ddos_detected_at = ?
                WHERE id = ?
            """, [protection_level, datetime.utcnow().isoformat(), link_id])
            
            self._log_ddos_event(link_id, 'temporary_disable', 4)
            conn.commit()
            conn.close()
            return 'temporary_disabled'
            
        elif protection_level >= 3:
            # Level 3: Captcha required
            conn.execute("""
                UPDATE links 
                SET protection_level = ?
                WHERE id = ?
            """, [protection_level, link_id])
            
            self._log_ddos_event(link_id, 'captcha_required', 3)
            conn.commit()
            conn.close()
            return 'captcha_required'
        
        conn.close()
        return 'normal'
    
    def is_link_protected(self, link_id):
        """Check if link has active protection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        link = conn.execute("""
            SELECT protection_level, auto_disabled, ddos_detected_at
            FROM links WHERE id = ?
        """, [link_id]).fetchone()
        
        conn.close()
        
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
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO ddos_events 
            (link_id, event_type, severity, ip_address, detected_at, protection_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [link_id, event_type, severity, ip_address, 
              datetime.utcnow().isoformat(), severity])
        conn.commit()
        conn.close()
    
    def _reset_protection(self, link_id):
        """Reset protection level for a link"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE links 
            SET protection_level = 0, ddos_detected_at = NULL
            WHERE id = ?
        """, [link_id])
        conn.commit()
        conn.close()
    
    def get_protection_stats(self, link_id):
        """Get protection statistics for a link"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        stats = conn.execute("""
            SELECT 
                event_type,
                COUNT(*) as count,
                MAX(detected_at) as last_event
            FROM ddos_events 
            WHERE link_id = ?
            GROUP BY event_type
            ORDER BY count DESC
        """, [link_id]).fetchall()
        
        conn.close()
        return [dict(row) for row in stats]