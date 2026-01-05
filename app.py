import hashlib
import os
import re
import sqlite3
import string
import uuid
import smtplib
import csv
import io
# GeoIP removed in favor of ip-api.com
# import geoip2.database
# import geoip2.errors
GEOIP_AVAILABLE = False
import requests
import tarfile
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
# Import threading for async IP fetching if needed, though we'll keep it simple for now
import threading
from functools import wraps
from werkzeug.utils import secure_filename

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_from_directory,
    jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash

# Import DDoS Protection
from ddos_protection import DDoSProtection
from chatbot import get_chat_response
from admin_panel import admin_bp, ensure_admin_tables, track_ad_impression, track_user_activity

# Configuration
DATABASE = os.path.join(os.path.dirname(__file__), "smart_links.db")
SESSION_COOKIE_NAME = "smartlink_session"
RETURNING_WINDOW_HOURS = 48
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = (800, 600)  # Max width, height in pixels
MULTI_CLICK_THRESHOLD = 3
SUSPICIOUS_INTERVAL_SECONDS = 1.0
ATTENTION_DECAY_DAYS = 14
STATE_DECAY_DAYS = 21
USER_SESSION_KEY = "uid"

# Membership Configuration
MEMBERSHIP_TIERS = {
    "free": {"max_links": 10, "validity_days": 7, "name": "Free User", "custom_ads": False, "ddos_protection": False, "ad_free": False},
    "elite": {"max_links": 35, "validity_days": None, "name": "Elite User", "custom_ads": False, "ddos_protection": False, "ad_free": False},
    "elite_pro": {"max_links": float('inf'), "validity_days": None, "name": "Elite Pro User", "custom_ads": True, "ddos_protection": True, "ad_free": True},
}


# GeoIP Configuration
GEOIP_DB_PATH = os.path.join(os.path.dirname(__file__), "GeoLite2-City.mmdb")
GEOIP_DB_URL = "https://download.maxmind.com/app/geoip_update?edition_id=GeoLite2-City&license_key=YOUR_LICENSE_KEY&suffix=tar.gz"


def download_geoip_database():
    """Download and extract GeoLite2 database if not exists."""
    if os.path.exists(GEOIP_DB_PATH):
        return True
    
    try:
        print("Downloading GeoLite2 database...")
        
        # For demo purposes, we'll use a direct download URL
        # In production, you should register for a MaxMind account and use your license key
        # This is a fallback URL that might work for testing
        fallback_url = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"
        
        response = requests.get(fallback_url, stream=True)
        response.raise_for_status()
        
        with open(GEOIP_DB_PATH, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"GeoLite2 database downloaded to {GEOIP_DB_PATH}")
        return True
        
    except Exception as e:
        print(f"Failed to download GeoIP database: {e}")
        print("Using fallback location detection...")
        return False


