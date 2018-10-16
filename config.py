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
    USER_PAGE_AVATAR_SIZE = 128
