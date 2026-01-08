"""
Smart Link Intelligence - Main Routes
Landing page, dashboard, maintenance, documentation, and chat
"""

from flask import Blueprint, render_template, request, redirect, url_for, g, jsonify, session, flash
from datetime import datetime
from decorators import login_required
from database import query_db
from config import MEMBERSHIP_TIERS, USER_SESSION_KEY
from chatbot import get_chat_response

main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def landing():
    """Landing page"""
    # If user is already logged in, redirect to dashboard
    if g.user:
        return redirect(url_for("main.index"))
    return render_template("landing.html")


@main_bp.route("/maintenance")
def maintenance():
    """Public maintenance page"""
    # Clear user session to force re-login after maintenance
    session.pop(USER_SESSION_KEY, None)
    g.user = None
    
    # unexpected error handling if table doesn't exist yet
    try:
        msg_setting = query_db("SELECT setting_value FROM system_settings WHERE setting_key = 'maintenance_message'", one=True)
        message = msg_setting['setting_value'] if msg_setting else "We are currently performing scheduled maintenance. We will be back shortly."
    except:
        message = "We are currently performing scheduled maintenance. We will be back shortly."
        
    return render_template("maintenance.html", maintenance_message=message, now=datetime.now())


@main_bp.route("/dashboard")
@login_required
def index():
    """Main dashboard"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
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
    
    # Track dashboard view
    track_user_activity(g.user["id"], "view_dashboard", "Viewed main dashboard")
    
    return render_template("index.html", 
                           links=links, 
                           chart_data=chart_data, 
                           behavior_rules=behavior_rules, 
                           new_link=new_link,
                           tier_info=tier_info,
                           link_count=link_count,
                           user_tier=user_tier)


@main_bp.route("/documentation")
@login_required
def documentation():
    """Documentation page"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    track_user_activity(g.user["id"], "view_docs", "Viewed documentation")
    return render_template("documentation.html")


@main_bp.route("/chat", methods=["POST"])
def chat():
    """AI Chat endpoint"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    data = request.get_json()
    message = data.get("message")
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    response = get_chat_response(message)
    
    # Track AI chat activity
    if g.user:
        track_user_activity(g.user["id"], "use_ai_chat", "Interacted with AI chatbot")
        
    return jsonify({"response": response})