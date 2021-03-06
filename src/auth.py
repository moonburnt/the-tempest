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
    current_app,
)
from werkzeug.security import check_password_hash, generate_password_hash
from dataclasses import dataclass, asdict
from src.database import get_users_collection
from bson.json_util import dumps as bdumps
from bson import ObjectId
from json import loads as jloads
from datetime import datetime
import logging

log = logging.getLogger(__name__)


@dataclass
class UserData:
    # name of user's account
    login: str
    # user's password
    password: str
    # when user has registered their account
    registration: datetime
    # when user logged in for last time
    last_access: datetime


# This will create blueprint for authentication-related requests
bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Register on site"""
    if request.method == "POST":
        name = request.form["login"]
        pw = request.form["password"]
        col = get_users_collection()

        error = None
        if not name:
            error = "Login is required"
        elif not pw:
            error = "Password is required"
        elif not (
            current_app.config["LOGIN_LENGTH"][0]
            <= len(name)
            <= current_app.config["LOGIN_LENGTH"][1]
        ):
            error = (
                f"Invalid login length. Must be between "
                f"{current_app.config['LOGIN_LENGTH'][0]} and "
                f"{current_app.config['LOGIN_LENGTH'][1]}."
            )
        elif not (
            current_app.config["PASSWORD_LENGTH"][0]
            <= len(pw)
            <= current_app.config["PASSWORD_LENGTH"][1]
        ):
            error = (
                f"Invalid password length. Must be between "
                f"{current_app.config['PASSWORD_LENGTH'][0]} and "
                f"{current_app.config['PASSWORD_LENGTH'][1]}."
            )
        else:
            # Idk if this is the best way to ensure uniqueness of login. #TODO
            if not col.find_one({"login": name}):
                try:
                    current_time = datetime.utcnow()
                    data = UserData(
                        login=name,
                        password=generate_password_hash(pw),
                        registration=current_time,
                        last_access=current_time,
                    )
                    col.insert_one(asdict(data))
                except Exception as e:
                    log.error(f"Unable to register user: {e}")
                    error = "Internal registration error. Please inform administrator"
                else:
                    return redirect(url_for("auth.login"))
            else:
                error = "This login is already registered"

        flash(error)

    return render_template("auth/register.html.jinja")


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Login to already registered account"""
    if request.method == "POST":
        name = request.form["login"]
        pw = request.form["password"]
        col = get_users_collection()

        error = None
        user = col.find_one({"login": name})
        if user is None:
            error = "Invalid login"
        elif not check_password_hash(user["password"], pw):
            error = "Invalid password"

        if error is None:
            session.clear()
            # This will store user id in cookie in signed form. Should be secure
            # enough... I think #TODO
            # We need to convert bson to string first, to store it there
            session["user_id"] = jloads(bdumps(user["_id"]))["$oid"]
            # updatin last access time
            col.update_one(
                {"login": name},
                {"$set": {"last_access": datetime.utcnow()}},
            )
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html.jinja")


# before_app_request will ensure this runs before every request to this bp's pages
@bp.before_app_request
def load_logged_in_user():
    """Load logged in user's data"""
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        # we need to convert string to objectid to compare
        g.user = get_users_collection().find_one({"_id": ObjectId(user_id)})


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
