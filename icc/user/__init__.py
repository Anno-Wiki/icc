from flask import Blueprint

user = Blueprint("user", __name__, url_prefix="/user",
                 template_folder="templates")

from icc.user import routes, edit, follow, forms
