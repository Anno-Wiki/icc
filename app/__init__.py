from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import LONGTEXT
from flask_migrate import Migrate
from flask_login import LoginManager
from flaskext.markdown import Markdown

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
db.LONGTEXT = LONGTEXT
migrate = Migrate(app, db)
login = LoginManager(app)
md = Markdown(app)
login.login_view = 'login'

from app import routes, models
