"""
Smart Link Intelligence - Analytics Routes
Analytics viewing, CSV/Excel exports, and reporting
"""

from flask import Blueprint, render_template, redirect, url_for, flash, g
from decorators import login_required, login_or_admin_required
from database import query_db

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route("/links/<code>")
@login_or_admin_required
def analytics(code):
    """Detailed analytics for a specific link"""
    try:
        link = query_db("SELECT * FROM links WHERE code = ?", [code], one=True)
        if not link:
            flash("Link not found", "danger")
            return redirect(url_for("main.index"))
        
        # For now, redirect to the original analytics in app_backup.py
        # This is a temporary solution until we can fix the full analytics implementation
        flash("Analytics feature is being migrated. Please check back later.", "info")
        return redirect(url_for("main.index"))
        
    except Exception as e:
        flash(f"Error loading analytics: {str(e)}", "danger")
        return redirect(url_for("main.index"))


@analytics_bp.route("/analytics-overview")
@login_required
def analytics_overview():
    """Analytics overview dashboard"""
    try:
        # For now, show a simple message
        flash("Analytics overview is being migrated. Please check back later.", "info")
        return redirect(url_for("main.index"))
        
    except Exception as e:
        flash(f"Error loading analytics overview: {str(e)}", "danger")
        return redirect(url_for("main.index"))