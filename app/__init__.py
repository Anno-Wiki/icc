from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flaskext.markdown import Markdown

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
md = Markdown(app)
login.login_view = 'login'
app.jinja_env.globals['round'] = round

from app import routes, models
