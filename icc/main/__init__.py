from flask import Blueprint

main = Blueprint("main", __name__, template_folder="templates")

from icc.main import annotations, editions, routes, tags, texts, wikis, writers
