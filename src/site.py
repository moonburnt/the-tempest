from flask import (
    Flask,
    render_template,
    flash,
    request,
    redirect,
    url_for,
    send_from_directory,
    wrappers,
)
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from os.path import join, splitext
from os import environ, makedirs
from sys import exit
from uuid import uuid4
from dataclasses import asdict
import atexit
from datetime import datetime
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
        # For now only adding "files", since users arent there yet #TODO
        files_collection = db["files"]

    except Exception as e:
        log.critical(f"Unable to establish database connection: {e}")
        exit(2)

    def allowed_file(filename: str) -> bool:
        """Check if file can be uploaded, based on its extension"""

        # #TODO: add hashsum blacklist or something like that, make function check
        # against it too
        return splitext(filename)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

    def save_file(file: FileStorage, filename: str = None) -> str:
        """Save provided file into server's UPLOAD_DIRECTORY"""

        # Ensuring filename wont contain unwanted symbols
        # this may crash without file.filename, but it shouldnt happen
        filename = secure_filename(filename or file.filename)
        # We could avoid this part entirely by adding uuid before name
        # But for now it doesnt seem like an issue, may change l8r #TODO
        name, extension = splitext(filename)
        # Adding uuid4 to name, to avoid overwriting existing files with same name
        local_filename = f"{name}-{uuid4()}{extension}"
        # #TODO: add user-specific subdirectories, save into them based on id
        file.save(join(app.config["UPLOAD_DIRECTORY"], local_filename))
        savetime = datetime.utcnow()
        info = database.FileInfo(
            filename=local_filename,
            original_name=filename,
            uploaded=savetime,
            last_access=savetime,
        )
        files_collection.insert_one(asdict(info))

        return local_filename

    @app.route("/uploads/<path:name>", methods=("GET", "POST"))
    def download_file(name: str) -> wrappers.Response:
        """Get link to download specified file from server's UPLOAD_DIRECTORY"""

        # updating file's last access time
        files_collection.update_one(
            {"filename": name},
            {"$set": {"last_access": datetime.utcnow()}},
        )

        # Toggling "as_attachment" will make browsers open "save file" dialog instead
        # of opening direct link in new tab
        # return send_from_directory(app.config["UPLOAD_DIRECTORY"], name, as_attachment=True)
        return send_from_directory(app.config["UPLOAD_DIRECTORY"], name)

    @app.route("/")
    def index():
        return render_template("index.html.jinja")

    @app.route("/upload", methods=("GET", "POST"))
    def upload_file():
        """File uploading form"""

        if request.method == "POST":
            file = request.files.get("file", None)
            if file is None or file.filename == "":
                flash("No file has been selected")
            elif file and allowed_file(file.filename):
                return redirect(url_for("download_file", name=save_file(file)))
            else:
                flash("Invalid file type, please try something else")

        return render_template("upload_file.html.jinja")

    # Ensuring closeup of application will kill database connection
    # Idk if its the proper way to do that stuff, but will do for now #TODO
    def close_connection():
        with app.app_context():
            database.close_connection()

    atexit.register(close_connection)

    #from src import auth
    #app.register_blueprint(auth.bp)

    return app
