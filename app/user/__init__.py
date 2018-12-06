from flask import Blueprint

user = Blueprint("user", __name__, url_prefix="/user",
        template_folder="templates")

from app.user import routes, forms
