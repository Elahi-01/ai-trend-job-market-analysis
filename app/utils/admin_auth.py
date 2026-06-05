"""Small admin-session helpers for private owner-only pages."""
from functools import wraps
from flask import session, redirect, url_for, request, flash


def is_admin_authenticated() -> bool:
    return bool(session.get("admin_authenticated"))


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_admin_authenticated():
            flash("Please login as admin to access this private area.", "warning")
            return redirect(url_for("admin.login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapper
