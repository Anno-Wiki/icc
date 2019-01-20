from flask import Blueprint

main = Blueprint("main", __name__, template_folder="../templates")

from icc.main import routes
