"""
Smart Link Intelligence - Authentication Routes
Login, signup, logout, and related functionality
"""

import re
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db
from config import USER_SESSION_KEY
from utils import send_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """User registration"""
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
            html_content = render_template(
                "emails/welcome.html",
                username=username,
                host_url=request.host_url,
                current_year=datetime.now().year
            )

            # Send Welcome Email
            send_email(
                to_email=email,
                subject="Welcome to Smart Link Intelligence!",
                html_content=html_content
            )
            
            # Log the user in automatically
            user = query_db("SELECT id FROM users WHERE username = ?", [username_lower], one=True)
            session[USER_SESSION_KEY] = user["id"]
            
            # Track user registration activity
            from admin_panel import track_user_activity
            track_user_activity(user["id"], "register", f"New user registered: {username}")
            
            flash("🎉 Account created successfully! Welcome to Smart Link Intelligence.", "success")
            return redirect(url_for("main.index"))
            
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


@auth_bp.route("/check-availability", methods=["POST"])
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


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login"""
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
        from admin_panel import track_user_activity
        track_user_activity(user["id"], "login", f"User logged in: {user['username']}")
        
        # Handle remember me functionality (extend session)
        if remember_me:
            session.permanent = True
            # Set session to last 30 days if remember me is checked
            from flask import current_app
            current_app.permanent_session_lifetime = timedelta(days=30)
        
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(url_for("main.index"))
        
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """User logout"""
    session.pop(USER_SESSION_KEY, None)
    flash("Logged out", "info")
    return redirect(url_for("auth.login"))