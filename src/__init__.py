#!/usr/bin/env python3

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
import logging

log = logging.getLogger(__name__)

# TODO: maybe make it possible to load settings from config.ini/config.toml
def create_app() -> Flask:
    """Create and configure site's flask instance"""

    app = Flask(__name__, instance_relative_config=True)
    try:
        app.config.from_mapping(
            # Secret key is salt for sessions. We must keep it the same, else
            # users will need to re-login
            SECRET_KEY=environ["SECRET_KEY"],
            # Upload directory is where uploaded files go
            UPLOAD_DIRECTORY=environ["UPLOAD_DIRECTORY"],
            # Allowed extensions is basically a whitelist of file extensions
            ALLOWED_EXTENSIONS={".txt", ".png", ".jpg", ".jpeg", ".gif"},
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
        filename = f"{name}-{uuid4()}{extension}"
        # #TODO: add user-specific subdirectories, save into them based on id
        file.save(join(app.config["UPLOAD_DIRECTORY"], filename))

        return filename

    @app.route("/uploads/<path:name>", methods=["GET", "POST"])
    def download_file(name: str) -> wrappers.Response:
        """Get link to download specified file from server's UPLOAD_DIRECTORY"""

        # Toggling "as_attachment" will make browsers open "save file" dialog instead
        # of opening direct link in new tab
        # return send_from_directory(app.config["UPLOAD_DIRECTORY"], name, as_attachment=True)
        return send_from_directory(app.config["UPLOAD_DIRECTORY"], name)

    @app.route("/", methods=["GET", "POST"])
    def upload_file():
        """File uploading form"""

        if request.method == "POST":
            if "file" not in request.files:
                flash("Received no files")
                return redirect(request.url)

            file = request.files["file"]

            if file.filename == "":
                flash("No file has been selected")
                return redirect(request.url)

            if file and allowed_file(file.filename):
                return redirect(url_for("download_file", name=save_file(file)))

        return render_template("upload_file.html.jinja")

    return app
