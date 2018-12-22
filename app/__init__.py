import os
from time import time
from elasticsearch import Elasticsearch

from config import Config

from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flaskext.markdown import Markdown

import logging
from logging.handlers import SMTPHandler, RotatingFileHandler


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login = LoginManager(app)
login.login_view = "user.login"

md = Markdown(app)
mail = Mail(app)
elasticsearch = Elasticsearch([app.config["ELASTICSEARCH_URL"]]) \
        if app.config["ELASTICSEARCH_URL"] else None

from .admin import admin
app.register_blueprint(admin)
from .requests import requests
app.register_blueprint(requests)
from .ajax import ajax
app.register_blueprint(ajax)
from .user import user
app.register_blueprint(user)

# jinja environment variables
app.jinja_env.globals["round"] = round
app.jinja_env.globals["vars"] = app.config
app.jinja_env.globals["len"] = len
app.jinja_env.globals["time"] = time

if not app.debug:
    if app.config["MAIL_SERVER"]:
        auth = None
        if app.config["MAIL_USERNAME"] or app.config["MAIL_PASSWORD"]:
            auth = (app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        secure = None
        if app.config["MAIL_USE_TLS"]:
            secure = ()
        mail_handler = SMTPHandler(
                mailhost=(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]),
                fromaddr="no-reply@" + app.config["MAIL_SERVER"],
                toaddrs=app.config["ADMINS"], subject="ICC FAILURE",
                credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if not os.path.exists("logs"):
        os.mkdir("logs")
    file_handler = RotatingFileHandler("logs/icc.log", maxBytes=10240,
            backupCount=10)
    file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s "
            "[in %(pathname)s:%(lineno)d]"))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("ICC startup")

from app import routes, models, errors, funky
