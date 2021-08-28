from flask import (
    Blueprint,
    current_app,
    g,
    send_from_directory,
    url_for,
    wrappers,
    redirect,
    request,
    flash,
    render_template,
    abort,
)
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from uuid import uuid4
from dataclasses import dataclass, asdict
from datetime import datetime
from os.path import join, splitext
from os import environ, makedirs
from src.database import get_db
import logging


log = logging.getLogger(__name__)

FILES_COL_NAME = "files"


@dataclass(frozen=True)
class FileInfo:
    # name of file on disk
    filename: str
    # name of file how its been received (after securing but without uuid4)
    original_name: str
    # time of file's upload
    uploaded: datetime
    # when file was accessed the last time
    last_access: datetime
    # login of user who uploaded file. Will be None in case of anonymous upload
    uploader: str = None
    # subdirectory where file is saved on disk. Is either None or user's login.
    # Kept as separate value to be future-proof, in case it will be switched
    # to uploader's id or something like that later
    location: str = None


def allowed_file(filename: str) -> bool:
    """Check if file can be uploaded, based on its extension"""

    # #TODO: add hashsum blacklist or something like that, make function check
    # against it too
    return splitext(filename)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


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
    # #TODO: maybe switch authorized upload directory's name from login to id?
    uploader = g.user.get("login") if g.user else None
    savepath = current_app.config["UPLOAD_DIRECTORY"]
    if uploader:
        savepath = join(savepath, uploader)
        makedirs(savepath, exist_ok=True)

    file.save(join(savepath, local_filename))
    savetime = datetime.utcnow()
    info = FileInfo(
        filename=local_filename,
        original_name=filename,
        uploaded=savetime,
        last_access=savetime,
        uploader=uploader,
        location=uploader,
    )
    db = get_db()
    db[FILES_COL_NAME].insert_one(asdict(info))

    # This doesnt return uploader as uploader, but as location
    return local_filename, uploader


def get_download_link(name: str, directory: str = None):
    """Get download link for provided file"""
    db = get_db()

    # Updating last access to file
    # TODO: in case file doesnt exist, it may cause trouble
    db[FILES_COL_NAME].update_one(
        {"filename": name},
        {"$set": {"last_access": datetime.utcnow()}},
    )

    if directory:
        name = join(directory, name)

    # Toggling "as_attachment" will make browsers open "save file" dialog instead
    # of opening direct link in new tab
    # return send_from_directory(down_path, name, as_attachment=True)
    return send_from_directory(current_app.config["UPLOAD_DIRECTORY"], name)


bp = Blueprint("filesharing", __name__)


@bp.route("/uploads/<path:directory>/<path:name>", methods=("GET", "POST"))
def download_from_directory(directory: str, name: str) -> wrappers.Response:
    """Get link to download specified file from provided dir inside UPLOAD_DIRECTORY"""
    return get_download_link(name, directory)


@bp.route("/uploads/<path:name>", methods=("GET", "POST"))
def download_file(name: str) -> wrappers.Response:
    """Get link to download specified file from server's UPLOAD_DIRECTORY"""
    return get_download_link(name)


@bp.route("/upload", methods=("GET", "POST"))
def upload_file():
    """File uploading form"""

    # I may want to import load_logged_in_user from auth module #TODO
    # rn save_file() works without it, but may break at some point
    if request.method == "POST":
        file = request.files.get("file", None)
        if file is None or file.filename == "":
            flash("No file has been selected")
        elif file and allowed_file(file.filename):
            name, path = save_file(file)
            if path:
                return redirect(
                    url_for(
                        "filesharing.download_from_directory", name=name, directory=path
                    )
                )

            return redirect(url_for("filesharing.download_file", name=name))
        else:
            flash("Invalid file type, please try something else")

    return render_template("upload_file.html.jinja")
