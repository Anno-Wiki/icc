import os
import mysqlpw


class Config:
    """The default config object."""
    DEBUG = True
    HEARBEAT = True
    TEMPLATES_AUTO_RELOAD = True
    ADMINS = ['emails@futuretld.org']
    ANNOTATIONS_PER_PAGE = 5

    # mail system
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None

    # vote margins
    VOTES_FOR_APPROVAL = 2
    VOTES_FOR_REJECTION = -2
    VOTES_FOR_REQUEST_REJECTION = -10000000000000
    VOTES_FOR_REQUEST_APPROVAL = 100000000000000

    # per pages
    ANNOTATIONS_PER_SEARCH_PAGE = 5
    CARDS_PER_PAGE = 15
    COMMENTS_PER_PAGE = 25
    LINES_PER_PAGE = 30
    LINES_PER_SEARCH_PAGE = 10
    NOTIFICATIONS_PER_PAGE = 15

    USER_PAGE_AVATAR_SIZE = 128
    TIME = '%I:%M %p %m/%d/%y (UTC)'

    # technicals
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'youllneverguess'
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or\
        f'mysql+pymysql://{mysqlpw.ACCT}:{mysqlpw.PW}@localhost/'\
        'icc?charset=utf8mb4'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = 0
