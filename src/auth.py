import functools
from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from dataclasses import dataclass, asdict
from src.database import get_db
from bson.json_util import dumps as bdumps
from bson import ObjectId
from json import loads as jloads
import logging

log = logging.getLogger(__name__)

USERS_COL_NAME = "users"


@dataclass
class UserData:
    # name of user's account
    login: str
    # user's password
    password: str


# This will create blueprint for authentication-related requests
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Register on site"""
    if request.method == "POST":
        data = UserData(
            login=request.form["login"],
            password=request.form["password"],
        )
        db = get_db()

        error = None
        if not data.login:
            error = "Login is required"
        elif not data.password:
            error = "Password is required"

        if error is None:
            # Idk if this is the best way to ensure uniqueness of login. #TODO
            if not db[USERS_COL_NAME].find_one({"login": data.login}):
                data.password = generate_password_hash(data.password)
                db[USERS_COL_NAME].insert_one(asdict(data))
                return redirect(url_for("auth.login"))

            error = "This login is already registered"

        flash(error)

    return render_template("auth/register.html.jinja")


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Login to already registered account"""
    if request.method == "POST":
        data = UserData(
            login=request.form["login"],
            password=request.form["password"],
        )
        db = get_db()

        error = None
        user = db[USERS_COL_NAME].find_one({"login": data.login})
        if user is None:
            error = "Invalid login"
        elif not check_password_hash(user["password"], data.password):
            error = "Invalid password"

        if error is None:
            session.clear()
            # This will store user id in cookie in signed form. Should be secure
            # enough... I think #TODO
            # We need to convert bson to string first, to store it there
            session["user_id"] = jloads(bdumps(user["_id"]))["$oid"]
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html.jinja")


# before_app_request will ensure this runs before every request to this bp's pages
@bp.before_app_request
def load_logged_in_user():
    """Load logged in user"""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        db = get_db()
        # we need to convert string to objectid to compare
        g.user = db[USERS_COL_NAME].find_one({"_id": ObjectId(user_id)})

@bp.route("/logout")
def logout():
    """Logout from current account"""
    # This will clear stored session data (e.g make cookie invalid, I guess?)
    session.clear()
    return redirect(url_for("index"))


# This decorator will ensure that user is logged in, else redirect to login form
# Will be useful on tasks that require user's creditnails
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
