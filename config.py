import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'Swl,Ap,as,atot,alAgb'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root@localhost/icc?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
