import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "youllneverguess"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "mysql+pymysql://root@localhost/icc?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LINES_PER_PAGE = 30
    ANNO_UP_FACTOR = 10
    ANNO_DOWN_FACTOR = 15
    AUTHORIZATION = { "EDIT_QUEUE" : 1, "TAG_CREATION" : 1, "LINE_EDIT" : 1,
            "BOOK_REQUEST": 1, "TAG_REQUEST": 1 }
    MIN_APPROVAL_RATING = 2
    MIN_REJECTION_RATING = -2
    ANNOTATIONS_PER_PAGE = 5
    CARDS_PER_PAGE = 15
    NOTIFICATIONS_PER_PAGE = 15
    USER_PAGE_AVATAR_SIZE = 255
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    ADMINS = ["emails@futuretld.org"]
    ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL")
    SQLALCHEMY_ECHO=0
    UPVOTES_FOR_NOTIFICATION = 2
