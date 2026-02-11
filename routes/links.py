"""
Smart Link Intelligence - Link Management Routes
Link creation, redirection, password protection, and deletion
"""

import sqlite3
import csv
import io
from datetime import datetime, timedelta, timezone
from collections import Counter
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, g, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from decorators import login_required, login_or_admin_required
from database import query_db, execute_db
from config import MEMBERSHIP_TIERS, RETURNING_WINDOW_HOURS, MULTI_CLICK_THRESHOLD
from utils import (
    generate_code, utcnow, get_link_password_hash, ensure_session, 
    get_client_ip, hash_value, detect_region, detect_device, 
    get_detailed_location, parse_browser, parse_os, get_isp_info,
    classify_behavior, detect_suspicious, decide_target, evaluate_state,
    trust_score, attention_decay, country_to_continent, normalize_isp
)

links_bp = Blueprint('links', __name__)


@links_bp.route("/create", methods=["POST"])
@login_required
def create():
    """Create a new link"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    print("Create route called")  # Debug
    data = {k: (request.form.get(k) or "").strip() for k in request.form.keys()}
    print(f"Form data: {data}")  # Debug
    
    # Check Membership Limits
    user_dict = dict(g.user) if g.user else {}
    user_tier = user_dict.get("membership_tier", "free")
    if not user_tier: 
        user_tier = "free"
        
    tier_rules = MEMBERSHIP_TIERS.get(user_tier, MEMBERSHIP_TIERS["free"])
    
    # Check link count
    current_links_count = query_db("SELECT COUNT(*) as count FROM links WHERE user_id = ?", [g.user["id"]], one=True)["count"]
    if current_links_count >= tier_rules["max_links"]:
        flash(f"Limit Reached: Your {tier_rules['name']} plan allows a maximum of {tier_rules['max_links']} links. Please upgrade to create more.", "warning")
        return redirect(url_for("main.index"))
    
    # Calculate expiration
    if tier_rules["validity_days"]:
        expires_at = (utcnow() + timedelta(days=tier_rules["validity_days"])).isoformat()
    else:
        expires_at = None

    # Enforce Feature Restrictions for Free Users
    requested_rule = data.get("behavior_rule", "standard")
    if user_tier == "free" and requested_rule in ["progression", "password_protected"]:
        data["behavior_rule"] = "standard"
        data["returning_url"] = ""
        data["cta_url"] = ""
        data["password"] = ""
        
    primary_url = data.get("primary_url")
    if not primary_url:
        flash("Primary URL is required", "danger")
        return redirect(url_for("main.index"))

    code = data.get("code") or generate_code()
    if query_db("SELECT id FROM links WHERE code = ?", [code], one=True):
        flash("Code already exists, please choose another", "danger")
        return redirect(url_for("main.index"))

    # Get behavior rule ID (optional)
    behavior_rule_id = data.get("behavior_rule_id")
    if behavior_rule_id:
        behavior_rule_id = int(behavior_rule_id)
    else:
        behavior_rule_id = None

    # Get security profile ID (Elite Pro only)
    security_profile_id = data.get("security_profile_id")
    if security_profile_id and user_tier == "elite_pro":
        security_profile_id = int(security_profile_id)
    else:
        security_profile_id = None

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
                 behavior_rule, created_at, state, user_id, 
                 behavior_rule_id, security_profile_id, password_hash, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                code,
                primary_url,
                data.get("returning_url") or primary_url,
                data.get("cta_url") or primary_url,
                data.get("behavior_rule") or "standard",
                now.isoformat(),
                "Active",
                g.user["id"],
                behavior_rule_id,
                security_profile_id,
                password_hash,
                expires_at,
            ],
        )
    except sqlite3.IntegrityError as e:
        flash(f"Database Integrity Error: {str(e)}", "danger")
        return redirect(url_for("main.index"))
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"An unexpected error occurred: {str(e)}", "danger")
        return redirect(url_for("main.index"))
    
    flash(f"Link created with code {code}", "success")
    
    # Track user activity
    track_user_activity(g.user["id"], "create_link", f"Created link: {code} -> {primary_url}")
    
    # Store full link for the success box on dashboard
    base_url = request.host_url.rstrip('/')
    session['new_link'] = f"{base_url}/r/{code}"
    return redirect(url_for("main.index"))


@links_bp.route("/r/<code>")
def redirect_link(code):
    """Redirect to target URL based on link behavior"""
    # Import here to avoid circular imports
    from admin_panel import track_ad_impression
    from ddos_protection import DDoSProtection
    
    link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
    if not link:
        abort(404)

    # Check if link is password protected - ALWAYS require password
    password_hash = get_link_password_hash(link)
    if password_hash:
        # Always redirect to password page for password-protected links
        return redirect(url_for("links.password_protected", code=code))

    # Check Expiration
    if link["expires_at"]:
        try:
            expires_at = datetime.fromisoformat(link["expires_at"])
            if utcnow() > expires_at:
                flash("This link has expired.", "warning")
                return redirect(url_for("main.landing"))
        except ValueError:
            pass  # Invalid date format, ignore

    # DDoS Protection Check
    link_owner = query_db("SELECT membership_tier, is_premium FROM users WHERE id = ?", [link["user_id"]], one=True)
    tier_name = link_owner["membership_tier"] if link_owner and link_owner["membership_tier"] else "free"
    
    tier_config = MEMBERSHIP_TIERS.get(tier_name, MEMBERSHIP_TIERS["free"])
    has_ddos_protection = tier_config["ddos_protection"]

    ip_address = get_client_ip()
    ip_hash = hash_value(ip_address)

    if has_ddos_protection:
        ddos_protection = DDoSProtection("smart_links.db")
        
        # DDoS Detection - Run this BEFORE blocking to allow escalation to Level 5
        is_ddos, ddos_reason, new_protection_level = ddos_protection.detect_ddos_attack(link["id"])
        if is_ddos:
            current_level = link['protection_level']
            # Only apply if new level is higher than current
            if new_protection_level > current_level:
                protection_action = ddos_protection.apply_protection(link["id"], new_protection_level)
                
                if protection_action in ['link_disabled', 'temporary_disabled']:
                    flash("This link has been automatically protected due to suspicious activity.", "warning")
                    return render_template("ddos_blocked.html", 
                                        message="Link Protected", 
                                        description="This link has been automatically protected due to detected attacks.")

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
                flash("Please verify you're human to continue.", "info")
                return render_template("ddos_blocked.html", 
                                    message="Verification Required", 
                                    description="Please verify you're human to access this link.")
        
        # Rate limiting check (Runs if link is not globally blocked)
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

    sess_id = ensure_session()
    user_agent = request.headers.get("User-Agent", "unknown")[:255]
    
    # Detect region and device
    region = detect_region(ip_address)
    device = detect_device(user_agent)
    
    # Get detailed location information
    location_info = get_detailed_location(ip_address)
    
    # Parse browser and OS from user agent
    browser = parse_browser(user_agent)
    os_name = parse_os(user_agent)
    
    # Get ISP info
    isp_info = get_isp_info(ip_address)
    
    # Get referrer (Smart Tracking)
    # 1. Check URL parameters first (robust for mobile apps/PDFs)
    referrer = (
        request.args.get("ref") or 
        request.args.get("source") or 
        request.args.get("utm_source")
    )
    
    # 2. Check User-Agent for social media apps (they often strip referrer)
    # This takes priority over HTTP Referer to detect WhatsApp, Instagram, etc.
    if not referrer:
        ua_lower = user_agent.lower()
        
        # WhatsApp detection - comprehensive patterns
        # WhatsApp uses different User-Agents depending on platform:
        # - Android: Contains "WhatsApp" or "wv)" (WebView)
        # - iOS: Often just shows as Safari but with specific patterns
        # - Desktop: May show as Chrome/Edge
        if any(x in ua_lower for x in [
            'whatsapp',           # Direct WhatsApp identifier
            'wa/',                # WhatsApp short form
            'wv)',                # Android WebView (commonly used by WhatsApp)
        ]):
            referrer = 'WhatsApp'
        
        # Instagram detection
        elif 'instagram' in ua_lower:
            referrer = 'Instagram'
        
        # Facebook detection - covers app and messenger
        elif any(x in ua_lower for x in [
            'fban',               # Facebook App
            'fbav',               # Facebook App Version
            'fb_iab',             # Facebook In-App Browser
            'fbios',              # Facebook iOS
            'messenger',          # Facebook Messenger
            'fb4a',               # Facebook for Android
        ]):
            referrer = 'Facebook'
        
        # Twitter/X detection
        elif any(x in ua_lower for x in ['twitter', 'twitterbot']):
            referrer = 'Twitter'
        
        # LinkedIn detection
        elif 'linkedin' in ua_lower:
            referrer = 'LinkedIn'
        
        # Telegram detection
        elif 'telegram' in ua_lower:
            referrer = 'Telegram'
    
    # 3. Check HTTP Referer header
    if not referrer:
        http_referrer = request.headers.get("Referer", "")
        
        if http_referrer:
            from urllib.parse import urlparse
            try:
                ref_domain = urlparse(http_referrer).netloc.lower()
                current_domain = urlparse(request.host_url).netloc.lower()
                
                # Check if it's an external referrer
                if ref_domain and ref_domain != current_domain:
                    # Check for known social media domains
                    if any(x in ref_domain for x in ['whatsapp.com', 'wa.me', 'chat.whatsapp.com']):
                        referrer = 'WhatsApp'
                    elif any(x in ref_domain for x in ['facebook.com', 'fb.com', 'messenger.com', 'fb.me', 'm.facebook.com', 'l.facebook.com', 'lm.facebook.com']):
                        referrer = 'Facebook'
                    elif any(x in ref_domain for x in ['instagram.com', 'l.instagram.com']):
                        referrer = 'Instagram'
                    elif any(x in ref_domain for x in ['t.co', 'twitter.com', 'x.com', 'mobile.twitter.com']):
                        referrer = 'Twitter'
                    elif any(x in ref_domain for x in ['linkedin.com', 'lnkd.in']):
                        referrer = 'LinkedIn'
                    elif any(x in ref_domain for x in ['youtube.com', 'youtu.be', 'm.youtube.com']):
                        referrer = 'YouTube'
                    elif any(x in ref_domain for x in ['t.me', 'telegram.me', 'telegram.org']):
                        referrer = 'Telegram'
                    elif any(x in ref_domain for x in ['google.com', 'google.', 'www.google.']):
                        referrer = 'Google'
                    elif 'mail.google.com' in ref_domain:
                        referrer = 'Gmail'
                    else:
                        # External referrer - use the full URL
                        referrer = http_referrer
                else:
                    # Internal referrer (from your own dashboard) - mark as no referrer
                    referrer = "no referrer"
            except:
                # If parsing fails, use the referrer as-is if it looks like a URL
                if http_referrer.startswith(('http://', 'https://')):
                    referrer = http_referrer
                else:
                    referrer = "no referrer"
        else:
            referrer = "no referrer"
            
    referrer = referrer[:500]  # Truncate for DB safety
    
    now = utcnow()

    visits = query_db(
        """
        SELECT ts, ip_hash FROM visits
        WHERE link_id = ?
        ORDER BY ts DESC
        LIMIT 20
        """,
        [link["id"]],
    )
    
    # DDoS Protection & Behavioral Rules
    ddos_protection = DDoSProtection("smart_links.db")
    ddos_rules = ddos_protection.get_link_rules(link["id"])
    
    # Get behavior rule settings (separate from security profile)
    behavior_rule = None
    if link["behavior_rule_id"]:
        behavior_rule = query_db("SELECT * FROM behavior_rules WHERE id = ?", [link["behavior_rule_id"]], one=True)
    
    if not behavior_rule:
        # Fallback to user's default behavioral rule
        behavior_rule = query_db("SELECT * FROM behavior_rules WHERE user_id = ? AND is_default = 1", [link["user_id"]], one=True)
    
    behavior, per_session_count = classify_behavior(link["id"], sess_id, visits, now, dict(behavior_rule) if behavior_rule else None)
    suspicious = detect_suspicious(visits, now, ip_hash, ddos_rules)
    target_url = decide_target(link, behavior, per_session_count)

    target_url = decide_target(link, behavior, per_session_count)

    # Check if the visitor is the owner of the link
    is_owner = g.user and g.user["id"] == link["user_id"]

    if not is_owner:
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

        new_state = evaluate_state(link["id"], now, ddos_rules)
        if new_state != link["state"]:
            execute_db("UPDATE links SET state = ? WHERE id = ?", [new_state, link["id"]])
    else:
        # If owner, just ensure state doesn't change arbitrarily, or maybe we just don't touch it.
        # We definitely don't record the visit.
        new_state = link["state"]

    if new_state == "Inactive":
        flash("Link became inactive due to decay or abnormal behavior", "warning")
        return redirect(url_for("main.index"))

    # Check if user wants to skip ads
    skip_ads = request.args.get('direct', '').lower() == 'true'
    
    # Check if the link owner has ad-free experience
    link_owner_tier = link_owner["membership_tier"] if link_owner and link_owner["membership_tier"] else "free"
    link_owner_config = MEMBERSHIP_TIERS.get(link_owner_tier, MEMBERSHIP_TIERS["free"])
    has_ad_free_experience = link_owner_config["ad_free"]
    
    # Also check legacy premium status for backward compatibility
    is_premium_link = link_owner and link_owner["is_premium"]
    
    # Skip ads if: direct parameter, premium user, or Elite Pro user
    if skip_ads or is_premium_link or has_ad_free_experience:
        return redirect(target_url)
    
    # Redirect to ads page for Free and Elite users
    return redirect(url_for("links.show_ads", code=code, target=target_url))


@links_bp.route("/ads/<code>")
def show_ads(code):
    """Show ads page before redirecting to target"""
    # Import here to avoid circular imports
    from admin_panel import track_ad_impression
    
    target_url = request.args.get('target')
    if not target_url:
        flash("Invalid redirect target", "danger")
        return redirect(url_for("main.index"))
    
    link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
    if not link:
        flash("Link not found", "danger")
        return redirect(url_for("main.index"))
    
    # Get active ads
    ads_data = query_db(
        """
        SELECT DISTINCT pa.*, COALESCE(u.username, 'System') as username 
        FROM personalized_ads pa 
        LEFT JOIN users u ON pa.user_id = u.id 
        WHERE pa.is_active = 1 
        AND (
            -- Case 1: Ad is owned by user AND has no specific targeting assignments
            (pa.user_id = ? AND NOT EXISTS (SELECT 1 FROM ad_display_assignments WHERE ad_id = pa.id))
            -- Case 2: Ad is specifically assigned to this user
            OR pa.id IN (SELECT ad_id FROM ad_display_assignments WHERE target_user_id = ?)
            -- Case 3: Global Ads (owned by no one/admin)
            OR (pa.user_id IS NULL AND NOT EXISTS (SELECT 1 FROM ad_display_assignments WHERE ad_id = pa.id))
        )
        ORDER BY RANDOM()
        """,
        [link["user_id"], link["user_id"]]
    )
    
    # Organize ads with randomized selection
    ads_by_position = {1: None, 2: None, 3: None}
    
    # Separate ads by type
    large_ads = [ad for ad in ads_data if ad["grid_position"] == 1]
    small_ads = [ad for ad in ads_data if ad["grid_position"] in [2, 3]]
    
    import random
    
    # Select one Large ad for Position 1
    if large_ads:
        selected_large = random.choice(large_ads)
        ads_by_position[1] = selected_large
        # Track impression
        try:
            track_ad_impression(link["id"], link["user_id"], "large", 1, get_client_ip(), selected_large['id'])
        except Exception as e:
            print(f"Error tracking large ad impression: {e}")
            
    # Select two unique Small ads for Position 2 and 3
    if small_ads:
        selected_small = random.sample(small_ads, min(2, len(small_ads)))
        
        # Assign to positions
        for i, ad in enumerate(selected_small):
            pos = i + 2  # 2 or 3
            ads_by_position[pos] = ad
            # Track impression
            try:
                track_ad_impression(link["id"], link["user_id"], "small", pos, get_client_ip(), ad['id'])
            except Exception as e:
                print(f"Error tracking small ad impression: {e}")
    
    # Count how many ads we have
    active_ads_count = sum(1 for ad in ads_by_position.values() if ad is not None)
        
    return render_template("ads.html", 
                         original_url=target_url, 
                         link=link, 
                         ads_by_position=ads_by_position,
                         active_ads_count=active_ads_count)


@links_bp.route("/p/<code>", methods=["GET", "POST"])
def password_protected(code):
    """Handle password-protected links"""
    try:
        link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
        if not link:
            abort(404)
        
        # If link is not password protected, redirect to normal flow
        password_hash = get_link_password_hash(link)
        if not password_hash:
            return redirect(url_for("links.redirect_link", code=code))
        
        if request.method == "POST":
            password = request.form.get("password", "").strip()
            
            if password and password_hash and check_password_hash(password_hash, password):
                # Password is correct, redirect directly to the link destination
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
                
                # Get referrer (Smart Tracking) - same logic as redirect_link
                # 1. Check URL parameters first
                referrer = (
                    request.args.get("ref") or 
                    request.args.get("source") or 
                    request.args.get("utm_source")
                )
                
                # 2. Check User-Agent for social media apps
                if not referrer:
                    ua_lower = user_agent.lower()
                    if 'whatsapp' in ua_lower:
                        referrer = 'WhatsApp'
                    elif 'instagram' in ua_lower:
                        referrer = 'Instagram'
                    elif any(x in ua_lower for x in ['fban', 'fbav']):
                        referrer = 'Facebook'
                
                # 3. Fallback to HTTP Header (filter internal referrers)
                if not referrer:
                    http_referrer = request.headers.get("Referer", "no referrer")
                    
                    if http_referrer and http_referrer != 'no referrer':
                        from urllib.parse import urlparse
                        try:
                            ref_domain = urlparse(http_referrer).netloc
                            current_domain = urlparse(request.host_url).netloc
                            
                            if ref_domain and ref_domain != current_domain:
                                referrer = http_referrer
                            else:
                                referrer = "no referrer"
                        except:
                            referrer = http_referrer
                    else:
                        referrer = "no referrer"
                        
                referrer = referrer[:500]
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
                suspicious = detect_suspicious(visits, now, ip_hash)
                target_url = decide_target(link, behavior, per_session_count)
                
                target_url = decide_target(link, behavior, per_session_count)
                
                # Check if the visitor is the owner of the link
                is_owner = g.user and g.user["id"] == link["user_id"]

                # Log the visit only if NOT owner
                ip_hash = hash_value(ip_address)
                
                if not is_owner:
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
                
                # Skip ads if: direct parameter, premium user, or Elite Pro user
                if skip_ads or is_premium_link or has_ad_free_experience:
                    return redirect(target_url)
                else:
                    return redirect(url_for("links.show_ads", code=code, target=target_url))
            else:
                flash("Incorrect password. Please try again.", "danger")
        
        return render_template("password_protected.html", link=link, code=code)
        
    except Exception as e:
        print(f"Error in password_protected route: {e}")
        flash("An error occurred. Please try again.", "danger")
        return redirect(url_for("main.landing"))


@links_bp.route("/delete-link/<int:link_id>", methods=["POST"])
@login_required
def delete_link(link_id):
    """Delete a link"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check if link belongs to current user
    link = query_db(
        "SELECT * FROM links WHERE id = ? AND user_id = ?",
        [link_id, g.user["id"]], one=True
    )
    
    if not link:
        return jsonify({"success": False, "message": "Link not found"}), 404
    
    try:
        # Delete visits first (foreign key constraint)
        execute_db("DELETE FROM visits WHERE link_id = ?", [link_id])
        # Delete DDoS events
        execute_db("DELETE FROM ddos_events WHERE link_id = ?", [link_id])
        # Delete the link
        execute_db("DELETE FROM links WHERE id = ?", [link_id])
        
        track_user_activity(g.user["id"], "delete_link", f"Deleted link: {link['code']}")
        return jsonify({"success": True, "message": f"Link '{link['code']}' has been deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error deleting link: {str(e)}"}), 500

