from flask import (
    Blueprint,
    session,
    render_template,
)
from src.auth import login_required
from src.database import get_user_files
import logging


log = logging.getLogger(__name__)

# This blueprint should show profile-specific info
bp = Blueprint("profile", __name__)


@bp.route("/my_uploads")
@login_required
def show_uploads():
    """Show user's personal uploads template"""
    return render_template(
        "uploads.html.jinja",
        files=get_user_files(session.get("user_id")),
    )
