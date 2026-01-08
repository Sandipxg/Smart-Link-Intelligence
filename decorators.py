"""
Smart Link Intelligence - Custom Decorators
Authentication and authorization decorators
"""

from functools import wraps
from flask import g, flash, redirect, url_for, session


def login_required(fn):
    """Decorator to require user authentication"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.get("user"):
            flash("Please log in to continue", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def login_or_admin_required(fn):
    """Decorator to require user or admin authentication"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.get("user") and not session.get("admin_uid"):
            flash("Please log in to continue", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper