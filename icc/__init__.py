import os
from elasticsearch import Elasticsearch

from config import Config

from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flaskext.markdown import Markdown
from flask_moment import Moment

import logging
from logging.handlers import SMTPHandler, RotatingFileHandler


db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'main.login'
mail = Mail()
moment = Moment()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    app.md = Markdown(app)
    moment.init_app(app)
    app.elasticsearch = Elasticsearch([app.config["ELASTICSEARCH_URL"]]) \
        if app.config["ELASTICSEARCH_URL"] else None

    from icc.admin import admin as admin_bp
    app.register_blueprint(admin_bp)
    from icc.requests import requests as requests_bp
    app.register_blueprint(requests_bp)
    from icc.ajax import ajax as ajax_bp
    app.register_blueprint(ajax_bp)
    from icc.user import user as user_bp
    app.register_blueprint(user_bp)
    from icc.main import main as main_bp
    app.register_blueprint(main_bp)

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'],
                        app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject="ICC FAILURE",
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/icc.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s "
                "[in %(pathname)s:%(lineno)d]"))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("ICC startup")

    # jinja environment variables
    app.jinja_env.globals['vars'] = app.config
    app.jinja_env.globals['len'] = len
    app.jinja_env.globals['zip'] = zip
    app.jinja_env.globals['enumerate'] = enumerate
    from icc.funky import proc_links
    app.jinja_env.filters['proc_links'] = proc_links
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.auto_reload = True

    return app


from icc.models.annotation import classes as aclasses
from icc.models.content import classes as cclasses
from icc.models.request import classes as rclasses
from icc.models.user import classes as uclasses
from icc.models.wiki import classes as wclasses
classes = {**aclasses, **cclasses, **rclasses, **wclasses, **uclasses}
