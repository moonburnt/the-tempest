#!/usr/bin/env python3

from flask import (
    Flask,
    render_template,
    flash,
    request,
    redirect,
    url_for,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from os.path import join, splitext
import logging

log = logging.getLogger(__name__)
app = Flask(__name__)

def allowed_file(filename: str) -> bool:
    """Check if file's extension is in ALLOWED_EXTENSIONS list"""
    # #TODO: add hashsum blacklist or something like that, make function check
    # against it too
    return splitext(filename)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


@app.route("/uploads/<path:name>", methods=["GET", "POST"])
def download_file(name:str):
    """Download file with provided name from server's UPLOAD_DIRECTORY"""
    # Toggling "as_attachment" will make browsers open "save file" dialog instead
    # of opening direct link in new tab
    #return send_from_directory(app.config["UPLOAD_DIRECTORY"], name, as_attachment=True)
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
            filename = secure_filename(file.filename)
            file.save(join(app.config["UPLOAD_DIRECTORY"], filename))
            return redirect(url_for("download_file", name=filename))

    return render_template('upload_file.html.jinja')


if __name__ == "__main__":
    from os import makedirs, urandom
    from sys import exit

    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="[%(asctime)s][%(name)s][%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)

    # TODO: get this from envar, else it will break logins
    app.secret_key = urandom(24)

    # TODO: make this absolute pass obtained from envar or config file
    UPLOAD_DIRECTORY = join(".", "uploaded_files")
    # TODO: add extensions blacklist
    ALLOWED_EXTENSIONS = {".txt", ".png", ".jpg", ".jpeg", ".gif"}

    try:
        makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    except Exception as e:
        log.critical(f"Unable to set UPLOAD_DIRECTORY to {UPLOAD_DIRECTORY}: {e}")
        exit(2)
    app.config["UPLOAD_DIRECTORY"] = UPLOAD_DIRECTORY
    log.info(f"UPLOAD_DIRECTORY has been set to {UPLOAD_DIRECTORY}")

    app.config["ALLOWED_EXTENSIONS"] = ALLOWED_EXTENSIONS
    log.info(f"ALLOWED_EXTENSIONS has been set to {ALLOWED_EXTENSIONS}")

    log.info(f"Attempting to load website")
    app.run(debug=True)
