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
    # not implemented yet #TODO
    # uploader: str
    # time of file's upload
    uploaded: datetime
    # when file was accessed the last time
    last_access: datetime


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
    # #TODO: add user-specific subdirectories, save into them based on id
    file.save(join(current_app.config["UPLOAD_DIRECTORY"], local_filename))
    savetime = datetime.utcnow()
    info = FileInfo(
        filename=local_filename,
        original_name=filename,
        uploaded=savetime,
        last_access=savetime,
    )
    db = get_db()
    db[FILES_COL_NAME].insert_one(asdict(info))

    return local_filename


bp = Blueprint("filesharing", __name__)


@bp.route("/uploads/<path:name>", methods=("GET", "POST"))
def download_file(name: str) -> wrappers.Response:
    """Get link to download specified file from server's UPLOAD_DIRECTORY"""

    # updating file's last access time
    db = get_db()
    db[FILES_COL_NAME].update_one(
        {"filename": name},
        {"$set": {"last_access": datetime.utcnow()}},
    )

    # Toggling "as_attachment" will make browsers open "save file" dialog instead
    # of opening direct link in new tab
    # return send_from_directory(app.config["UPLOAD_DIRECTORY"], name, as_attachment=True)
    return send_from_directory(current_app.config["UPLOAD_DIRECTORY"], name)


@bp.route("/upload", methods=("GET", "POST"))
def upload_file():
    """File uploading form"""

    if request.method == "POST":
        file = request.files.get("file", None)
        if file is None or file.filename == "":
            flash("No file has been selected")
        elif file and allowed_file(file.filename):
            return redirect(url_for("filesharing.download_file", name=save_file(file)))
        else:
            flash("Invalid file type, please try something else")

    return render_template("upload_file.html.jinja")
