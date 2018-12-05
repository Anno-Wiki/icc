from flask import Blueprint

admin = Blueprint("admin", __name__, url_prefix="/admin",
        template_folder="templates")

from app.admin import routes
