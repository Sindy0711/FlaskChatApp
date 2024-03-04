from functools import wraps
import random
from string import ascii_letters
from flask import flash, redirect, session, url_for

def generate_room_code(length: int, existing_codes: list[str]) -> str:
        while True:
            code_chars = [random.choice(ascii_letters) for _ in range(length)]
            code = ''.join(code_chars)

            if code not in existing_codes:
                return code

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("email") is None:
            flash("You need to login to access this page." , "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function