from flask import Blueprint

admin = Blueprint("admin", __name__, url_prefix="/admin",
                  template_folder="templates")

from icc.admin import (annotations, edits, misc, requests, tags, users, wikis)
from icc.admin import forms
