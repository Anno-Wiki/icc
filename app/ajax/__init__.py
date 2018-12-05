from flask import Blueprint

ajax = Blueprint("ajax", __name__, url_prefix="/ajax")

from app.ajax import routes