# Link Update Route
@links_bp.route("/update-link", methods=["POST"])
@login_required
def update_link():
    """Update an existing link's redirect URLs"""
    try:
        data = request.get_json()
        link_id = data.get("id")
        primary_url = data.get("primary_url", "").strip()
        returning_url = data.get("returning_url", "").strip()
        cta_url = data.get("cta_url", "").strip()
        
        if not link_id or not primary_url:
            return jsonify({"success": False, "message": "Link ID and Primary URL are required"}), 400
            
        # Verify ownership
        link = query_db("SELECT user_id FROM links WHERE id = ?", [link_id], one=True)
        if not link or link["user_id"] != g.user["id"]:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
            
        from database import execute_db
        execute_db(
            """
            UPDATE links
            SET primary_url = ?, returning_url = ?, cta_url = ?
            WHERE id = ?
            """,
            [primary_url, returning_url, cta_url, link_id]
        )
        
        # Track activity
        from admin_panel import track_user_activity
        track_user_activity(g.user["id"], "update_link", f"Updated link ID {link_id}")
        
        return jsonify({"success": True, "message": "Link updated successfully"})
        
    except Exception as e:
        print(f"Error updating link: {e}")
        return jsonify({"success": False, "message": "An error occurred while updating the link"}), 500

# Analytics routes (temporarily placed here due to file system issues)
@links_bp.route("/links/<code>")
@login_or_admin_required
def analytics(code):
    """Detailed analytics for a specific link"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity, log_admin_activity
    
    is_admin = session.get("admin_uid") is not None
    try:
        link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
        if not link:
            abort(404)

        if g.get("user"):
            track_user_activity(g.user["id"], "view_analytics", f"Viewed analytics for link: {code}")
        elif is_admin:
             log_admin_activity("view_analytics", "link", link["id"], f"Viewed analytics for link {code}")

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

        # Get the security profile for this link
        security_profile = None
        if link["security_profile_id"]:
            security_profile = query_db("SELECT * FROM security_profiles WHERE id = ?", [link["security_profile_id"]], one=True)
        
        if not security_profile:
            user_id = link["user_id"] or (g.user["id"] if g.user else None)
            if user_id:
                security_profile = query_db(
                    "SELECT * FROM security_profiles WHERE user_id = ? AND is_default = 1",
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
        # Get TRUE total counts from DB (independent of the 200 limit)
        total_visits = query_db("SELECT COUNT(*) as count FROM visits WHERE link_id = ?", [link["id"]], one=True)["count"]
        suspicious_count = query_db("SELECT COUNT(*) as count FROM visits WHERE link_id = ? AND is_suspicious = 1", [link["id"]], one=True)["count"]
        
        # Use ip_hash for unique visitors instead of session_id for better persistence
        unique_visitors_query = query_db("SELECT DISTINCT ip_hash FROM visits WHERE link_id = ?", [link["id"]])
        unique_visitors = len(unique_visitors_query)
        
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
        
        local_days = []
        local_hours = []
        
        for row in visits_raw:
            try:
                # Parse timestamp as UTC
                dt_utc = datetime.fromisoformat(row["ts"]).replace(tzinfo=timezone.utc)
                
                # Bin as UTC for absolute baseline (frontend will localize for the viewer)
                local_days.append(dt_utc.weekday())
                local_hours.append(dt_utc.hour)
            except Exception as e:
                print(f"Error processing timestamp: {e}")
                pass
        
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

        # Get country data explicitly for the Country Chart
        country_data_raw = query_db(
            """
            SELECT country, COUNT(DISTINCT ip_hash) as count
            FROM visits
            WHERE link_id = ? AND country IS NOT NULL AND country != 'Unknown'
            GROUP BY country
            ORDER BY count DESC
            """,
            [link["id"]],
        )
        # Create a simple list of dicts {country: "USA", count: 10}
        country_data = [{'country': row['country'], 'count': row['count']} for row in country_data_raw]

        analytics_payload = {
            "debug_version": "v1.0.1_country_added",
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
            "hourly": hourly_data,
            "daily": daily_data,
            "region": region_data,
            "country": country_data,  # Included new country data
            "cities": [dict(row) for row in city_data],
            "device": [dict(row) for row in device_data],
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
            is_admin=is_admin,
            security_profile=security_profile,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Error loading analytics: {str(e)}", "danger")
        return redirect(url_for("main.index"))


@links_bp.route("/analytics-overview")
@login_required
def analytics_overview():
    """Analytics overview dashboard"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
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
    
    # Track analytics overview view
    track_user_activity(g.user["id"], "view_analytics_overview", "Viewed analytics overview")
    
    return render_template(
        "analytics_overview.html",
        links=links,
        chart_data=chart_data,
        total_clicks=total_clicks,
        unique_visitors=unique_visitors,
        link_stats=link_click_stats
    )

@links_bp.route("/links/<code_id>/csv")
def export_csv(code_id):
    """Export link analytics as CSV"""
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
    from zoneinfo import ZoneInfo
    local_hours = []
    for row in hourly_raw:
        try:
            dt_utc = datetime.fromisoformat(row["ts"]).replace(tzinfo=timezone.utc)
            tz_name = row["timezone"] or "UTC"
            try:
                visitor_tz = ZoneInfo(tz_name)
            except:
                visitor_tz = timezone.utc
            
            dt_local = dt_utc.astimezone(visitor_tz)
            local_hours.append(dt_local.hour)
        except: 
            pass
    hour_counts = Counter(local_hours)

    # Build CSV
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

    # Track CSV export activity
    if g.user:
        from admin_panel import track_user_activity
        track_user_activity(g.user["id"], "export_analytics", f"Exported analytics (CSV) for link: {code_id}")

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=analytics_{code_id}.csv"}
    )


@links_bp.route("/links/<code_id>/export-excel")
@login_required
def export_link_analytics_excel(code_id):
    """Export detailed visitor log as Excel"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
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
        
        # Track Excel export activity
        track_user_activity(g.user["id"], "export_analytics", f"Exported detailed visitor log (Excel) for link: {code_id}")

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