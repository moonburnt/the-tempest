from flask import (
    Flask,
    render_template,
)
from os import environ, makedirs
from sys import exit
import atexit
from src import database
import logging


log = logging.getLogger(__name__)


# TODO: maybe make it possible to load settings from config.ini/config.toml
def create_app() -> Flask:
    """Create and configure site's flask instance"""

    app = Flask(__name__, instance_relative_config=True)
    try:
        log.debug("Attempting to load settings")
        app.config.from_mapping(
            # Secret key is salt for sessions. We must keep it the same, else
            # users will need to re-login
            SECRET_KEY=environ["SECRET_KEY"],
            # Upload directory is where uploaded files go
            UPLOAD_DIRECTORY=environ["UPLOAD_DIRECTORY"],
            # Allowed extensions is basically a whitelist of file extensions
            ALLOWED_EXTENSIONS={".txt", ".png", ".jpg", ".jpeg", ".gif"},
            # Mongodb shenanigans for database.py module
            MONGODB_ADDRESS=environ["MONGODB_ADDRESS"],
            DATABASE_NAME=environ["DATABASE_NAME"],
            # Minimal/maximal allowed login/password lengths
            LOGIN_LENGTH=(6, 15),
            # #TODO: maybe add something to ensure code contain special symbols?
            PASSWORD_LENGTH=(6, 30),
        )
    except Exception as e:
        log.critical(f"Unable to configure site: {e}")
        exit(2)

    try:
        makedirs(app.config["UPLOAD_DIRECTORY"], exist_ok=True)
    except Exception as e:
        log.critical(
            f"Unable to set UPLOAD_DIRECTORY to {app.config['UPLOAD_DIRECTORY']}: {e}"
        )
        exit(2)

    try:
        log.debug("Attempting to connect to database")
        with app.app_context():
            db = database.get_db()
            # Configuring collection indexes
            database.initialize_files_indexes()

    except Exception as e:
        log.critical(f"Unable to establish database connection: {e}")
        exit(2)

    @app.route("/")
    def index():
        # I shouldnt put return into with app.context() loop, coz it will break
        # g values and similar stuff
        with app.app_context():
            files_amount = database.get_files_amount()
            users_amount = database.get_users_amount()

        return render_template(
            "index.html.jinja",
            files_amount=files_amount,
            users_amount=users_amount,
        )

    # Ensuring closeup of application will kill database connection
    # Idk if its the proper way to do that stuff, but will do for now #TODO
    def close_connection():
        with app.app_context():
            database.close_connection()

    atexit.register(close_connection)

    # Attaching all blueprints to application
    from src import filesharing, auth, profile

    app.register_blueprint(filesharing.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(profile.bp)

    return app
