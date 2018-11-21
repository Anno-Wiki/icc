import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    ADMINS = ["emails@futuretld.org"]
    ANNOTATIONS_PER_PAGE = 5
    ANNO_DOWN_FACTOR = 15
    ANNO_UP_FACTOR = 10
    AUTHORIZATION = { "EDIT_QUEUE" : 1, "TAG_CREATION" : 1, "LINE_EDIT" : 1,
            "BOOK_REQUEST": 1, "TAG_REQUEST": 1 }
    CARDS_PER_PAGE = 15
    LINES_PER_SEARCH_PAGE = 10
    ANNOTATIONS_PER_SEARCH_PAGE = 5
    ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL")
    LINES_PER_PAGE = 30
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None
    MIN_APPROVAL_RATING = 2
    MIN_REJECTION_RATING = -2
    NOTIFICATIONS_PER_PAGE = 15
    SECRET_KEY = os.environ.get("SECRET_KEY") or "youllneverguess"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "mysql+pymysql://root@localhost/icc?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPVOTES_FOR_NOTIFICATION = 2
    USER_PAGE_AVATAR_SIZE = 255
#    SQLALCHEMY_ECHO = 1
#    SERVER_NAME = "www.annopedia.org:5000"
