from functools import wraps
from flask import flash, redirect, session, url_for


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("email") is None:
            flash("You need to login to access this page." , "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function