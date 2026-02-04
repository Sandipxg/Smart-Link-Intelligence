"""
Smart Link Intelligence - User Management Routes
User settings, notifications, upgrade, and account management
"""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.security import check_password_hash, generate_password_hash
from decorators import login_required
from database import query_db, execute_db
from config import MEMBERSHIP_TIERS

user_bp = Blueprint('user', __name__)


@user_bp.route("/settings")
@login_required
def settings():
    """User account settings"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Get user statistics
    total_links = query_db("SELECT COUNT(*) as count FROM links WHERE user_id = ?", [g.user["id"]], one=True)["count"]
    total_clicks = query_db("SELECT COUNT(*) as count FROM visits v JOIN links l ON v.link_id = l.id WHERE l.user_id = ?", [g.user["id"]], one=True)["count"]
    
    # Track settings view
    track_user_activity(g.user["id"], "view_settings", "Viewed account settings")
    
    return render_template("settings.html", total_links=total_links, total_clicks=total_clicks)


@user_bp.route("/settings/update", methods=["POST"])
@login_required
def update_settings():
    """Update user settings"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
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
            return redirect(url_for("user.settings"))
    
    track_user_activity(g.user["id"], "update_settings", "Updated account security/email settings")
    flash("Settings updated successfully", "success")
    return redirect(url_for("user.settings"))


@user_bp.route("/settings/preferences", methods=["POST"])
@login_required
def update_preferences():
    """Update user preferences"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # For now, just show success message
    # In a real app, you'd store these preferences in the database
    track_user_activity(g.user["id"], "update_preferences", "Updated user preferences")
    
    flash("Preferences updated successfully", "success")
    return redirect(url_for("user.settings"))


@user_bp.route("/settings/delete-account", methods=["POST"])
@login_required
def delete_account():
    """Delete user account"""
    confirm_username = request.form.get("confirm_username", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()
    
    if confirm_username != g.user["username"]:
        flash("Username confirmation does not match", "danger")
        return redirect(url_for("user.settings"))
    
    if not check_password_hash(g.user["password_hash"], confirm_password):
        flash("Password confirmation is incorrect", "danger")
        return redirect(url_for("user.settings"))
    
    # Delete user data
    execute_db("DELETE FROM visits WHERE link_id IN (SELECT id FROM links WHERE user_id = ?)", [g.user["id"]])
    execute_db("DELETE FROM links WHERE user_id = ?", [g.user["id"]])
    execute_db("DELETE FROM personalized_ads WHERE user_id = ?", [g.user["id"]])
    execute_db("DELETE FROM users WHERE id = ?", [g.user["id"]])
    
    from flask import session
    from config import USER_SESSION_KEY
    session.clear()
    flash("Your account has been deleted successfully", "info")
    return redirect(url_for("auth.login"))


@user_bp.route("/notifications")
@login_required
def notifications():
    """Site notifications for the logged-in user"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    user_dict = dict(g.user) if g.user else {}
    user_tier = user_dict.get("membership_tier", "free")
    if not user_tier: 
        user_tier = "free"
    
    user_notifications = query_db("""
        SELECT n.* FROM notifications n
        LEFT JOIN notification_dismissals d ON n.id = d.notification_id AND d.user_id = ?
        WHERE (n.target_user_id = ? 
           OR n.target_group = 'all' 
           OR (n.target_group = ? AND n.target_user_id IS NULL))
           AND d.id IS NULL
        ORDER BY n.created_at DESC
    """, [g.user["id"], g.user["id"], user_tier])
    
    # Track notifications view
    track_user_activity(g.user["id"], "view_notifications", "Viewed notification center")
    
    return render_template("notifications.html", notifications=user_notifications)


@user_bp.route("/delete-notification/<int:notification_id>", methods=["POST"])
@login_required
def delete_notification(notification_id):
    """Dismiss a notification for the current user"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Ensure the notification exists and is meant for this user (security check)
    user_dict = dict(g.user) if g.user else {}
    user_tier = user_dict.get("membership_tier", "free")
    if not user_tier: 
        user_tier = "free"

    notification = query_db("""
        SELECT * FROM notifications 
        WHERE id = ? AND (
            target_user_id = ? OR 
            target_group = 'all' OR 
            (target_group = ? AND target_user_id IS NULL)
        )
    """, [notification_id, g.user["id"], user_tier], one=True)

    if notification:
        # Check if already dismissed to avoid duplicates
        exists = query_db("SELECT id FROM notification_dismissals WHERE user_id = ? AND notification_id = ?", 
                        [g.user["id"], notification_id], one=True)
        if not exists:
            execute_db("INSERT INTO notification_dismissals (user_id, notification_id) VALUES (?, ?)", 
                     [g.user["id"], notification_id])
            track_user_activity(g.user["id"], "delete_notification", "Dismissed a notification")
            flash("Notification removed", "success")
    else:
        flash("Notification not found", "danger")

    return redirect(url_for("user.notifications"))


@user_bp.route("/upgrade")
@login_required
def upgrade():
    """Upgrade plans page"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    track_user_activity(g.user["id"], "view_upgrade", "Viewed upgrade plans")
    return render_template("upgrade.html")


@user_bp.route("/upgrade/process", methods=["POST"])
@login_required
def process_upgrade():
    """Process upgrade (demo implementation)"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # In a real app, you'd integrate with a payment processor like Stripe
    # For demo purposes, we'll just upgrade the user
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
    
    track_user_activity(g.user["id"], "upgrade", f"Upgraded account to {target_tier}")
    tier_name = MEMBERSHIP_TIERS[target_tier]["name"]
    flash(f"🎉 Upgraded to {tier_name}! Enjoy your new features.", "success")
    return redirect(url_for("main.index"))


@user_bp.route("/behavior-rules")
@login_required
def behavior_rules():
    """Manage user's behavior rules"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
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
            INSERT INTO behavior_rules (user_id, rule_name, returning_window_hours, interested_threshold, engaged_threshold, 
                                        requests_per_ip_per_minute, requests_per_ip_per_hour, requests_per_link_per_minute,
                                        burst_threshold, suspicious_threshold, ddos_threshold, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [g.user["id"], "Default Rule", 48, 2, 3, 60, 1000, 500, 100, 10, 50, 1]
        )
        user_rules = query_db(
            "SELECT * FROM behavior_rules WHERE user_id = ? ORDER BY created_at DESC",
            [g.user["id"]]
        )
    
    # Track behavior rules view
    track_user_activity(g.user["id"], "view_rules", "Viewed behavior rules")
    
    return render_template("behavior_rules.html", user_rules=user_rules)


@user_bp.route("/behavior-rules/create", methods=["POST"])
@login_required
def create_behavior_rule():
    """Create a new behavior rule"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    rule_name = request.form.get("rule_name", "").strip()
    returning_window_hours = int(request.form.get("returning_window_hours", 48))
    interested_threshold = int(request.form.get("interested_threshold", 2))
    engaged_threshold = int(request.form.get("engaged_threshold", 3))
    
    # DDoS Settings
    requests_per_ip_per_minute = int(request.form.get("requests_per_ip_per_minute", 60))
    requests_per_ip_per_hour = int(request.form.get("requests_per_ip_per_hour", 1000))
    requests_per_link_per_minute = int(request.form.get("requests_per_link_per_minute", 500))
    burst_threshold = int(request.form.get("burst_threshold", 100))
    suspicious_threshold = int(request.form.get("suspicious_threshold", 10))
    ddos_threshold = int(request.form.get("ddos_threshold", 50))
    
    # Validation
    if not rule_name:
        flash("Rule name is required", "danger")
        return redirect(url_for("user.behavior_rules"))
    
    if returning_window_hours < 1 or returning_window_hours > 168:  # 1 hour to 1 week
        flash("Returning window must be between 1 and 168 hours", "danger")
        return redirect(url_for("user.behavior_rules"))
    
    if interested_threshold < 1 or engaged_threshold < 1:
        flash("Thresholds must be at least 1", "danger")
        return redirect(url_for("user.behavior_rules"))
    
    if engaged_threshold <= interested_threshold:
        flash("Engaged threshold must be higher than interested threshold", "danger")
        return redirect(url_for("user.behavior_rules"))
        
    # Validate DDoS Settings
    if requests_per_ip_per_minute < 10 or requests_per_ip_per_hour < 100:
        flash("Rate limits are too low", "danger")
        return redirect(url_for("user.behavior_rules"))
        
    if ddos_threshold <= suspicious_threshold:
        flash("DDoS threshold must be higher than suspicious threshold", "danger")
        return redirect(url_for("user.behavior_rules"))
    
    # Check if user already has 5 rules (limit)
    existing_count = query_db("SELECT COUNT(*) as count FROM behavior_rules WHERE user_id = ?", [g.user["id"]], one=True)["count"]
    if existing_count >= 5:
        flash("You can only have up to 5 behavior rules", "warning")
        return redirect(url_for("user.behavior_rules"))
    
    # Create the rule
    execute_db(
        """
        INSERT INTO behavior_rules (user_id, rule_name, returning_window_hours, interested_threshold, engaged_threshold,
                                    requests_per_ip_per_minute, requests_per_ip_per_hour, requests_per_link_per_minute,
                                    burst_threshold, suspicious_threshold, ddos_threshold, is_default)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [g.user["id"], rule_name, returning_window_hours, interested_threshold, engaged_threshold,
         requests_per_ip_per_minute, requests_per_ip_per_hour, requests_per_link_per_minute,
         burst_threshold, suspicious_threshold, ddos_threshold, 0]
    )
    
    track_user_activity(g.user["id"], "create_rule", f"Created behavior rule: {rule_name}")
    flash(f"Behavior rule '{rule_name}' created successfully", "success")
    return redirect(url_for("user.behavior_rules"))


@user_bp.route("/behavior-rules/delete/<int:rule_id>", methods=["POST"])
@login_required
def delete_behavior_rule(rule_id):
    """Delete a behavior rule"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check if rule belongs to current user
    rule = query_db(
        "SELECT * FROM behavior_rules WHERE id = ? AND user_id = ?",
        [rule_id, g.user["id"]], one=True
    )
    
    if not rule:
        flash("Rule not found", "danger")
        return redirect(url_for("user.behavior_rules"))
    
    # Don't allow deletion of default rule if it's the only one
    if rule["is_default"]:
        other_rules = query_db("SELECT COUNT(*) as count FROM behavior_rules WHERE user_id = ? AND id != ?", [g.user["id"], rule_id], one=True)["count"]
        if other_rules == 0:
            flash("Cannot delete the only remaining rule", "danger")
            return redirect(url_for("user.behavior_rules"))
    
    execute_db("DELETE FROM behavior_rules WHERE id = ?", [rule_id])
    track_user_activity(g.user["id"], "delete_rule", f"Deleted behavior rule: {rule['rule_name']}")
    flash("Behavior rule deleted successfully", "success")
    return redirect(url_for("user.behavior_rules"))


@user_bp.route("/behavior-rules/set-default/<int:rule_id>", methods=["POST"])
@login_required
def set_default_behavior_rule(rule_id):
    """Set a behavior rule as default"""
    # Import here to avoid circular imports
    from admin_panel import track_user_activity
    
    # Check if rule belongs to current user
    rule = query_db(
        "SELECT * FROM behavior_rules WHERE id = ? AND user_id = ?",
        [rule_id, g.user["id"]], one=True
    )
    
    if not rule:
        flash("Rule not found", "danger")
        return redirect(url_for("user.behavior_rules"))
    
    # Unset all other default rules for this user
    execute_db("UPDATE behavior_rules SET is_default = 0 WHERE user_id = ?", [g.user["id"]])
    
    # Set this rule as default
    execute_db("UPDATE behavior_rules SET is_default = 1 WHERE id = ?", [rule_id])
    
    track_user_activity(g.user["id"], "set_default_rule", f"Set default behavior rule: {rule['rule_name']}")
    flash(f"'{rule['rule_name']}' is now your default behavior rule", "success")
    return redirect(url_for("user.behavior_rules"))