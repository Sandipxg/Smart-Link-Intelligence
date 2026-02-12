"""
Smart Link Intelligence - Main Application
Refactored Flask application with modular structure
"""

import os
from flask import Flask, g, session
from config import FLASK_CONFIG, USER_SESSION_KEY
from database import ensure_db, close_db, query_db
from ddos_protection import DDoSProtection

# Import blueprints
from admin_panel import admin_bp, ensure_admin_tables
from ddos_protection import ddos_bp
from routes.main import main_bp
from routes.auth import auth_bp
from routes.links import links_bp
from routes.user import user_bp
from routes.ads import ads_bp
# Note: Analytics routes temporarily integrated into other modules due to file system issues


def create_app() -> Flask:
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configure Flask app
    for key, value in FLASK_CONFIG.items():
        app.config[key] = value
    
    # Set up request handlers
    app.before_request(_before_request)
    app.teardown_appcontext(close_db)
    
    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Initialize database
    ensure_db()
    ensure_admin_tables()
    
    # Initialize DDoS Protection
    ddos_protection = DDoSProtection(os.path.join(os.path.dirname(__file__), "smart_links.db"))
    
    # Register blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(ddos_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(links_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(ads_bp)
    # Note: Analytics routes temporarily integrated into other modules
    
    @app.context_processor
    def inject_global_data():
        if g.user:
            rules = query_db("SELECT * FROM behavior_rules WHERE user_id = ? ORDER BY is_default DESC, rule_name ASC", [g.user["id"]])
            
            # Security profiles are for elite_pro only
            profiles = []
            user_data = dict(g.user)
            if user_data.get("membership_tier") == "elite_pro":
                profiles = query_db("SELECT * FROM security_profiles WHERE user_id = ? ORDER BY is_default DESC, profile_name ASC", [g.user["id"]])
                
            return dict(behavior_rules=rules, security_profiles=profiles)
        return dict(behavior_rules=[], security_profiles=[])
        
    return app


def _before_request():
    """Handle before request processing"""
    from utils import ensure_session
    
    ensure_session()
    g.user = None
    uid = session.get(USER_SESSION_KEY)
    if uid:
        user = query_db("SELECT * FROM users WHERE id = ?", [uid], one=True)
        g.user = user

    # Maintenance Mode Check
    try:
        maintenance_setting = query_db("SELECT setting_value FROM system_settings WHERE setting_key = 'maintenance_mode'", one=True)
        if maintenance_setting and maintenance_setting['setting_value'] == '1':
            # Direct check for admin session
            is_admin = session.get('admin_id') is not None
            
            # Exemptions:
            # 1. Static files (css, js, images)
            # 2. Admin routes (so admins can login and manage)
            # 3. The maintenance page itself
            # 4. Admin login page specifically
            from flask import request
            
            is_exempt = (
                (request.endpoint and 'static' in request.endpoint) or
                request.path.startswith('/admin') or
                request.endpoint == 'main.maintenance'
            )
            
            if not (is_admin or is_exempt):
                # Clear user session to force re-login after maintenance
                session.pop(USER_SESSION_KEY, None)
                g.user = None
                from flask import redirect, url_for
                return redirect(url_for('main.maintenance'))
    except Exception:
        # Fail gracefully if DB table doesn't exist or query fails
        pass


# Create the application
appl = create_app()

if __name__ == "__main__":
    appl.run(debug=True, port=5000, host="0.0.0.0")