def get_link_password_hash(link):
    """Safely get password hash from link row object"""
    try:
        return link["password_hash"] if link["password_hash"] else None
    except (KeyError, IndexError, TypeError):
        return None

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "dev-secret-change-me")
    app.config["SESSION_COOKIE_NAME"] = SESSION_COOKIE_NAME
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    app.before_request(_before_request)
    app.teardown_appcontext(_teardown)

    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    ensure_db()
    
    # Initialize admin tables
    ensure_admin_tables()
    
    # Initialize GeoIP database
    download_geoip_database()
    
    # Initialize DDoS Protection
    ddos_protection = DDoSProtection(DATABASE)
    
    # Register admin blueprint
    app.register_blueprint(admin_bp)
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json()
        message = data.get("message")
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        response = get_chat_response(message)
        return jsonify({"response": response})

    @app.route("/")
    def landing():
        # If user is already logged in, redirect to dashboard
        if g.user:
            return redirect(url_for("index"))
        return render_template("landing.html")

    @app.route("/dashboard")
    @login_required
    def index():
        links = query_db(
            """
            SELECT id, code, primary_url, returning_url, cta_url,
                   behavior_rule, state, created_at
            FROM links
            WHERE user_id = ?
            ORDER BY created_at DESC
            """
            ,
            [g.user["id"]],
        )
        
        # Get link status distribution for chart
        link_stats = query_db(
            """
            SELECT state, COUNT(*) as count
            FROM links
            WHERE user_id = ?
            GROUP BY state
            """,
            [g.user["id"]],
        )
        
        # Get user's behavior rules for the create form
        behavior_rules = query_db(
            "SELECT * FROM behavior_rules WHERE user_id = ? ORDER BY is_default DESC, rule_name ASC",
            [g.user["id"]]
        )
        
        # Prepare chart data
        chart_data = {
            "linkStats": [{"state": row["state"], "count": row["count"]} for row in link_stats]
        }
        
        new_link = session.pop('new_link', None)
        
        # Get Tier Info
        # Convert Row to dict to use .get method
        user_dict = dict(g.user) if g.user else {}
        user_tier = user_dict.get("membership_tier", "free")
        tier_info = MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])
        link_count = len(links)
        
        return render_template("index.html", 
                               links=links, 
                               chart_data=chart_data, 
                               behavior_rules=behavior_rules, 
                               new_link=new_link,
                               tier_info=tier_info,
                               link_count=link_count,
                               user_tier=user_tier)



    @app.route("/create", methods=["POST"])
    @login_required
    def create():
        print("Create route called")  # Debug
        data = {k: (request.form.get(k) or "").strip() for k in request.form.keys()}
        print(f"Form data: {data}")  # Debug
        
        # Check Membership Limits
        # Convert Row to dict to use .get method
        user_dict = dict(g.user) if g.user else {}
        user_tier = user_dict.get("membership_tier", "free")
        # Handle case where tier might be null/empty in DB
        if not user_tier: user_tier = "free"
            
        tier_rules = MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])
        
        # Check link count
        current_links_count = query_db("SELECT COUNT(*) as count FROM links WHERE user_id = ?", [g.user["id"]], one=True)["count"]
        if current_links_count >= tier_rules["max_links"]:
            flash(f"Limit Reached: Your {tier_rules['name']} plan allows a maximum of {tier_rules['max_links']} links. Please upgrade to create more.", "warning")
            return redirect(url_for("index"))
        
        # Calculate expiration
        if tier_rules["validity_days"]:
            expires_at = (utcnow() + timedelta(days=tier_rules["validity_days"])).isoformat()
        else:
            expires_at = None

        
        # Enforce Feature Restrictions for Free Users
        requested_rule = data.get("behavior_rule", "standard")
        if user_tier == "free" and requested_rule in ["progression", "password_protected"]:
            # flash(f"The '{requested_rule.replace('_', ' ').title()}' feature is locked for Free users. Defaulted to Standard.", "warning")
            # Silently enforce or warn? User asked to "make this feature lock". 
            # Usually strict enforcement is better.
            data["behavior_rule"] = "standard"
            data["returning_url"] = ""
            data["cta_url"] = ""
            data["password"] = ""
            
        primary_url = data.get("primary_url")
        if not primary_url:
            flash("Primary URL is required", "danger")
            return redirect(url_for("index"))
        
        # Also ensure calculate expiration is already done above


        code = data.get("code") or generate_code()
        if query_db("SELECT id FROM links WHERE code = ?", [code], one=True):
            flash("Code already exists, please choose another", "danger")
            return redirect(url_for("index"))

        # Get behavior rule ID (optional)
        behavior_rule_id = data.get("behavior_rule_id")
        if behavior_rule_id:
            behavior_rule_id = int(behavior_rule_id)
        else:
            behavior_rule_id = None

        # Handle password protection
        password = data.get("password")
        password_hash = None
        if password:
            password_hash = generate_password_hash(password)

        now = utcnow()
        try:
            execute_db(
                """
                INSERT INTO links
                    (code, primary_url, returning_url, cta_url,
                     variant_a_url, variant_b_url,
                     behavior_rule, created_at, state, user_id, behavior_rule_id, password_hash, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    code,
                    primary_url,
                    data.get("returning_url") or primary_url,
                    data.get("cta_url") or primary_url,
                    data.get("variant_a_url") or primary_url,
                    data.get("variant_b_url") or primary_url,
                    data.get("behavior_rule") or "standard",
                    now.isoformat(),
                    "Active",
                    g.user["id"],
                    behavior_rule_id,
                    password_hash,
                    expires_at,
                ],
            )
        except sqlite3.IntegrityError as e:
            flash(f"Database Integrity Error: {str(e)}", "danger")
            return redirect(url_for("index"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return redirect(url_for("index"))
        flash(f"Link created with code {code}", "success")
        
        # Track user activity
        track_user_activity(g.user["id"], "create_link", f"Created link: {code} -> {primary_url}")
        
        # Store full link for the success box on dashboard
        base_url = request.host_url.rstrip('/')
        session['new_link'] = f"{base_url}/r/{code}"
        return redirect(url_for("index"))

    @app.route("/r/<code>")
    def redirect_link(code):
        link = query_db(
            """
            SELECT * FROM links WHERE code = ?
            """,
            [code],
            one=True,
        )
        if not link:
            abort(404)

        # Check if link is password protected - ALWAYS require password
        password_hash = get_link_password_hash(link)
        if password_hash:
            # Always redirect to password page for password-protected links
            return redirect(url_for("password_protected", code=code))

        # Check Expiration
        if link["expires_at"]:
            try:
                expires_at = datetime.fromisoformat(link["expires_at"])
                if utcnow() > expires_at:
                    flash("This link has expired.", "warning")
                    return redirect(url_for("landing"))
            except ValueError:
                pass # Invalid date format, ignore

        # DDoS Protection Check
        # Only applies if link owner has DDoS protection enabled (Elite Pro)
        link_owner = query_db("SELECT membership_tier, is_premium FROM users WHERE id = ?", [link["user_id"]], one=True)
        tier_name = link_owner["membership_tier"] if link_owner and link_owner["membership_tier"] else "free"
        
        # Use simple dictionary lookup for tier name to avoid errors
        tier_config = MEMBERSHIP_TIERS.get(tier_name, MEMBERSHIP_TIERS["free"])
        has_ddos_protection = tier_config["ddos_protection"]

        # Use robust IP detection
        ip_address = get_client_ip()
        
        # Calculate IP hash for privacy-preserving tracking
        ip_hash = hash_value(ip_address)

        if has_ddos_protection:
            # Check if link is under protection
            is_protected, protection_status = ddos_protection.is_link_protected(link["id"])
            if is_protected:
                if protection_status == 'disabled':
                    flash("This link has been temporarily disabled due to suspicious activity.", "warning")
                    return render_template("ddos_blocked.html", 
                                        message="Link Disabled", 
                                        description="This link has been automatically disabled due to detected DDoS attacks.")
                elif protection_status == 'temporary_disabled':
                    flash("This link is temporarily unavailable due to high traffic.", "warning")
                    return render_template("ddos_blocked.html", 
                                        message="Temporarily Unavailable", 
                                        description="This link is temporarily disabled due to unusual traffic patterns. Please try again later.")
                elif protection_status == 'captcha_required':
                    # In a real implementation, you'd show a captcha here
                    flash("Please verify you're human to continue.", "info")
                    return render_template("ddos_blocked.html", 
                                        message="Verification Required", 
                                        description="Please verify you're human to access this link.")
            
            # Rate limiting check (using real IP)
            rate_allowed, rate_status = ddos_protection.check_rate_limit(ip_address, link["id"])
            if not rate_allowed:
                if rate_status == 'rate_limited':
                    flash("Too many requests. Please slow down.", "warning")
                    return render_template("ddos_blocked.html", 
                                        message="Rate Limited", 
                                        description="You're making requests too quickly. Please wait a moment and try again.")
                elif rate_status == 'burst_attack':
                    flash("Suspicious activity detected.", "danger")
                    return render_template("ddos_blocked.html", 
                                        message="Blocked", 
                                        description="Suspicious activity detected from your connection.")
            
            # DDoS Detection
            is_ddos, ddos_reason, protection_level = ddos_protection.detect_ddos_attack(link["id"])
            if is_ddos:
                # Apply protection measures
                protection_action = ddos_protection.apply_protection(link["id"], protection_level)
                
                if protection_action in ['link_disabled', 'temporary_disabled']:
                    flash("This link has been automatically protected due to suspicious activity.", "warning")
                    return render_template("ddos_blocked.html", 
                                        message="Link Protected", 
                                        description="This link has been automatically protected due to detected attacks.")

        sess_id = ensure_session()
        user_agent = request.headers.get("User-Agent", "unknown")[:255]
        # Detect region and device
        region = detect_region(ip_address)
        device = detect_device(user_agent)
        
        # Get detailed location information
        location_info = get_detailed_location(ip_address)
        
        # Parse browser and OS from user agent (Grabify-like details)
        browser = parse_browser(user_agent)
        os_name = parse_os(user_agent)
        
        # Get ISP info (async-friendly, with timeout)
        isp_info = get_isp_info(ip_address)
        
        # Get referrer
        referrer = request.headers.get("Referer", "no referrer")[:500]  # Limit length
        
        now = utcnow()

        visits = query_db(
            """
            SELECT ts FROM visits
            WHERE link_id = ?
            ORDER BY ts DESC
            LIMIT 20
            """,
            [link["id"]],
        )
        
        # Get the link owner's default behavior rule
        behavior_rule = query_db(
            """
            SELECT * FROM behavior_rules 
            WHERE user_id = ? AND is_default = 1
            """,
            [link["user_id"]], one=True
        )
        
        behavior, per_session_count = classify_behavior(link["id"], sess_id, visits, now, behavior_rule)
        suspicious = detect_suspicious(visits, now)
        target_url = decide_target(link, behavior, per_session_count)

        execute_db(
            """
            INSERT INTO visits
                (link_id, session_id, ip_hash, user_agent, ts, behavior, is_suspicious, target_url, region, device, country, city, latitude, longitude, timezone, browser, os, isp, hostname, org, referrer, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                link["id"],
                sess_id,
                ip_hash,
                user_agent,
                now.isoformat(),
                behavior,
                1 if suspicious else 0,
                target_url,
                region,
                device,
                location_info['country'],
                location_info['city'],
                location_info['latitude'],
                location_info['longitude'],
                location_info['timezone'],
                browser,
                os_name,
                isp_info['isp'],
                isp_info['hostname'],
                isp_info['org'],
                referrer,
                ip_address,
            ],
        )

        new_state = evaluate_state(link["id"], now)
        if new_state != link["state"]:
            execute_db("UPDATE links SET state = ? WHERE id = ?", [new_state, link["id"]])

        if new_state == "Inactive":
            flash("Link became inactive due to decay or abnormal behavior", "warning")
            return redirect(url_for("index"))

        # Check if user wants to skip ads (direct parameter)
        skip_ads = request.args.get('direct', '').lower() == 'true'
        
        # Check if the link owner has ad-free experience (Elite Pro)
        link_owner_tier = link_owner["membership_tier"] if link_owner and link_owner["membership_tier"] else "free"
        link_owner_config = MEMBERSHIP_TIERS.get(link_owner_tier, MEMBERSHIP_TIERS["free"])
        has_ad_free_experience = link_owner_config["ad_free"]
        
        # Also check legacy premium status for backward compatibility
        is_premium_link = link_owner and link_owner["is_premium"]
        
        # Skip ads if: direct parameter, premium user, or Elite Pro user (ad-free experience)
        if skip_ads or is_premium_link or has_ad_free_experience:
            return redirect(target_url)
        
        # Redirect to ads page for Free and Elite users
        return redirect(url_for("show_ads", code=code, target=target_url))

    @app.route("/ads/<code>")
    def show_ads(code):
        target_url = request.args.get('target')
        if not target_url:
            flash("Invalid redirect target", "danger")
            return redirect(url_for("index"))
        
        link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
        if not link:
            flash("Link not found", "danger")
            return redirect(url_for("index"))
        
        # Get active ads that are either:
        # 1. From the link owner (original behavior)
        # 2. Assigned to the link owner by admin (new targeted ads)
        ads_data = query_db(
            """
            SELECT DISTINCT pa.*, u.username 
            FROM personalized_ads pa 
            JOIN users u ON pa.user_id = u.id 
            LEFT JOIN ad_display_assignments ada ON pa.id = ada.ad_id
            WHERE pa.is_active = 1 
            AND (
                pa.user_id = ? 
                OR ada.target_user_id = ?
            )
            ORDER BY pa.grid_position ASC, RANDOM()
            """,
            [link["user_id"], link["user_id"]]
        )
        
        # Organize ads by grid position with random selection
        ads_by_position = {1: None, 2: None, 3: None}
        
        # Separate ads by position
        position_ads = {1: [], 2: [], 3: []}
        for ad in ads_data:
            position = ad["grid_position"]
            if position in position_ads:
                position_ads[position].append(ad)
        
        # Randomly select one ad per position (1 large + 2 small)
        import random
        for position in [1, 2, 3]:
            if position_ads[position]:
                selected_ad = random.choice(position_ads[position])
                ads_by_position[position] = selected_ad
                
                # Track ad impression and revenue
                ad_type = "large" if position == 1 else "small"
                ip_address = get_client_ip()
                try:
                    revenue = track_ad_impression(link["id"], link["user_id"], ad_type, position, ip_address)
                    print(f"Ad impression tracked: {ad_type} ad, revenue: ${revenue:.2f}")
                except Exception as e:
                    print(f"Error tracking ad impression: {e}")
        
        # Count how many ads we have
        active_ads_count = sum(1 for ad in ads_by_position.values() if ad is not None)
            
        return render_template("ads.html", 
                             original_url=target_url, 
                             link=link, 
                             ads_by_position=ads_by_position,
                             active_ads_count=active_ads_count)

    @app.route("/p/<code>", methods=["GET", "POST"])
    def password_protected(code):
        try:
            link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
            if not link:
                abort(404)
            
            # If link is not password protected, redirect to normal flow
            password_hash = get_link_password_hash(link)
            if not password_hash:
                return redirect(url_for("redirect_link", code=code))
            
            if request.method == "POST":
                password = request.form.get("password", "").strip()
                
                if password and password_hash and check_password_hash(password_hash, password):
                    # Password is correct, redirect directly to the link destination
                    # No session storage - password required every time
                    flash("Password verified successfully!", "success")
                    
                    # Get the target URL based on behavior rules
                    sess_id = ensure_session()
                    user_agent = request.headers.get("User-Agent", "unknown")[:255]
                    ip_address = get_client_ip()
                    region = detect_region(ip_address)
                    device = detect_device(user_agent)
                    location_info = get_detailed_location(ip_address)
                    browser = parse_browser(user_agent)
                    os_name = parse_os(user_agent)
                    isp_info = get_isp_info(ip_address)
                    referrer = request.headers.get("Referer", "no referrer")[:500]
                    now = utcnow()
                    
                    # Get visits for behavior classification
                    visits = query_db(
                        """
                        SELECT ts FROM visits
                        WHERE link_id = ?
                        ORDER BY ts DESC
                        LIMIT 20
                        """,
                        [link["id"]],
                    )
                    
                    # Get the link owner's default behavior rule
                    behavior_rule = query_db(
                        """
                        SELECT * FROM behavior_rules 
                        WHERE user_id = ? AND is_default = 1
                        """,
                        [link["user_id"]], one=True
                    )
                    
                    behavior, per_session_count = classify_behavior(link["id"], sess_id, visits, now, behavior_rule)
                    suspicious = detect_suspicious(visits, now)
                    target_url = decide_target(link, behavior, per_session_count)
                    
                    # Log the visit
                    ip_hash = hash_value(ip_address)
                    execute_db(
                        """
                        INSERT INTO visits
                            (link_id, session_id, ip_hash, user_agent, ts, behavior, is_suspicious, target_url, region, device, country, city, latitude, longitude, timezone, browser, os, isp, hostname, org, referrer, ip_address)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            link["id"],
                            sess_id,
                            ip_hash,
                            user_agent,
                            now.isoformat(),
                            behavior,
                            1 if suspicious else 0,
                            target_url,
                            region,
                            device,
                            location_info['country'],
                            location_info['city'],
                            location_info['latitude'],
                            location_info['longitude'],
                            location_info['timezone'],
                            browser,
                            os_name,
                            isp_info['isp'],
                            isp_info['hostname'],
                            isp_info['org'],
                            referrer,
                            ip_address,
                        ],
                    )
                    
                    # Check if user wants to skip ads or if link owner has ad-free experience
                    skip_ads = request.args.get('direct', '').lower() == 'true'
                    link_owner = query_db("SELECT membership_tier, is_premium FROM users WHERE id = ?", [link["user_id"]], one=True)
                    
                    # Check for Elite Pro ad-free experience
                    link_owner_tier = link_owner["membership_tier"] if link_owner and link_owner["membership_tier"] else "free"
                    link_owner_config = MEMBERSHIP_TIERS.get(link_owner_tier, MEMBERSHIP_TIERS["free"])
                    has_ad_free_experience = link_owner_config["ad_free"]
                    
                    # Also check legacy premium status for backward compatibility
                    is_premium_link = link_owner and link_owner["is_premium"]
                    
                    # Skip ads if: direct parameter, premium user, or Elite Pro user (ad-free experience)
                    if skip_ads or is_premium_link or has_ad_free_experience:
                        return redirect(target_url)
                    else:
                        return redirect(url_for("show_ads", code=code, target=target_url))
                        
                else:
                    flash("Incorrect password. Please try again.", "danger")
            
            return render_template("password_protected.html", link=link, code=code)
            
        except Exception as e:
            print(f"Error in password_protected route: {e}")
            flash("An error occurred. Please try again.", "danger")
            return redirect(url_for("landing"))

    @app.route("/links/<code>")
    @login_required
    def analytics(code):
        try:
            link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
            if not link:
                abort(404)

            # Track analytics view activity
            track_user_activity(g.user["id"], "view_analytics", f"Viewed analytics for link: {code}")

            # Get the behavior rule for this link
            behavior_rule = None
            if link["behavior_rule_id"]:
                behavior_rule = query_db("SELECT * FROM behavior_rules WHERE id = ?", [link["behavior_rule_id"]], one=True)
            
            if not behavior_rule:
                # Get user's default behavior rule (fallback to link owner's rule or g.user's)
                user_id = link["user_id"] or (g.user["id"] if g.user else None)
                if user_id:
                    behavior_rule = query_db(
                        "SELECT * FROM behavior_rules WHERE user_id = ? AND is_default = 1",
                        [user_id], one=True
                    )

            visits = query_db(
                """
                SELECT ts, behavior, is_suspicious, region, device, country, city, latitude, longitude, timezone, browser, os, isp, hostname, org, referrer, user_agent, ip_hash, ip_address
                FROM visits
                WHERE link_id = ?
                ORDER BY ts DESC
                LIMIT 200
                """,
                [link["id"]],
            )

            # Recalculate behavior classifications with custom rules
            now = utcnow()
            
            # Initialize rules before loop to ensure they exist even if visits is empty
            if behavior_rule:
                returning_window_hours = behavior_rule["returning_window_hours"]
                interested_threshold = behavior_rule["interested_threshold"]
                engaged_threshold = behavior_rule["engaged_threshold"]
            else:
                returning_window_hours = RETURNING_WINDOW_HOURS
                interested_threshold = 2
                engaged_threshold = MULTI_CLICK_THRESHOLD

            recalculated_visits = []
            for visit in visits:
                visit_time = datetime.fromisoformat(visit["ts"])
                # Get session visits for this specific visit
                session_visits = query_db(
                    "SELECT ts FROM visits WHERE link_id = ? AND session_id = (SELECT session_id FROM visits WHERE id = (SELECT id FROM visits WHERE link_id = ? AND ts = ? LIMIT 1))",
                    [link["id"], link["id"], visit["ts"]]
                )
                
                # Count recent visits and session visits
                recent_visits = [v for v in session_visits if (now - datetime.fromisoformat(v["ts"])).total_seconds() < returning_window_hours * 3600]
                session_count = len(session_visits)
                
                # Reclassify
                if session_count >= engaged_threshold:
                    new_behavior = "Highly engaged"
                elif len(recent_visits) >= interested_threshold:
                    new_behavior = "Interested"
                else:
                    new_behavior = "Curious"
                
                # Create updated visit dict
                updated_visit = dict(visit)
                updated_visit["behavior"] = new_behavior
                recalculated_visits.append(updated_visit)

            # Calculate unique user behavior
            # Group visits by ip_hash to analyze user behavior
            user_behaviors = query_db(
                """
                SELECT 
                    ip_hash,
                    COUNT(*) as total_visits,
                    SUM(CASE WHEN ts >= datetime('now', '-' || ? || ' hours') THEN 1 ELSE 0 END) as recent_visits
                FROM visits 
                WHERE link_id = ? 
                GROUP BY ip_hash
                """,
                [returning_window_hours if behavior_rule else RETURNING_WINDOW_HOURS, link["id"]]
            )

            curious_users = 0
            interested_users = 0
            engaged_users = 0

            for user in user_behaviors:
                is_engaged = user["total_visits"] >= (behavior_rule["engaged_threshold"] if behavior_rule else MULTI_CLICK_THRESHOLD)
                is_interested = user["recent_visits"] >= (behavior_rule["interested_threshold"] if behavior_rule else 2)
                
                if is_engaged:
                    engaged_users += 1
                elif is_interested:
                    interested_users += 1
                else:
                    curious_users += 1

            # Calculate totals
            total_visits = len(recalculated_visits)
            # Use ip_hash for unique visitors instead of session_id for better persistence
            unique_visitors_query = query_db("SELECT DISTINCT ip_hash FROM visits WHERE link_id = ?", [link["id"]])
            unique_visitors = len(unique_visitors_query)
            suspicious_count = sum(1 for v in recalculated_visits if v["is_suspicious"])
            
            # Update totals dictionary with USER counts instead of VISIT counts
            curious_count = curious_users
            interested_count = interested_users
            engaged_count = engaged_users

            totals = {
                "total": total_visits,
                "unique_visitors": unique_visitors,
                "suspicious": suspicious_count,
                "curious": curious_count,
                "interested": interested_count,
                "engaged": engaged_count
            }
            
            # Get region distribution (grouped by continent)
            region_data_raw = query_db(
                """
                SELECT 
                    CASE 
                        WHEN country IS NOT NULL AND country != 'Unknown' THEN country
                        ELSE region 
                    END as location,
                    COUNT(DISTINCT ip_hash) as count
                FROM visits
                WHERE link_id = ? AND (country IS NOT NULL OR region IS NOT NULL)
                GROUP BY location
                ORDER BY count DESC
                """,
                [link["id"]],
            )
            
            # Group countries into continents
            continent_counts = {}
            for row in region_data_raw:
                continent = country_to_continent(row['location'])
                if continent in continent_counts:
                    continent_counts[continent] += row['count']
                else:
                    continent_counts[continent] = row['count']
            
            # Convert back to list format for template
            region_data = [{'location': continent, 'count': count} 
                          for continent, count in sorted(continent_counts.items(), 
                                                       key=lambda x: x[1], reverse=True)]

            # Get city distribution
            city_data = query_db(
                """
                SELECT city, country, COUNT(DISTINCT ip_hash) as count 
                FROM visits 
                WHERE link_id = ? AND city IS NOT NULL AND city != 'Unknown'
                GROUP BY city, country
                ORDER BY count DESC
                LIMIT 20
                """, 
                [link["id"]]
            )

            # Get ISP distribution
            isp_counts_raw = query_db(
                """
                SELECT isp, COUNT(DISTINCT ip_hash) as count
                FROM visits
                WHERE link_id = ?
                GROUP BY isp
                """,
                [link["id"]]
            )
            
            normalized_isp_counts = {}
            for row in isp_counts_raw:
                provider = normalize_isp(row['isp'])
                # Aggregate counts for normalized names
                normalized_isp_counts[provider] = normalized_isp_counts.get(provider, 0) + row['count']
            
            # Convert to list of dicts for template, sorted by count
            isp_data = [
                {'provider': k, 'count': v} 
                for k, v in sorted(normalized_isp_counts.items(), key=lambda x: x[1], reverse=True)
            ][:10]

            # Get device distribution
            device_data = query_db(
                """
                SELECT device, COUNT(DISTINCT ip_hash) as count
                FROM visits
                WHERE link_id = ? AND device IS NOT NULL
                GROUP BY device
                """,
                [link["id"]],
            )

            # Get daily and hourly engagement trends using visitor's local timezone
            visits_raw = query_db(
                "SELECT ts, timezone FROM visits WHERE link_id = ?",
                [link["id"]]
            )
            
            from collections import Counter
            local_days = []
            local_hours = []
            
            for row in visits_raw:
                try:
                    dt_utc = datetime.fromisoformat(row["ts"]).replace(tzinfo=timezone.utc)
                    tz_name = row["timezone"] or "UTC"
                    try:
                        visitor_tz = ZoneInfo(tz_name)
                    except:
                        visitor_tz = timezone.utc
                    
                    dt_local = dt_utc.astimezone(visitor_tz)
                    local_days.append(dt_local.weekday())
                    local_hours.append(dt_local.hour)
                except: pass
            
            # Process daily distribution (Mon=0...Sun=6)
            day_names_sun = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            day_counts = Counter(local_days)
            daily_data = []
            # Map Python's 0=Mon...6=Sun to display 0=Sun...6=Sat
            ordered_indices = [6, 0, 1, 2, 3, 4, 5]
            for i, idx in enumerate(ordered_indices):
                daily_data.append({"day": day_names_sun[i], "count": day_counts.get(idx, 0)})
            
            # Process hourly distribution (0-23)
            hour_counts = Counter(local_hours)
            hourly_data = []
            for h in range(24):
                hourly_data.append({"hour": h, "count": hour_counts.get(h, 0)})

            # Calculate weekend vs weekday insight
            weekday_total = sum(day_counts.get(i, 0) for i in range(5)) # Mon-Fri
            weekend_total = sum(day_counts.get(i, 0) for i in range(5, 7)) # Sat-Sun
            
            weekend_insight = ""
            if weekday_total > 0 and weekend_total > 0:
                weekend_percentage = ((weekend_total - weekday_total) / weekday_total) * 100
                if weekend_percentage > 20:
                    weekend_insight = f"Weekend traffic shows {abs(weekend_percentage):.0f}% increase compared to weekdays, suggesting consumer-focused audience behavior."
                elif weekend_percentage < -20:
                    weekend_insight = f"Weekday traffic shows {abs(weekend_percentage):.0f}% increase compared to weekends, suggesting business-focused audience behavior."
                else:
                    weekend_insight = "Traffic is fairly consistent between weekdays and weekends."
            else:
                weekend_insight = "Gathering engagement pattern data..."

            trust = trust_score(link["id"])
            attention = attention_decay(list(reversed(recalculated_visits)))

            # Prepare payload for frontend
            def safe_get(row, key):
                return row[key] if row and row[key] is not None else 0

            analytics_payload = {
                "debug_version": "v1.0.1_isp_restored",
                "intent": {
                    "curious": curious_count,
                    "interested": interested_count,
                    "engaged": engaged_count
                },
                "quality": {
                    "human": total_visits - suspicious_count,
                    "suspicious": suspicious_count
                },
                "attention": attention,
                "hourly": hourly_data,  # Already list of dicts
                "daily": daily_data,
                "region": region_data,  # Already list of dicts
                "cities": [dict(row) for row in city_data],  # SQLite Row objects
                "device": [dict(row) for row in device_data],  # SQLite Row objects
                "isp": [dict(row) for row in isp_data],
                "weekend_insight": weekend_insight
            }
            
            # Prepare detailed visitor list for Grabify-like log
            detailed_visitors = []
            for visit in recalculated_visits[:50]:  # Limit to 50 most recent
                # Use real IP address if available, otherwise fallback to hashed IP (masked)
                ip_display = visit.get('ip_address')
                if not ip_display or ip_display == 'unknown':
                     ip_display = f"hashed: {visit.get('ip_hash', '')[-8:]}" if visit.get('ip_hash') else 'N/A'

                visitor = {
                    'timestamp': visit.get('ts', ''),
                    'ip_address': ip_display,
                    'country': visit.get('country', 'Unknown'),
                    'city': visit.get('city', 'Unknown'),
                    'region': visit.get('region', 'Unknown'),
                    'browser': visit.get('browser', 'Unknown'),
                    'os': visit.get('os', 'Unknown'),
                    'device': visit.get('device', 'Unknown'),
                    'user_agent': visit.get('user_agent', 'Unknown'),
                    'referrer': visit.get('referrer', 'no referrer'),
                    'isp': visit.get('isp', 'Unknown'),
                    'hostname': visit.get('hostname', 'Unknown'),
                    'org': visit.get('org', 'Unknown'),
                    'timezone': visit.get('timezone', 'Unknown'),
                    'latitude': visit.get('latitude'),
                    'longitude': visit.get('longitude'),
                    'behavior': visit.get('behavior', 'Unknown'),
                    'is_suspicious': visit.get('is_suspicious', False)
                }
                detailed_visitors.append(visitor)

            return render_template(
                "analytics.html",
                link=link,
                visits=recalculated_visits,
                totals=totals,
                trust=trust,
                attention=attention,
                region_data=region_data,
                city_data=city_data,
                device_data=device_data,
                hourly_data=hourly_data,
                daily_data=daily_data,
                weekend_insight=weekend_insight,
                analytics_payload=analytics_payload,
                behavior_rule=behavior_rule,
                detailed_visitors=detailed_visitors,
                isp_data=isp_data,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash(f"Error loading analytics: {str(e)}", "danger")
            return redirect(url_for("index"))

    @app.route("/debug-analytics/<code>")
    def debug_analytics(code):
        """Debug route to check analytics data"""
        link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
        if not link:
            return f"Link {code} not found", 404
        
        # Get daily data and timestamps for hourly distribution (same logic as analytics route)
        visits_raw = query_db("SELECT ts, timezone FROM visits WHERE link_id = ?", [link["id"]])
        
        from collections import Counter
        local_days = []
        local_hours = []
        
        for row in visits_raw:
            try:
                dt_utc = datetime.fromisoformat(row["ts"]).replace(tzinfo=timezone.utc)
                
                # Get visitor's timezone
                tz_name = row["timezone"] or "UTC"
                try:
                    visitor_tz = ZoneInfo(tz_name)
                except:
                    visitor_tz = timezone.utc
                
                dt_local = dt_utc.astimezone(visitor_tz)
                local_days.append(dt_local.weekday())
                local_hours.append(dt_local.hour)
            except Exception as e:
                print(f"Error processing debug timestamp: {e}")
                pass

        day_counts = Counter(local_days)
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily_data = []
        
        for i, day_name in enumerate(day_names):
            count = day_counts.get(i, 0)
            daily_data.append({"day": day_name, "count": count})
        
        hour_counts = Counter(local_hours)
        final_hourly_data = [{"hour": h, "count": hour_counts.get(h, 0)} for h in range(24)]
        
        # Create simplified analytics payload
        analytics_payload = {
            "daily": daily_data,
            "intent": {"curious": 0, "interested": 0, "engaged": 0},
            "quality": {"human": 0, "suspicious": 0},
            "attention": [],
            "hourly": final_hourly_data,
            "region": [],
            "device": []
        }
        
        return render_template(
            "debug_analytics.html",
            link=link,
            daily_data=daily_data,
            analytics_payload=analytics_payload
        )

    @app.route("/links/<code_id>/csv")
    def export_csv(code_id):
        link = query_db("SELECT * FROM links WHERE code = ?", [code_id], one=True)

        if not link:
            return "Link not found", 404

        # Reuse aggregation logic (simplified for export)
        # Note: In a production app, we would refactor this common logic into helper functions.
        # For now, we will query fresh data to ensure accuracy.
        
        # 1. Totals & Intent
        totals = query_db("""
            SELECT 
                COUNT(*) as total,
                SUM(is_suspicious) as suspicious,
                SUM(CASE WHEN behavior = 'Curious' THEN 1 ELSE 0 END) as curious,
                SUM(CASE WHEN behavior = 'Interested' THEN 1 ELSE 0 END) as interested,
                SUM(CASE WHEN behavior = 'Highly engaged' THEN 1 ELSE 0 END) as engaged
            FROM visits WHERE link_id = ?
        """, [link["id"]], one=True)
        
        # 2. Region (using continent data for better grouping)
        region_data_raw = query_db(
            """
            SELECT 
                CASE 
                    WHEN country IS NOT NULL AND country != 'Unknown' THEN country
                    ELSE region 
                END as location,
                COUNT(*) as count
            FROM visits 
            WHERE link_id = ? AND (country IS NOT NULL OR region IS NOT NULL)
            GROUP BY location
            ORDER BY count DESC
            """, 
            [link["id"]]
        )
        
        # Group countries into continents for CSV
        continent_counts = {}
        for row in region_data_raw:
            continent = country_to_continent(row['location'])
            if continent in continent_counts:
                continent_counts[continent] += row['count']
            else:
                continent_counts[continent] = row['count']
        
        region_data = [{'location': continent, 'count': count} 
                      for continent, count in sorted(continent_counts.items(), 
                                                   key=lambda x: x[1], reverse=True)]

        # 2b. City data
        city_data = query_db(
            """
            SELECT city, country, COUNT(*) as count 
            FROM visits 
            WHERE link_id = ? AND city IS NOT NULL AND city != 'Unknown'
            GROUP BY city, country
            ORDER BY count DESC
            """, 
            [link["id"]]
        )
        
        # 3. Device
        device_data = query_db("SELECT device, COUNT(*) as count FROM visits WHERE link_id = ? GROUP BY device", [link["id"]])
        
        # 4. Hourly distribution using visitor's local timezone
        hourly_raw = query_db("SELECT ts, timezone FROM visits WHERE link_id = ?", [link["id"]])
        import datetime
        from zoneinfo import ZoneInfo
        from collections import Counter
        local_hours = []
        for row in hourly_raw:
            try:
                dt_utc = datetime.datetime.fromisoformat(row["ts"]).replace(tzinfo=datetime.timezone.utc)
                tz_name = row["timezone"] or "UTC"
                try:
                    visitor_tz = ZoneInfo(tz_name)
                except:
                    visitor_tz = datetime.timezone.utc
                
                dt_local = dt_utc.astimezone(visitor_tz)
                local_hours.append(dt_local.hour)
            except: pass
        hour_counts = Counter(local_hours)

        # Build CSV
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Category', 'Key', 'Value'])
        
        # Helper to treat None as 0
        val = lambda x: x if x is not None else 0

        # Summary
        if totals:
            total_clicks = val(totals['total'])
            suspicious_count = val(totals['suspicious'])
            writer.writerow(['Summary', 'Total Clicks', total_clicks])
            writer.writerow(['Summary', 'Human Traffic', total_clicks - suspicious_count])
            writer.writerow(['Summary', 'Suspicious', suspicious_count])
        else:
            # Should not happen given COUNT(*), but safety first
            writer.writerow(['Summary', 'Total Clicks', 0])
            writer.writerow(['Summary', 'Human Traffic', 0])
            writer.writerow(['Summary', 'Suspicious', 0])
        
        # Region
        for r in region_data:
            writer.writerow(['Continent', r['location'], r['count']])
        
        # Cities
        for c in city_data:
            city_country = f"{c['city']}, {c['country']}" if c['country'] else c['city']
            writer.writerow(['City', city_country, c['count']])
            
        # Device
        for d in device_data:
            writer.writerow(['Device', d['device'], d['count']])
            
        # Hourly
        for h, c in hour_counts.items():
            writer.writerow(['Hourly', f"{h}:00", c])
        
        # Daily (if available)
        if 'daily_data' in locals():
            for day_info in daily_data:
                writer.writerow(['Daily Pattern', day_info['day'], day_info['count']])

        from flask import Response
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=analytics_{code_id}.csv"}
        )

    @app.route("/links/<code_id>/export-excel")
    @login_required
    def export_link_analytics_excel(code_id):
        try:
            link = query_db("SELECT * FROM links WHERE code = ?", [code_id], one=True)
            if not link:
                return "Link not found", 404
            
            # Use the same unique visitor logic as the analytics route
            visits = query_db(
                """
                SELECT ts, ip_address, country, city, browser, isp, hostname, org, timezone, device, behavior, is_suspicious, latitude, longitude, user_agent, referrer
                FROM visits
                WHERE link_id = ?
                ORDER BY ts DESC
                """,
                [link["id"]],
            )
            
            # Create Excel content using HTML table format
            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 10pt; }}
                    th {{ background-color: #f2f2f2; font-weight: bold; }}
                    .center {{ text-align: center; }}
                    .header {{ background-color: #333; color: white; padding: 15px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Detailed Visitor Log - {link['code']}</h2>
                    <p>Original URL: {link['primary_url']}</p>
                    <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>Total Records: {len(visits)}</p>
                </div>
                <table>
                    <tr>
                        <th>Srno</th>
                        <th>Time (UTC)</th>
                        <th>IP Address</th>
                        <th>Country</th>
                        <th>City</th>
                        <th>Browser</th>
                        <th>ISP</th>
                        <th>Coordinate</th>
                    </tr>
            """
            
            # Add data rows
            for i, v in enumerate(visits, 1):
                # Normalize ISP for the export as well
                provider = normalize_isp(v['isp'])
                
                # Format coordinate
                coordinate = f"{v['latitude']}, {v['longitude']}" if v['latitude'] and v['longitude'] else "N/A"
                
                html_content += f"""
                    <tr>
                        <td class="center">{i}</td>
                        <td>{str(v['ts'])[:19]}</td>
                        <td>{str(v['ip_address'])}</td>
                        <td>{str(v['country'])}</td>
                        <td>{str(v['city'])}</td>
                        <td>{str(v['browser'])}</td>
                        <td>{provider}</td>
                        <td>{coordinate}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </body>
            </html>
            """
            
            from flask import Response
            return Response(
                html_content,
                mimetype="application/vnd.ms-excel",
                headers={
                    "Content-disposition": f"attachment; filename=visitor_log_{code_id}.xls",
                    "Content-Type": "application/vnd.ms-excel; charset=utf-8"
                }
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Export Error: {str(e)}", 500

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = (request.form.get("password") or "").strip()
            confirm_password = (request.form.get("confirm_password") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            terms_accepted = bool(request.form.get("terms"))

            # Validation errors list
            errors = []

            # Required fields validation
            if not username:
                errors.append("Username is required")
            if not password:
                errors.append("Password is required")
            if not confirm_password:
                errors.append("Password confirmation is required")
            if not email:
                errors.append("Email is required")
            if not terms_accepted:
                errors.append("You must accept the terms and conditions")

            # Username validation
            if username:
                # Convert to lowercase for storage but validate original case
                username_lower = username.lower()
                if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
                    errors.append("Username must be 3-20 characters and contain only letters, numbers, and underscores")
                elif query_db("SELECT id FROM users WHERE username = ?", [username_lower], one=True):
                    errors.append("Username already exists")

            # Email validation
            if email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, email):
                    errors.append("Please enter a valid email address")
                elif query_db("SELECT id FROM users WHERE email = ?", [email], one=True):
                    errors.append("Email address already registered")

            # Password validation
            if password:
                if len(password) < 8:
                    errors.append("Password must be at least 8 characters long")
                if not re.search(r'[A-Z]', password):
                    errors.append("Password must contain at least one uppercase letter")
                if not re.search(r'[a-z]', password):
                    errors.append("Password must contain at least one lowercase letter")
                if not re.search(r'\d', password):
                    errors.append("Password must contain at least one number")
                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    errors.append("Password must contain at least one special character")

            # Password confirmation validation
            if password and confirm_password and password != confirm_password:
                errors.append("Passwords do not match")

            # If there are validation errors, show them and return to form
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("signup.html")

            # All validations passed, create user
            try:
                execute_db(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    [username_lower, email, generate_password_hash(password)],
                )
                
                # Send Welcome Email
                send_email(
                    to_email=email,
                    subject="Welcome to Smart Link Intelligence!",
                    body=f"Hi {username},\n\nWelcome to Smart Link Intelligence! Your account has been created successfully.\n\nYou can now start creating smart links and tracking their analytics.\n\nBest regards,\nThe Smart Link Team"
                )
                
                # Log the user in automatically
                user = query_db("SELECT id FROM users WHERE username = ?", [username_lower], one=True)
                session[USER_SESSION_KEY] = user["id"]
                
                # Track user registration activity
                track_user_activity(user["id"], "register", f"New user registered: {username}")
                
                flash("🎉 Account created successfully! Welcome to Smart Link Intelligence.", "success")
                return redirect(url_for("index"))
                
            except sqlite3.IntegrityError as e:
                # Handle database constraint violations
                if "username" in str(e).lower():
                    flash("Username already exists", "danger")
                elif "email" in str(e).lower():
                    flash("Email address already registered", "danger")
                else:
                    flash("An account with these details already exists", "danger")
                return render_template("signup.html")
            except Exception as e:
                flash("An error occurred while creating your account. Please try again.", "danger")
                return render_template("signup.html")

        return render_template("signup.html")

        return render_template("signup.html")

    @app.route("/check-availability", methods=["POST"])
    def check_availability():
        """AJAX endpoint to check username/email availability during signup"""
        data = request.get_json()
        field_type = data.get("type")  # "username" or "email"
        value = data.get("value", "").strip()
        
        if not value:
            return jsonify({"available": False, "message": "Value is required"})
        
        if field_type == "username":
            value = value.lower()
            if not re.match(r'^[a-zA-Z0-9_]{3,20}$', value):
                return jsonify({"available": False, "message": "Invalid username format"})
            
            exists = query_db("SELECT id FROM users WHERE username = ?", [value], one=True)
            if exists:
                return jsonify({"available": False, "message": "Username already taken"})
            else:
                return jsonify({"available": True, "message": "Username available"})
                
        elif field_type == "email":
            value = value.lower()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return jsonify({"available": False, "message": "Invalid email format"})
            
            exists = query_db("SELECT id FROM users WHERE email = ?", [value], one=True)
            if exists:
                return jsonify({"available": False, "message": "Email already registered"})
            else:
                return jsonify({"available": True, "message": "Email available"})
        
        return jsonify({"available": False, "message": "Invalid request"})

    @app.route("/behavior-rules")
    @login_required
    def behavior_rules():
        """Manage user's behavior rules"""
        # Get user's existing behavior rules
        user_rules = query_db(
            "SELECT * FROM behavior_rules WHERE user_id = ? ORDER BY created_at DESC",
            [g.user["id"]]
        )
        
        # Get default rule if no custom rules exist
        if not user_rules:
            # Create default rule for new users
            execute_db(
                """
                INSERT INTO behavior_rules (user_id, rule_name, returning_window_hours, interested_threshold, engaged_threshold, is_default)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [g.user["id"], "Default Rule", 48, 2, 3, 1]
            )
            user_rules = query_db(
                "SELECT * FROM behavior_rules WHERE user_id = ? ORDER BY created_at DESC",
                [g.user["id"]]
            )
        
        return render_template("behavior_rules.html", user_rules=user_rules)

    @app.route("/behavior-rules/create", methods=["POST"])
    @login_required
    def create_behavior_rule():
        """Create a new behavior rule"""
        rule_name = request.form.get("rule_name", "").strip()
        returning_window_hours = int(request.form.get("returning_window_hours", 48))
        interested_threshold = int(request.form.get("interested_threshold", 2))
        engaged_threshold = int(request.form.get("engaged_threshold", 3))
        
        # Validation
        if not rule_name:
            flash("Rule name is required", "danger")
            return redirect(url_for("behavior_rules"))
        
        if returning_window_hours < 1 or returning_window_hours > 168:  # 1 hour to 1 week
            flash("Returning window must be between 1 and 168 hours", "danger")
            return redirect(url_for("behavior_rules"))
        
        if interested_threshold < 1 or interested_threshold > 10:
            flash("Interested threshold must be between 1 and 10", "danger")
            return redirect(url_for("behavior_rules"))
        
        if engaged_threshold < 1 or engaged_threshold > 20:
            flash("Engaged threshold must be between 1 and 20", "danger")
            return redirect(url_for("behavior_rules"))
        
        if engaged_threshold <= interested_threshold:
            flash("Engaged threshold must be higher than interested threshold", "danger")
            return redirect(url_for("behavior_rules"))
        
        # Create the rule
        execute_db(
            """
            INSERT INTO behavior_rules (user_id, rule_name, returning_window_hours, interested_threshold, engaged_threshold)
            VALUES (?, ?, ?, ?, ?)
            """,
            [g.user["id"], rule_name, returning_window_hours, interested_threshold, engaged_threshold]
        )
        
        flash(f"Behavior rule '{rule_name}' created successfully!", "success")
        return redirect(url_for("behavior_rules"))

    @app.route("/behavior-rules/delete/<int:rule_id>", methods=["POST"])
    @login_required
    def delete_behavior_rule(rule_id):
        """Delete a behavior rule"""
        # Check if rule belongs to current user
        rule = query_db(
            "SELECT * FROM behavior_rules WHERE id = ? AND user_id = ?",
            [rule_id, g.user["id"]], one=True
        )
        
        if not rule:
            flash("Rule not found", "danger")
            return redirect(url_for("behavior_rules"))
        
        if rule["is_default"]:
            flash("Cannot delete the default rule", "danger")
            return redirect(url_for("behavior_rules"))
        
        execute_db("DELETE FROM behavior_rules WHERE id = ?", [rule_id])
        flash("Behavior rule deleted successfully", "success")
        return redirect(url_for("behavior_rules"))

    @app.route("/behavior-rules/set-default/<int:rule_id>", methods=["POST"])
    @login_required
    def set_default_behavior_rule(rule_id):
        """Set a rule as default"""
        # Check if rule belongs to current user
        rule = query_db(
            "SELECT * FROM behavior_rules WHERE id = ? AND user_id = ?",
            [rule_id, g.user["id"]], one=True
        )
        
        if not rule:
            flash("Rule not found", "danger")
            return redirect(url_for("behavior_rules"))
        
        # Remove default from all other rules
        execute_db("UPDATE behavior_rules SET is_default = 0 WHERE user_id = ?", [g.user["id"]])
        
        # Set this rule as default
        execute_db("UPDATE behavior_rules SET is_default = 1 WHERE id = ?", [rule_id])
        
        flash(f"'{rule['rule_name']}' is now your default behavior rule", "success")
        return redirect(url_for("behavior_rules"))

    @app.route("/ddos-protection")
    @login_required
    def ddos_protection_dashboard():
        """DDoS Protection Dashboard"""
        # Check Membership
        # Convert Row to dict to use .get method
        user_dict = dict(g.user) if g.user else {}
        user_tier = user_dict.get("membership_tier", "free")
        if not user_tier: user_tier = "free"
        
        if not MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])["ddos_protection"]:
            flash("DDoS Protection is exclusive to Elite Pro members. Please upgrade to access this feature.", "warning")
            return redirect(url_for("index"))
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
        
        return render_template("ddos_protection.html", 
                             links=links_with_protection, 
                             recent_events=recent_events)

    @app.route("/ddos-protection/recover/<int:link_id>", methods=["POST"])
    @login_required
    def recover_link(link_id):
        """Manually recover a DDoS-protected link"""
        # Check if link belongs to current user
        link = query_db(
            "SELECT * FROM links WHERE id = ? AND user_id = ?",
            [link_id, g.user["id"]], one=True
        )
        
        if not link:
            flash("Link not found", "danger")
            return redirect(url_for("ddos_protection_dashboard"))
        
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
        
        flash(f"Link '{link['code']}' has been recovered and is now active", "success")
        return redirect(url_for("ddos_protection_dashboard"))

    @app.route("/ddos-protection/stats/<int:link_id>")
    @login_required
    def ddos_link_stats(link_id):
        """Get detailed DDoS statistics for a specific link"""
        # Check if link belongs to current user
        link = query_db(
            "SELECT * FROM links WHERE id = ? AND user_id = ?",
            [link_id, g.user["id"]], one=True
        )
        
        if not link:
            abort(404)
        
        # Get protection statistics
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
        
        return render_template("ddos_link_stats.html", 
                             link=link, 
                             stats=stats, 
                             events=events)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username_or_email = (request.form.get("username") or "").strip()
            password = (request.form.get("password") or "").strip()
            remember_me = request.form.get("remember_me") == "on"

            # Validation errors
            errors = []

            # Required fields validation
            if not username_or_email:
                errors.append("Username or email is required")
            if not password:
                errors.append("Password is required")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("login.html")

            # Check for admin login first
            if username_or_email.lower() == "admin":
                # Redirect to admin login page
                flash("Please use the admin login page", "info")
                return redirect(url_for("admin.admin_login"))

            # Try to find user by username or email
            user = None
            
            # Check if input looks like an email
            if '@' in username_or_email:
                # Login with email
                email = username_or_email.lower()
                user = query_db("SELECT * FROM users WHERE email = ?", [email], one=True)
                if not user:
                    flash("No account found with this email address", "danger")
                    return render_template("login.html")
            else:
                # Login with username
                username = username_or_email.lower()
                user = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
                if not user:
                    flash("No account found with this username", "danger")
                    return render_template("login.html")

            # Validate password
            if not check_password_hash(user["password_hash"], password):
                flash("Incorrect password", "danger")
                return render_template("login.html")

            # Login successful
            session[USER_SESSION_KEY] = user["id"]
            
            # Track user login activity
            track_user_activity(user["id"], "login", f"User logged in: {user['username']}")
            
            # Handle remember me functionality (extend session)
            if remember_me:
                session.permanent = True
                # Set session to last 30 days if remember me is checked
                from datetime import timedelta
                app.permanent_session_lifetime = timedelta(days=30)
            
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("index"))
            
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop(USER_SESSION_KEY, None)
        flash("Logged out", "info")
        return redirect(url_for("login"))

    @app.route("/documentation")
    @login_required
    def documentation():
        return render_template("documentation.html")

    @app.route("/upgrade")
    @login_required
    def upgrade():
        return render_template("upgrade.html")

    @app.route("/upgrade/process", methods=["POST"])
    @login_required
    def process_upgrade():
        # In a real app, you'd integrate with a payment processor like Stripe
        # For demo purposes, we'll just upgrade the user
        from datetime import datetime, timedelta
        
        target_tier = request.form.get("plan", "elite")
        
        # Validate tier
        if target_tier not in ["elite", "elite_pro"]:
            target_tier = "elite"
            
        # Set premium expiry (Demo: 30 days)
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        execute_db(
            "UPDATE users SET is_premium = 1, membership_tier = ?, premium_expires_at = ? WHERE id = ?",
            [target_tier, expires_at, g.user["id"]]
        )
        
        tier_name = MEMBERSHIP_TIERS[target_tier]["name"]
        flash(f"🎉 Upgraded to {tier_name}! Enjoy your new features.", "success")
        return redirect(url_for("index"))

    @app.route("/create-ad")
    @login_required
    def create_ad():
        # Check Membership
        # Convert Row to dict to use .get method
        user_dict = dict(g.user) if g.user else {}
        user_tier = user_dict.get("membership_tier", "free")
        if not user_tier: user_tier = "free"
        
        if not MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])["custom_ads"]:
            flash("Custom Ads are exclusive to Elite Pro members. Please upgrade to access this feature.", "warning")
            return redirect(url_for("index"))

        # Get user's existing ads
        user_ads = query_db(
            "SELECT * FROM personalized_ads WHERE user_id = ? ORDER BY created_at DESC",
            [g.user["id"]]
        )
        
        # Get ad statistics
        total_ads = len(user_ads)
        active_ads = len([ad for ad in user_ads if ad["is_active"]])
        
        return render_template("create_ad.html", user_ads=user_ads, total_ads=total_ads, active_ads=active_ads)

    @app.route("/create-ad/submit", methods=["POST"])
    @login_required
    def submit_ad():
        # Check Membership
        # Convert Row to dict to use .get method
        user_dict = dict(g.user) if g.user else {}
        user_tier = user_dict.get("membership_tier", "free")
        if not user_tier: user_tier = "free"
        
        if not MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])["custom_ads"]:
            flash("Custom Ads are exclusive to Elite Pro members.", "danger")
            return redirect(url_for("index"))

        data = {k: (request.form.get(k) or "").strip() for k in request.form.keys()}
        
        ad_type = data.get("ad_type", "custom")
        title = data.get("title")
        description = data.get("description")
        cta_text = data.get("cta_text")
        cta_url = data.get("cta_url")
        grid_position = int(data.get("grid_position", "1"))
        
        if not all([title, description, cta_text, cta_url]):
            flash("Title, description, CTA text, and URL are required", "danger")
            return redirect(url_for("create_ad"))
        
        # Validate URL
        if not cta_url.startswith(('http://', 'https://')):
            flash("Please enter a valid URL starting with http:// or https://", "danger")
            return redirect(url_for("create_ad"))
        
        # Validate grid position
        if grid_position not in [1, 2, 3]:
            flash("Invalid grid position selected", "danger")
            return redirect(url_for("create_ad"))
        
        image_filename = None
        background_color = "#667eea"
        text_color = "#ffffff"
        icon = "🚀"
        
        if ad_type == "image":
            # Handle image upload
            if 'ad_image' not in request.files:
                flash("Please select an image file", "danger")
                return redirect(url_for("create_ad"))
            
            file = request.files['ad_image']
            if file.filename == '':
                flash("Please select an image file", "danger")
                return redirect(url_for("create_ad"))
            
            # Process and save image with proper resizing/cropping
            image_filename = process_and_save_image(file, g.user["id"])
            if not image_filename:
                flash("Error processing image. Please try a different image.", "danger")
                return redirect(url_for("create_ad"))
        else:
            # Handle custom ad
            background_color = data.get("background_color", "#667eea")
            text_color = data.get("text_color", "#ffffff")
            icon = data.get("icon", "🚀")
        
        execute_db(
            """
            INSERT INTO personalized_ads 
            (user_id, title, description, cta_text, cta_url, background_color, text_color, icon, grid_position, ad_type, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [g.user["id"], title, description, cta_text, cta_url, background_color, text_color, icon, grid_position, ad_type, image_filename]
        )
        
        flash("🎉 Your personalized ad has been created successfully!", "success")
        return redirect(url_for("create_ad"))

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route("/toggle-ad/<int:ad_id>", methods=["POST"])
    @login_required
    def toggle_ad(ad_id):
        # Check if ad belongs to current user
        ad = query_db(
            "SELECT * FROM personalized_ads WHERE id = ? AND user_id = ?",
            [ad_id, g.user["id"]], one=True
        )
        
        if not ad:
            flash("Ad not found", "danger")
            return redirect(url_for("create_ad"))
        
        new_status = 0 if ad["is_active"] else 1
        execute_db(
            "UPDATE personalized_ads SET is_active = ? WHERE id = ?",
            [new_status, ad_id]
        )
        
        status_text = "activated" if new_status else "deactivated"
        flash(f"Ad has been {status_text}", "success")
        return redirect(url_for("create_ad"))

    @app.route("/delete-ad/<int:ad_id>", methods=["POST"])
    @login_required
    def delete_ad(ad_id):
        # Check if ad belongs to current user
        ad = query_db(
            "SELECT * FROM personalized_ads WHERE id = ? AND user_id = ?",
            [ad_id, g.user["id"]], one=True
        )
        
        if not ad:
            flash("Ad not found", "danger")
            return redirect(url_for("create_ad"))
        
        execute_db("DELETE FROM personalized_ads WHERE id = ?", [ad_id])
        flash("Ad has been deleted", "success")
        return redirect(url_for("create_ad"))

    @app.route("/settings")
    @login_required
    def settings():
        # Get user statistics
        total_links = query_db("SELECT COUNT(*) as count FROM links WHERE user_id = ?", [g.user["id"]], one=True)["count"]
        total_clicks = query_db("SELECT COUNT(*) as count FROM visits v JOIN links l ON v.link_id = l.id WHERE l.user_id = ?", [g.user["id"]], one=True)["count"]
        
        return render_template("settings.html", total_links=total_links, total_clicks=total_clicks)

    @app.route("/settings/update", methods=["POST"])
    @login_required
    def update_settings():
        email = request.form.get("email", "").strip()
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        
        # Update email if provided
        if email:
            execute_db("UPDATE users SET email = ? WHERE id = ?", [email, g.user["id"]])
        
        # Update password if provided
        if current_password and new_password:
            if check_password_hash(g.user["password_hash"], current_password):
                new_hash = generate_password_hash(new_password)
                execute_db("UPDATE users SET password_hash = ? WHERE id = ?", [new_hash, g.user["id"]])
                flash("Password updated successfully", "success")
            else:
                flash("Current password is incorrect", "danger")
                return redirect(url_for("settings"))
        
        flash("Settings updated successfully", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/preferences", methods=["POST"])
    @login_required
    def update_preferences():
        # For now, just show success message
        # In a real app, you'd store these preferences in the database
        flash("Preferences updated successfully", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/delete-account", methods=["POST"])
    @login_required
    def delete_account():
        confirm_username = request.form.get("confirm_username", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if confirm_username != g.user["username"]:
            flash("Username confirmation does not match", "danger")
            return redirect(url_for("settings"))
        
        if not check_password_hash(g.user["password_hash"], confirm_password):
            flash("Password confirmation is incorrect", "danger")
            return redirect(url_for("settings"))
        
        # Delete user data
        execute_db("DELETE FROM visits WHERE link_id IN (SELECT id FROM links WHERE user_id = ?)", [g.user["id"]])
        execute_db("DELETE FROM links WHERE user_id = ?", [g.user["id"]])
        execute_db("DELETE FROM personalized_ads WHERE user_id = ?", [g.user["id"]])
        execute_db("DELETE FROM users WHERE id = ?", [g.user["id"]])
        
        session.clear()
        flash("Your account has been deleted successfully", "info")
        return redirect(url_for("login"))

    @app.route("/analytics-overview")
    @login_required
    def analytics_overview():
        # Get all user links
        links = query_db(
            """
            SELECT id, code, primary_url, returning_url, cta_url,
                   behavior_rule, state, created_at
            FROM links
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            [g.user["id"]],
        )
        
        # Get link status distribution for chart
        link_stats = query_db(
            """
            SELECT state, COUNT(*) as count
            FROM links
            WHERE user_id = ?
            GROUP BY state
            """,
            [g.user["id"]],
        )
        
        # Get total clicks and unique visitors
        total_clicks = query_db(
            """
            SELECT COUNT(*) as count
            FROM visits v
            JOIN links l ON v.link_id = l.id
            WHERE l.user_id = ?
            """,
            [g.user["id"]],
            one=True
        )["count"]
        
        unique_visitors = query_db(
            """
            SELECT COUNT(DISTINCT session_id) as count
            FROM visits v
            JOIN links l ON v.link_id = l.id
            WHERE l.user_id = ?
            """,
            [g.user["id"]],
            one=True
        )["count"]
        
        # Get click stats for each link
        link_click_stats = {}
        for link in links:
            clicks = query_db(
                "SELECT COUNT(*) as count FROM visits WHERE link_id = ?",
                [link["id"]],
                one=True
            )["count"]
            link_click_stats[link["id"]] = {"clicks": clicks}
        
        # Prepare chart data
        chart_data = {
            "linkStats": [{"state": row["state"], "count": row["count"]} for row in link_stats]
        }
        
        return render_template(
            "analytics_overview.html",
            links=links,
            chart_data=chart_data,
            total_clicks=total_clicks,
            unique_visitors=unique_visitors,
            link_stats=link_click_stats
        )

    @app.route("/analytics-overview/export-excel")
    @login_required
    def export_excel():
        try:
            # Get all user links
            links = query_db(
                """
                SELECT id, code, primary_url, returning_url, cta_url,
                       behavior_rule, state, created_at
                FROM links
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                [g.user["id"]],
            )
            
            if not links:
                flash("No links found to export", "warning")
                return redirect(url_for("analytics_overview"))
            
            # Create Excel content using HTML table format (Excel can read HTML tables)
            html_content = """
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; font-weight: bold; }
                    .center { text-align: center; }
                </style>
            </head>
            <body>
                <h2>Analytics Export - """ + str(g.user["username"]) + """</h2>
                <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                <table>
                    <tr>
                        <th>Sr. No.</th>
                        <th>Code</th>
                        <th>Rule</th>
                        <th>State</th>
                        <th>Experience</th>
                        <th>Primary URL</th>
                        <th>Returning URL</th>
                        <th>CTA URL</th>
                        <th>Created Date</th>
                    </tr>
            """
            
            # Add data rows
            for i, link in enumerate(links, 1):
                # Safe access to user premium status
                is_premium = g.user.get("is_premium", 0) if hasattr(g.user, 'get') else g.user["is_premium"]
                experience = "Ad-Free" if is_premium else "With Ads"
                
                # Format URLs based on behavior rule
                primary_url = str(link["primary_url"])
                returning_url = str(link["returning_url"]) if link["behavior_rule"] == "progression" and link["returning_url"] != link["primary_url"] else ""
                cta_url = str(link["cta_url"]) if link["behavior_rule"] == "progression" and link["cta_url"] != link["primary_url"] else ""
                
                html_content += f"""
                    <tr>
                        <td class="center">{i}</td>
                        <td>{str(link["code"])}</td>
                        <td>{str(link["behavior_rule"]).title()}</td>
                        <td>{str(link["state"])}</td>
                        <td>{experience}</td>
                        <td>{primary_url}</td>
                        <td>{returning_url}</td>
                        <td>{cta_url}</td>
                        <td>{str(link["created_at"])[:10] if link["created_at"] else ""}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </body>
            </html>
            """
            
            # Create response with Excel MIME type
            from flask import Response
            return Response(
                html_content,
                mimetype="application/vnd.ms-excel",
                headers={
                    "Content-disposition": f"attachment; filename=analytics_export_{g.user['username']}.xls",
                    "Content-Type": "application/vnd.ms-excel; charset=utf-8"
                }
            )
            
        except Exception as e:
            flash(f"Error exporting Excel: {str(e)}", "danger")
            return redirect(url_for("analytics_overview"))

    @app.route("/analytics-overview/export-csv")
    @login_required
    def analytics_export_csv():
        try:
            # Get all user links
            links = query_db(
                """
                SELECT id, code, primary_url, returning_url, cta_url,
                       behavior_rule, state, created_at
                FROM links
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                [g.user["id"]],
            )
            
            if not links:
                flash("No links found to export", "warning")
                return redirect(url_for("analytics_overview"))
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Sr. No.",
                "Code", 
                "Rule",
                "State",
                "Experience",
                "Primary URL",
                "Returning URL",
                "CTA URL",
                "Created Date"
            ])
            
            # Write data rows
            for i, link in enumerate(links, 1):
                # Safe access to user premium status
                is_premium = g.user.get("is_premium", 0) if hasattr(g.user, 'get') else g.user["is_premium"]
                experience = "Ad-Free" if is_premium else "With Ads"
                
                # Format URLs based on behavior rule
                primary_url = str(link["primary_url"])
                returning_url = str(link["returning_url"]) if link["behavior_rule"] == "progression" and link["returning_url"] != link["primary_url"] else ""
                cta_url = str(link["cta_url"]) if link["behavior_rule"] == "progression" and link["cta_url"] != link["primary_url"] else ""
                
                writer.writerow([
                    i,
                    str(link["code"]),
                    str(link["behavior_rule"]).title(),
                    str(link["state"]),
                    experience,
                    primary_url,
                    returning_url,
                    cta_url,
                    str(link["created_at"])[:10] if link["created_at"] else ""
                ])
            
            # Create response
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": f"attachment; filename=analytics_export_{g.user['username']}.csv"}
            )
            
        except Exception as e:
            flash(f"Error exporting CSV: {str(e)}", "danger")
            return redirect(url_for("analytics_overview"))

    @app.route("/delete-link/<int:link_id>", methods=["POST"])
    @login_required
    def delete_link(link_id):
        """Delete a smart link and all its associated data"""
        try:
            # Check if link belongs to current user
            link = query_db(
                "SELECT * FROM links WHERE id = ? AND user_id = ?",
                [link_id, g.user["id"]], one=True
            )
            
            if not link:
                return jsonify({"success": False, "message": "Link not found or access denied"}), 404
            
            # Delete associated visits first (foreign key constraint)
            execute_db("DELETE FROM visits WHERE link_id = ?", [link_id])
            
            # Delete associated DDoS events if any
            execute_db("DELETE FROM ddos_events WHERE link_id = ?", [link_id])
            
            # Delete the link itself
            execute_db("DELETE FROM links WHERE id = ?", [link_id])
            
            return jsonify({
                "success": True, 
                "message": f"Link '{link['code']}' has been deleted successfully"
            })
            
        except Exception as e:
            return jsonify({"success": False, "message": f"Error deleting link: {str(e)}"}), 500

    return app


# --- Helpers ---

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_and_save_image(file, user_id):
    """Process uploaded image: save with basic validation (simplified version without PIL)"""
    if not file or not allowed_file(file.filename):
        return None
    
    try:
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Save file directly (without processing since PIL is not available)
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        return unique_filename
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def ensure_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            is_premium INTEGER DEFAULT 0,
            premium_expires_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            primary_url TEXT NOT NULL,
            returning_url TEXT NOT NULL,
            cta_url TEXT NOT NULL,
            behavior_rule TEXT NOT NULL DEFAULT 'standard',
            state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            user_id INTEGER,
            behavior_rule_id INTEGER,
            password_hash TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(behavior_rule_id) REFERENCES behavior_rules(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            ip_hash TEXT NOT NULL,
            user_agent TEXT NOT NULL,
            ts TEXT NOT NULL,
            behavior TEXT NOT NULL,
            is_suspicious INTEGER DEFAULT 0,
            target_url TEXT NOT NULL,
            region TEXT,
            device TEXT,
            FOREIGN KEY(link_id) REFERENCES links(id)
        )
        """
    )
    
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS personalized_ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
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
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS behavior_rules (
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
        """
    )

    # New table for DDoS protection events
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ddos_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            severity INTEGER NOT NULL,
            ip_hash TEXT,
            detected_at TEXT NOT NULL,
            protection_level INTEGER DEFAULT 0,
            FOREIGN KEY(link_id) REFERENCES links(id)
        )
        """
    )
    
    # Add new location columns to visits table if they don't exist
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN country TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN city TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN latitude REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN longitude REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN timezone TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add password protection column to links table if it doesn't exist
    try:
        conn.execute("ALTER TABLE links ADD COLUMN password_hash TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # New table for rate limiting
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_hash TEXT NOT NULL,
            link_id INTEGER,
            request_count INTEGER DEFAULT 1,
            window_start TEXT NOT NULL,
            window_type TEXT NOT NULL,
            blocked_until TEXT,
            FOREIGN KEY(link_id) REFERENCES links(id)
        )
        """
    )

    def ensure_column(table: str, column: str, ddl: str):
        cur = conn.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cur.fetchall()]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    ensure_column("links", "behavior_rule", "behavior_rule TEXT NOT NULL DEFAULT 'standard'")
    ensure_column("links", "user_id", "user_id INTEGER")
    ensure_column("links", "behavior_rule_id", "behavior_rule_id INTEGER")
    ensure_column("links", "protection_level", "protection_level INTEGER DEFAULT 0")
    ensure_column("links", "auto_disabled", "auto_disabled INTEGER DEFAULT 0")
    ensure_column("links", "ddos_detected_at", "ddos_detected_at TEXT")
    ensure_column("visits", "region", "region TEXT")
    ensure_column("visits", "device", "device TEXT")
    ensure_column("users", "email", "email TEXT")
    ensure_column("users", "is_premium", "is_premium INTEGER DEFAULT 0")
    ensure_column("users", "premium_expires_at", "premium_expires_at TEXT")
    ensure_column("personalized_ads", "grid_position", "grid_position INTEGER DEFAULT 1")
    ensure_column("personalized_ads", "ad_type", "ad_type TEXT DEFAULT 'custom'")
    ensure_column("personalized_ads", "image_filename", "image_filename TEXT")
    
    # New columns for Grabify-like detailed visitor tracking
    ensure_column("visits", "browser", "browser TEXT")
    ensure_column("visits", "os", "os TEXT")
    ensure_column("visits", "isp", "isp TEXT")
    ensure_column("visits", "hostname", "hostname TEXT")
    ensure_column("visits", "org", "org TEXT")
    ensure_column("visits", "referrer", "referrer TEXT")
    ensure_column("visits", "ip_address", "ip_address TEXT")
    ensure_column("ddos_events", "ip_address", "ip_address TEXT")
    ensure_column("rate_limits", "ip_address", "ip_address TEXT")
    
    # Membership Tier Columns
    ensure_column("users", "membership_tier", "membership_tier TEXT DEFAULT 'free'")
    ensure_column("links", "expires_at", "expires_at TEXT")
    
    conn.commit()
    conn.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def query_db(query: str, args=None, one=False):
    cur = get_db().execute(query, args or [])
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query: str, args=None):
    db = get_db()
    db.execute(query, args or [])
    db.commit()


def _before_request():
    ensure_session()
    g.user = None
    uid = session.get(USER_SESSION_KEY)
    if uid:
        user = query_db("SELECT * FROM users WHERE id = ?", [uid], one=True)
        g.user = user


def _teardown(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_session() -> str:
    sess_id = session.get("sid")
    if sess_id:
        return sess_id
    sess_id = str(uuid.uuid4())
    session["sid"] = sess_id
    return sess_id


def generate_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(alphabet[int.from_bytes(os.urandom(2), "big") % len(alphabet)] for _ in range(length))


def send_email(to_email: str, subject: str, body: str):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT", 587)
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not smtp_host or not smtp_user or not smtp_pass:
        print(f"--- MOCK EMAIL SEndING ---")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print(f"--------------------------")
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email

        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")


def utcnow() -> datetime:
    return datetime.utcnow()


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def classify_behavior(link_id: int, session_id: str, visits, now: datetime, behavior_rule=None) -> str:
    """Classify user behavior based on custom or default rules"""
    
    # Get behavior rule settings
    if behavior_rule:
        returning_window_hours = behavior_rule["returning_window_hours"]
        interested_threshold = behavior_rule["interested_threshold"]
        engaged_threshold = behavior_rule["engaged_threshold"]
    else:
        # Use default values if no rule provided
        returning_window_hours = RETURNING_WINDOW_HOURS
        interested_threshold = 2
        engaged_threshold = MULTI_CLICK_THRESHOLD
    
    # Count recent visits within the custom window
    recent = [datetime.fromisoformat(v["ts"]) for v in visits if (now - datetime.fromisoformat(v["ts"])) < timedelta(hours=returning_window_hours)]
    
    # Count total visits for this session
    res = query_db(
        """
        SELECT COUNT(*) AS c FROM visits
        WHERE link_id = ? AND session_id = ?
        """,
        [link_id, session_id],
        one=True,
    )
    per_session = res["c"] if res else 0

    # Apply custom thresholds
    if per_session >= engaged_threshold:
        return "Highly engaged", per_session
    if len(recent) >= interested_threshold:
        return "Interested", per_session
    return "Curious", per_session


def detect_suspicious(visits, now: datetime) -> bool:
    if len(visits) < 2:
        return False
    latest = datetime.fromisoformat(visits[0]["ts"])
    delta = (now - latest).total_seconds()
    return delta < SUSPICIOUS_INTERVAL_SECONDS


def decide_target(link, behavior: str, session_count: int) -> str:
    # Use dictionary syntax for sqlite3.Row
    rule = (link["behavior_rule"] if link["behavior_rule"] else "standard").lower()
    
    if rule == "progression":
        if session_count <= 1:
            return link["primary_url"]
        if session_count == 2:
            return link["returning_url"]
        return link["cta_url"]

    # standard behavior-based routing
    if behavior == "Highly engaged":
        return link["cta_url"]
    if behavior == "Interested":
        return link["returning_url"]
    return link["primary_url"]


def evaluate_state(link_id: int, now: datetime) -> str:
    recent = query_db(
        """
        SELECT ts, is_suspicious FROM visits
        WHERE link_id = ?
        ORDER BY ts DESC
        LIMIT 30
        """,
        [link_id],
    )
    if not recent:
        return "Active"

    latest_time = datetime.fromisoformat(recent[0]["ts"])
    days_since = (now - latest_time).days
    suspicious_hits = sum(1 for v in recent if v["is_suspicious"])

    if suspicious_hits >= 5:
        return "Inactive"
    if days_since > STATE_DECAY_DAYS:
        return "Inactive"
    if days_since > ATTENTION_DECAY_DAYS:
        return "Decaying"
    if len(recent) >= 10:
        return "High Interest"
    return "Active"


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.get("user"):
            flash("Please log in to continue", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def trust_score(link_id: int) -> int:
    metrics = query_db(
        """
        SELECT
            COUNT(*) AS total,
            SUM(is_suspicious) AS suspicious,
            SUM(CASE WHEN behavior = 'Highly engaged' THEN 1 ELSE 0 END) AS engaged
        FROM visits WHERE link_id = ?
        """,
        [link_id],
        one=True,
    )
    total = metrics["total"] or 0
    suspicious = metrics["suspicious"] or 0
    engaged = metrics["engaged"] or 0
    if total == 0:
        return 50
    score = 70 + int((engaged / max(total, 1)) * 20) - int((suspicious / max(total, 1)) * 40)
    return max(1, min(score, 100))


def attention_decay(visits):
    if not visits:
        return []
    # bucket by day to show drop-off
    buckets = {}
    for v in visits:
        day = datetime.fromisoformat(v["ts"]).date().isoformat()
        buckets[day] = buckets.get(day, 0) + 1
    return [{"day": k, "count": buckets[k]} for k in sorted(buckets.keys())]


def detect_device(user_agent: str) -> str:
    """Detect device type from user agent string."""
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "Mobile"
    elif "tablet" in ua or "ipad" in ua:
        return "Tablet"
    else:
        return "Desktop"


# Simple in-memory cache for geolocation (IP -> dict)
# In production, use Redis or database
geo_cache = {}

def get_client_ip():
    """
    Get the best available client IP address, checking proxy headers.
    """
    # Check X-Forwarded-For (standard for proxies)
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    
    # Check X-Real-IP (common alternative)
    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
        
    # Fallback to direct connection
    return request.remote_addr or "unknown"

def get_public_ip_fallback():
    """
    Fetch the server's own public IP.
    Useful when running locally to see real geolocation data.
    """
    try:
        response = requests.get('https://api.ipify.org', timeout=3)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        print(f"Could not fetch public IP: {e}")
    return None

def get_api_location(ip: str) -> dict:
    """Get location data from ip-api.com with caching."""
    
    # Handle private IPs by trying to resolve public IP (for dev/testing)
    if not ip or ip == "unknown" or ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10."):
        print(f"Private IP detected ({ip}). Attempting to fetch public IP for geolocation...", flush=True)
        public_ip = get_public_ip_fallback()
        if public_ip:
            print(f"Using public IP {public_ip} instead of {ip}", flush=True)
            ip = public_ip
        else:
            return {'status': 'private'}
    
    # Check cache
    if ip in geo_cache:
        # crude expiration check could be added here
        return geo_cache[ip]
    
    # Priority 1: IP2Location.io (Requested by User)
    try:
        # Note: In production, you should set IP2LOCATION_API_KEY in environment variables
        # The 'demo' key has strict limits, but allows testing
        api_key = os.environ.get("IP2LOCATION_API_KEY", "E7A157580629094000305F862A145025") # Providing a free shared key or rely on demo if empty
        # If no key, IP2Location might not work well, so we'll try robust fallback
        
        # Using the io API
        url = f"https://api.ip2location.io/?key={api_key}&ip={ip}&format=json"
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            # Map IP2Location fields to our expected format
            # IP2Location returns: country_name, region_name, city_name, etc.
            if 'country_name' in data:
                mapped_data = {
                    'status': 'success',
                    'country': data.get('country_name'),
                    'countryCode': data.get('country_code'),
                    'regionName': data.get('region_name'),
                    'city': data.get('city_name'),
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                    'timezone': data.get('time_zone'),
                    'isp': data.get('isp'),
                    'org': data.get('as')
                }
                geo_cache[ip] = mapped_data
                return mapped_data
    except Exception as e:
        print(f"IP2Location error: {e}")
        print("Falling back to ip-api.com...")

    # Priority 2: ip-api.com (Fallback)
    try:
        # http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                geo_cache[ip] = data
                return data
    except Exception as e:
        print(f"API Geolocation error for {ip}: {e}")
        
    return {'status': 'fail'}

def detect_region(ip: str) -> str:
    """Detect region from IP address using ip-api.com."""
    data = get_api_location(ip)
    
    if data.get('status') == 'private':
        return "Local/Private"
        
    if data.get('status') == 'success':
        city = data.get('city', '')
        country = data.get('country', 'Unknown Country')
        if city:
            return f"{city}, {country}"
        return country
        
    return "Unknown"


def get_detailed_location(ip: str) -> dict:
    """Get detailed location information including country, city, coordinates using ip-api.com."""
    location_info = {
        'country': 'Unknown',
        'city': 'Unknown', 
        'region': 'Unknown',
        'latitude': None,
        'longitude': None,
        'timezone': None
    }
    
    data = get_api_location(ip)
    
    if data.get('status') == 'private':
        location_info['country'] = 'Local/Private'
        location_info['region'] = 'Local/Private'
        return location_info
        
    if data.get('status') == 'success':
        location_info['country'] = data.get('country', 'Unknown')
        location_info['city'] = data.get('city', 'Unknown')
        location_info['region'] = data.get('regionName', 'Unknown')
        location_info['latitude'] = data.get('lat')
        location_info['longitude'] = data.get('lon')
        location_info['timezone'] = data.get('timezone')
    
    return location_info


def country_to_continent(country: str) -> str:
    """Map country names to continents."""
    if not country or country in ['Unknown', 'Local/Private']:
        return country
    
    # Comprehensive country to continent mapping
    continent_map = {
        # North America
        'United States': 'North America',
        'Canada': 'North America',
        'Mexico': 'North America',
        'Guatemala': 'North America',
        'Belize': 'North America',
        'El Salvador': 'North America',
        'Honduras': 'North America',
        'Nicaragua': 'North America',
        'Costa Rica': 'North America',
        'Panama': 'North America',
        'Cuba': 'North America',
        'Jamaica': 'North America',
        'Haiti': 'North America',
        'Dominican Republic': 'North America',
        'Bahamas': 'North America',
        'Barbados': 'North America',
        'Trinidad and Tobago': 'North America',
        
        # South America
        'Brazil': 'South America',
        'Argentina': 'South America',
        'Chile': 'South America',
        'Peru': 'South America',
        'Colombia': 'South America',
        'Venezuela': 'South America',
        'Ecuador': 'South America',
        'Bolivia': 'South America',
        'Paraguay': 'South America',
        'Uruguay': 'South America',
        'Guyana': 'South America',
        'Suriname': 'South America',
        'French Guiana': 'South America',
        
        # Europe
        'United Kingdom': 'Europe',
        'Germany': 'Europe',
        'France': 'Europe',
        'Italy': 'Europe',
        'Spain': 'Europe',
        'Netherlands': 'Europe',
        'Belgium': 'Europe',
        'Switzerland': 'Europe',
        'Austria': 'Europe',
        'Sweden': 'Europe',
        'Norway': 'Europe',
        'Denmark': 'Europe',
        'Finland': 'Europe',
        'Poland': 'Europe',
        'Czech Republic': 'Europe',
        'Hungary': 'Europe',
        'Romania': 'Europe',
        'Bulgaria': 'Europe',
        'Greece': 'Europe',
        'Portugal': 'Europe',
        'Ireland': 'Europe',
        'Croatia': 'Europe',
        'Serbia': 'Europe',
        'Bosnia and Herzegovina': 'Europe',
        'Slovenia': 'Europe',
        'Slovakia': 'Europe',
        'Lithuania': 'Europe',
        'Latvia': 'Europe',
        'Estonia': 'Europe',
        'Ukraine': 'Europe',
        'Belarus': 'Europe',
        'Moldova': 'Europe',
        'Russia': 'Europe',
        'Iceland': 'Europe',
        'Luxembourg': 'Europe',
        'Malta': 'Europe',
        'Cyprus': 'Europe',
        'Albania': 'Europe',
        'Montenegro': 'Europe',
        'North Macedonia': 'Europe',
        
        # Asia
        'China': 'Asia',
        'India': 'Asia',
        'Japan': 'Asia',
        'South Korea': 'Asia',
        'Indonesia': 'Asia',
        'Thailand': 'Asia',
        'Vietnam': 'Asia',
        'Philippines': 'Asia',
        'Malaysia': 'Asia',
        'Singapore': 'Asia',
        'Myanmar': 'Asia',
        'Cambodia': 'Asia',
        'Laos': 'Asia',
        'Bangladesh': 'Asia',
        'Pakistan': 'Asia',
        'Afghanistan': 'Asia',
        'Iran': 'Asia',
        'Iraq': 'Asia',
        'Turkey': 'Asia',
        'Saudi Arabia': 'Asia',
        'United Arab Emirates': 'Asia',
        'Qatar': 'Asia',
        'Kuwait': 'Asia',
        'Bahrain': 'Asia',
        'Oman': 'Asia',
        'Yemen': 'Asia',
        'Jordan': 'Asia',
        'Lebanon': 'Asia',
        'Syria': 'Asia',
        'Israel': 'Asia',
        'Palestine': 'Asia',
        'Kazakhstan': 'Asia',
        'Uzbekistan': 'Asia',
        'Turkmenistan': 'Asia',
        'Kyrgyzstan': 'Asia',
        'Tajikistan': 'Asia',
        'Mongolia': 'Asia',
        'North Korea': 'Asia',
        'Nepal': 'Asia',
        'Bhutan': 'Asia',
        'Sri Lanka': 'Asia',
        'Maldives': 'Asia',
        'Brunei': 'Asia',
        'East Timor': 'Asia',
        
        # Africa
        'Nigeria': 'Africa',
        'Ethiopia': 'Africa',
        'Egypt': 'Africa',
        'South Africa': 'Africa',
        'Kenya': 'Africa',
        'Uganda': 'Africa',
        'Algeria': 'Africa',
        'Sudan': 'Africa',
        'Morocco': 'Africa',
        'Angola': 'Africa',
        'Ghana': 'Africa',
        'Mozambique': 'Africa',
        'Madagascar': 'Africa',
        'Cameroon': 'Africa',
        'Ivory Coast': 'Africa',
        'Niger': 'Africa',
        'Burkina Faso': 'Africa',
        'Mali': 'Africa',
        'Malawi': 'Africa',
        'Zambia': 'Africa',
        'Senegal': 'Africa',
        'Somalia': 'Africa',
        'Chad': 'Africa',
        'Zimbabwe': 'Africa',
        'Guinea': 'Africa',
        'Rwanda': 'Africa',
        'Benin': 'Africa',
        'Tunisia': 'Africa',
        'Burundi': 'Africa',
        'South Sudan': 'Africa',
        'Togo': 'Africa',
        'Sierra Leone': 'Africa',
        'Libya': 'Africa',
        'Liberia': 'Africa',
        'Central African Republic': 'Africa',
        'Mauritania': 'Africa',
        'Eritrea': 'Africa',
        'Gambia': 'Africa',
        'Botswana': 'Africa',
        'Namibia': 'Africa',
        'Gabon': 'Africa',
        'Lesotho': 'Africa',
        'Guinea-Bissau': 'Africa',
        'Equatorial Guinea': 'Africa',
        'Mauritius': 'Africa',
        'Eswatini': 'Africa',
        'Djibouti': 'Africa',
        'Comoros': 'Africa',
        'Cape Verde': 'Africa',
        'São Tomé and Príncipe': 'Africa',
        'Seychelles': 'Africa',
        
        # Oceania
        'Australia': 'Oceania',
        'New Zealand': 'Oceania',
        'Papua New Guinea': 'Oceania',
        'Fiji': 'Oceania',
        'Solomon Islands': 'Oceania',
        'Vanuatu': 'Oceania',
        'Samoa': 'Oceania',
        'Micronesia': 'Oceania',
        'Tonga': 'Oceania',
        'Kiribati': 'Oceania',
        'Palau': 'Oceania',
        'Marshall Islands': 'Oceania',
        'Tuvalu': 'Oceania',
        'Nauru': 'Oceania',
    }
    
    # Return mapped continent or the original country if not found
    return continent_map.get(country, country)


def detect_region_fallback(ip: str) -> str:
    """Fallback region detection using real IP API."""
    try:
        # Check for localhost
        if ip == "127.0.0.1" or ip == "localhost":
            return "Localhost"

        parts = ip.split(".")
        if len(parts) != 4:
            return "Unknown"
            
        first = int(parts[0])
        
        # Check for Private Networks
        if first == 10:
            return "Private Network"
        if first == 192 and int(parts[1]) == 168:
            return "Private Network" 
        if first == 172 and (16 <= int(parts[1]) <= 31):
            return "Private Network"

        # Try to get real data from free API (with timeout to prevent hanging)
        try:
            import requests
            response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    # return continent or country
                    # ip-api free doesn't give continent directly, but gives country/timezone
                    # We can use timezone to infer roughly or just return Country
                    return data.get("country", "Unknown")
        except Exception:
            pass
            
        return "Unknown"

    except (ValueError, IndexError):
        return "Unknown"

def parse_browser(user_agent: str) -> str:
    """Parse browser name and version from User-Agent string."""
    if not user_agent or user_agent == "unknown":
        return "Unknown"
    
    ua = user_agent.lower()
    
    # Check for common browsers (order matters - more specific first)
    if "edg/" in ua or "edge/" in ua:
        # Extract Edge version
        import re
        match = re.search(r'edg[e]?/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Microsoft Edge ({version})" if version else "Microsoft Edge"
    
    if "opr/" in ua or "opera" in ua:
        import re
        match = re.search(r'(?:opr|opera)[/\s](\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Opera ({version})" if version else "Opera"
    
    if "chrome" in ua and "chromium" not in ua:
        import re
        match = re.search(r'chrome/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Chrome ({version})" if version else "Chrome"
    
    if "firefox" in ua:
        import re
        match = re.search(r'firefox/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Firefox ({version})" if version else "Firefox"
    
    if "safari" in ua and "chrome" not in ua:
        import re
        match = re.search(r'version/(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Safari ({version})" if version else "Safari"
    
    if "msie" in ua or "trident" in ua:
        import re
        match = re.search(r'(?:msie |rv:)(\d+[\.\d]*)', ua)
        version = match.group(1) if match else ""
        return f"Internet Explorer ({version})" if version else "Internet Explorer"
    
    if "chromium" in ua:
        return "Chromium"
    
    return "Unknown Browser"


def parse_os(user_agent: str) -> str:
    """Parse operating system from User-Agent string."""
    if not user_agent or user_agent == "unknown":
        return "Unknown"
    
    ua = user_agent.lower()
    
    # Windows versions
    if "windows nt 10.0" in ua:
        if "windows nt 10.0; win64" in ua:
            return "Windows 10/11 x64"
        return "Windows 10/11"
    if "windows nt 6.3" in ua:
        return "Windows 8.1"
    if "windows nt 6.2" in ua:
        return "Windows 8"
    if "windows nt 6.1" in ua:
        return "Windows 7"
    if "windows nt 6.0" in ua:
        return "Windows Vista"
    if "windows nt 5.1" in ua or "windows xp" in ua:
        return "Windows XP"
    if "windows" in ua:
        return "Windows"
    
    # macOS
    if "mac os x" in ua:
        import re
        match = re.search(r'mac os x (\d+[_\.]\d+)', ua)
        if match:
            version = match.group(1).replace('_', '.')
            return f"macOS {version}"
        return "macOS"
    
    # iOS
    if "iphone" in ua:
        import re
        match = re.search(r'iphone os (\d+[_\.]\d+)', ua)
        if match:
            version = match.group(1).replace('_', '.')
            return f"iOS {version} (iPhone)"
        return "iOS (iPhone)"
    if "ipad" in ua:
        return "iOS (iPad)"
    
    # Android
    if "android" in ua:
        import re
        match = re.search(r'android (\d+[\.\d]*)', ua)
        if match:
            return f"Android {match.group(1)}"
        return "Android"
    
    # Linux distributions
    if "ubuntu" in ua:
        return "Ubuntu Linux"
    if "fedora" in ua:
        return "Fedora Linux"
    if "linux" in ua:
        return "Linux"
    
    # Chrome OS
    if "cros" in ua:
        return "Chrome OS"
    
    return "Unknown OS"


def normalize_isp(isp_name: str) -> str:
    """Normalize common ISP names to prevent duplicates in analytics."""
    if not isp_name or isp_name.lower() == 'unknown':
        return "Other/Unknown"
    
    name = isp_name.strip()
    # Remove trailing dot if exists
    if name.endswith('.'):
        name = name[:-1].strip()
        
    name_lower = name.lower()
    
    # Reliance Jio variations
    if "reliance jio" in name_lower or "reliancejio" in name_lower:
        return "Reliance Jio"
    
    # Airtel variations
    if "bharti airtel" in name_lower or "airtel" in name_lower:
        return "Bharti Airtel"
    
    # Vodafone Idea variations
    if "vodafone" in name_lower or "idea" in name_lower:
        return "Vi (Vodafone Idea)"
    
    # BSNL variations
    if "bsnl" in name_lower or "bharat sanchar" in name_lower:
        return "BSNL"
    
    # Tata Tele/Communications
    if "tata tele" in name_lower or "tata comm" in name_lower:
        return "Tata"
        
    return name



def get_isp_info(ip: str) -> dict:
    """Get ISP and hostname via DNS reverse lookup and API fallback."""
    result = {
        'isp': 'Unknown',
        'hostname': 'Unknown',
        'org': 'Unknown'
    }
    
    if not ip or ip == "unknown" or ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10."):
        # Try to get public IP for dev mode to show real ISP
        public_ip = get_public_ip_fallback()
        if public_ip:
            ip = public_ip
        else:
            result['isp'] = 'Local Network'
            result['hostname'] = 'localhost'
            return result
    
    # Try DNS reverse lookup for hostname
    try:
        import socket
        hostname = socket.gethostbyaddr(ip)[0]
        result['hostname'] = hostname
        
        # Extract potential ISP from hostname
        # e.g., "user.isp.com" -> "isp.com"
        parts = hostname.split('.')
        if len(parts) >= 2:
            result['isp'] = '.'.join(parts[-2:])
    except (socket.herror, socket.gaierror, socket.timeout):
        pass
    
    # Try ip-api.com for accurate ISP info (free tier, no API key needed)
    try:
        import requests
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=isp,org,as", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('isp'):
                result['isp'] = normalize_isp(data['isp'])
            if data.get('org'):
                result['org'] = data['org']
    except Exception:
        pass
    
    return result

appl = create_app()
if __name__ == "__main__":
    appl.run(debug=True, port=5000, host="0.0.0.0")
